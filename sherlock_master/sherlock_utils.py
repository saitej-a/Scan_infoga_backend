import datetime
import sys
import os
import json
import time
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional

# Add the current directory to the path so we can import the sherlock modules
sys.path.append(os.path.dirname(os.path.realpath(__file__)))



from sherlock_master.sherlock_project.sites import SitesInformation
from sherlock_master.sherlock_project.sherlock import sherlock
from sherlock_master.sherlock_project.notify import QueryNotifyPrint
from sherlock_master.sherlock_project.result import QueryStatus, QueryResult

# Load site data once when the module is imported
site_data = SitesInformation().sites
site_data_dict = {site.name: site.information for site in site_data.values()}

def format_sherlock_results(results: Dict[str, Any], username: str) -> Dict[str, Any]:
    """
    Format the results from Sherlock into a more user-friendly structure
    
    Args:
        results (dict): The raw results from Sherlock
        username (str): The username that was searched
        
    Returns:
        dict: Formatted results with username, found accounts, and count
    """
    formatted_results = []
    for site_name, site_result in results.items():
        if site_result.get('status').status == QueryStatus.CLAIMED:
            formatted_results.append({
                'site_name': site_name,
                'url_main': site_result.get('url_main'),
                'url_user': site_result.get('url_user'),
                'http_status': site_result.get('http_status'),
                'response_time': site_result.get('status').query_time
            })
    
    return {
        'username': username,
        'found_accounts': formatted_results,
        'count': len(formatted_results)
    }

def run_sherlock_search(username: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Run the Sherlock search for a given username
    
    Args:
        username (str): The username to search for
        timeout (int): Timeout for requests in seconds
        
    Returns:
        dict: Raw results from Sherlock
    """
    # Create notify object for query results
    query_notify = QueryNotifyPrint(result=None, verbose=False, print_all=True, browse=False)
    
    # Run sherlock with the username
    results = sherlock(
        username,
        site_data_dict,
        query_notify,
        timeout=timeout
    )
    
    return results

def search_username(username: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Search for a username across social networks
    
    Args:
        username (str): The username to search for
        timeout (int): Timeout for requests in seconds
        
    Returns:
        dict: Formatted results with username, found accounts, and count
    """
    # Run the search
    results = run_sherlock_search(username, timeout)
    
    # Format the results
    formatted_results = format_sherlock_results(results, username)
    
    return formatted_results

def batch_search_usernames(usernames: List[str], timeout: int = 60) -> Dict[str, Any]:
    """
    Search for multiple usernames in batch
    
    Args:
        usernames (list): List of usernames to search for
        timeout (int): Timeout for requests in seconds
        
    Returns:
        dict: Results for each username and total count
    """
    all_results = []
    for username in usernames:
        # Run the search for each username
        results = run_sherlock_search(username, timeout)
        
        # Format the results
        formatted_results = format_sherlock_results(results, username)
        all_results.append(formatted_results)
    
    return {
        'results': all_results,
        'count': len(all_results)
    }

def get_available_sites() -> Dict[str, Any]:
    """
    Get a list of all sites that Sherlock can search
    
    Returns:
        dict: List of sites and total count
    """
    sites_list = []
    for site_name, site_info in site_data_dict.items():
        sites_list.append({
            'name': site_name,
            'url_main': site_info.get('urlMain'),
            'is_nsfw': site_info.get('isNSFW', False)
        })
    
    return {
        'sites': sites_list,
        'count': len(sites_list)
    }

# New async functions
async def fetch_site(session, site_name, site_info, username, timeout):
    """
    Fetch a single site asynchronously
    
    Args:
        session: aiohttp ClientSession
        site_name: Name of the site
        site_info: Site information dictionary
        username: Username to search for
        timeout: Request timeout in seconds
        
    Returns:
        tuple: (site_name, result)
    """
    url = site_info['url'].format(username)
    url_main = site_info.get('urlMain', "")
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
    }
    
    if "headers" in site_info:
        headers.update(site_info["headers"])
    
    error_type = site_info["errorType"]
    
    # Check if username is valid for this site
    regex_check = site_info.get("regexCheck")
    import re
    if regex_check and re.search(regex_check, username) is None:
        # Username not allowed on this site
        result = {
            'url_main': url_main,
            'url_user': url,
            'status': QueryResult(username, site_name, url, QueryStatus.ILLEGAL),
            'http_status': None,
            'response_text': None
        }
        return site_name, result
    
    try:
        start_time = time.time()
        
        # Determine request method
        request_method = site_info.get("request_method", "GET")
        
        # Use the appropriate URL
        url_probe = site_info.get("urlProbe", url)
        if url_probe != url:
            url_probe = url_probe.format(username)
        
        # Make the request
        if request_method == "GET":
            async with session.get(url_probe, headers=headers, timeout=timeout) as response:
                response_text = await response.text()
                http_status = response.status
        elif request_method == "HEAD":
            async with session.head(url_probe, headers=headers, timeout=timeout) as response:
                response_text = ""
                http_status = response.status
        elif request_method == "POST":
            request_payload = site_info.get("request_payload", {})
            if request_payload:
                request_payload = {k: v.format(username) if isinstance(v, str) else v 
                                 for k, v in request_payload.items()}
            async with session.post(url_probe, headers=headers, json=request_payload, timeout=timeout) as response:
                response_text = await response.text()
                http_status = response.status
        else:
            # Default to GET
            async with session.get(url_probe, headers=headers, timeout=timeout) as response:
                response_text = await response.text()
                http_status = response.status
        
        query_time = time.time() - start_time
        
        # Determine if the account exists based on the error type
        if error_type == "message":
            # Check for error messages in the response
            errors = site_info.get("errorMsg", [])
            if isinstance(errors, str):
                errors = [errors]
            
            error_found = any(error in response_text for error in errors)
            query_status = QueryStatus.AVAILABLE if error_found else QueryStatus.CLAIMED
            
        elif error_type == "status_code":
            # Check status code
            error_codes = site_info.get("errorCode", [])
            if isinstance(error_codes, int):
                error_codes = [error_codes]
            
            if error_codes and http_status in error_codes:
                query_status = QueryStatus.AVAILABLE
            elif http_status >= 300 or http_status < 200:
                query_status = QueryStatus.AVAILABLE
            else:
                query_status = QueryStatus.CLAIMED
                
        elif error_type == "response_url":
            # Check if the response URL is the same as the request URL
            if 200 <= http_status < 300:
                query_status = QueryStatus.CLAIMED
            else:
                query_status = QueryStatus.AVAILABLE
        else:
            query_status = QueryStatus.UNKNOWN
        
        result = {
            'url_main': url_main,
            'url_user': url,
            'status': QueryResult(username, site_name, url, query_status, query_time),
            'http_status': http_status,
            'response_text': response_text
        }
        
    except asyncio.TimeoutError:
        result = {
            'url_main': url_main,
            'url_user': url,
            'status': QueryResult(username, site_name, url, QueryStatus.UNKNOWN, None, "Timeout Error"),
            'http_status': None,
            'response_text': None
        }
    except Exception as e:
        result = {
            'url_main': url_main,
            'url_user': url,
            'status': QueryResult(username, site_name, url, QueryStatus.UNKNOWN, None, str(e)),
            'http_status': None,
            'response_text': None
        }
    
    return site_name, result

async def async_sherlock_search(username: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Run the Sherlock search asynchronously for a given username
    
    Args:
        username (str): The username to search for
        timeout (int): Timeout for requests in seconds
        
    Returns:
        dict: Raw results from Sherlock
    """
    results = {}
    
    # Create a ClientSession that will be used for all requests
    async with aiohttp.ClientSession() as session:
        # Create tasks for each site
        tasks = []
        for site_name, site_info in site_data_dict.items():
            task = fetch_site(session, site_name, site_info, username, timeout)
            tasks.append(task)
        
        # Wait for all tasks to complete
        for coro in asyncio.as_completed(tasks):
            site_name, result = await coro
            results[site_name] = result
            
            # Print progress (similar to original Sherlock)
            # status = result['status']
            # if status.status == QueryStatus.CLAIMED:
            #     print(f"[+] {site_name}: `{result['url_user']}`")
            # elif status.status == QueryStatus.AVAILABLE:
            #     print(f"[-] {site_name}: Not Found!")
            # elif status.status == QueryStatus.ILLEGAL:
            #     print(f"[-] {site_name}: Illegal Username Format For This Site!")
            # elif status.status == QueryStatus.UNKNOWN:
            #     print(f"[-] {site_name}: {status.context if status.context else 'Error Connecting'}")
    
    return results

async def async_search_username(username: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Search for a username across social networks asynchronously
    
    Args:
        username (str): The username to search for
        timeout (int): Timeout for requests in seconds
        
    Returns:
        dict: Formatted results with username, found accounts, and count
    """
    # Run the search
    print(f"[*] Checking username {username} on: ")
    print()
    
    results = await async_sherlock_search(username, timeout)
    
    # Format the results
    formatted_results = format_sherlock_results(results, username)
    
    return formatted_results

async def async_batch_search_usernames(usernames: List[str], timeout: int = 60) -> Dict[str, Any]:
    """
    Search for multiple usernames in batch asynchronously
    
    Args:
        usernames (list): List of usernames to search for
        timeout (int): Timeout for requests in seconds
        
    Returns:
        dict: Results for each username and total count
    """
    all_results = []
    for username in usernames:
        # Run the search for each username
        results = await async_search_username(username, timeout)
        all_results.append(results)
    
    return {
        'results': all_results,
        'count': len(all_results)
    }

async def get_detailed_results_async(username: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Get detailed results for a username search including all websites and their status asynchronously
    
    Args:
        username (str): The username to search for
        timeout (int): Timeout for requests in seconds
        
    Returns:
        dict: Detailed results with username, time taken, and all websites with their status
    """
    # Record start time
    start_time = time.time()
    
    # Run the search
    print(f"[*] Checking username {username} on: ")
    print()
    
    results = await async_sherlock_search(username, timeout)
    
    # Calculate time taken
    time_taken = time.time() - start_time
    
    # Format the websites results
    websites = {}
    for site_name, site_result in results.items():
        status = site_result.get('status')
        if status.status == QueryStatus.CLAIMED:
            websites[site_name] = site_result.get('url_user')
        # else:
        #     websites[site_name] = str(status)
    
    return {
        'results': websites,
        'metadata':{
            'username': username,
            'execution_time': round(time_taken, 2),
        },
        'datetime':datetime.datetime.now().isoformat() + 'Z',    
    }

# Example usage
if __name__ == '__main__':
    # Example: Search for a single username with detailed results asynchronously
    result = asyncio.run(get_detailed_results_async('johndoe'))
    print(json.dumps(result, indent=2))