from django.core.cache import cache
import requests
import os
from dotenv import load_dotenv


def fetch_payworld_data(sender_mobile):
    """
    Fetches data from Payworld API and returns the response.
    """
    # Replace this with the actual Payworld API URL if not set in environment
    api_url = os.getenv("PAYWORLD_API_URL")
    
    # Construct parameters (query string) for the API request
    params = {
        "action": "/get_sender_details",
        "method": "get",
        "sender_mobile_no": sender_mobile,
        "kyc_status": "0",
        "retailer_mobile_no": "8866739875"
    }
    
    # Custom headers, including cookies for authentication
    headers = {
        "accept": "application/json, text/plain, */*",
        "priority": "u=1, i",
        "referer": "https://qmr-new.payworldindia.com/retailer/qmr",
        "x-requested-with": "XMLHttpRequest",
        "Cookie": cache.get("cookie_payworld")["cookie"]
    }
    
    # Make the GET request to fetch the data
    response = requests.get(api_url, params=params, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch data from Payworld API: {response.status_code}")
