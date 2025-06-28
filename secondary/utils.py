import datetime
import os
import requests
from django.core.cache import cache

# def fetch_payworld_data(sender_mobile):
#     """
#     Fetches data from Payworld API and adds timestamp.
#     """
#     api_url = os.getenv("PAYWORLD_API_URL")
#     retailer_mobile_no = os.getenv("RETAILER_MOBILE_NO")

#     params = {
#         "action": "/get_sender_details",
#         "method": "get",
#         "sender_mobile_no": sender_mobile,
#         "kyc_status": "0",
#         "retailer_mobile_no": retailer_mobile_no,
#     }

#     headers = {
#         "accept": "application/json, text/plain, */*",
#         "priority": "u=1, i",
#         "referer": "https://qmr-new.payworldindia.com/retailer/qmr",
#         "x-requested-with": "XMLHttpRequest",
#         "Cookie": cache.get("cookie_payworld")["cookie"]
#     }

#     try:
#         response = requests.get(api_url, params=params, headers=headers)
#         response.raise_for_status()
#         result = response.json()
#         print("API_Response: ", result)

#         if result.get("message") == "Sender is not registered":
#             return {
#                 "status": False,
#                 "message": "Sender is not registered"
#             }

#         if response.status_code != 200:
#             raise Exception("Failed to fetch data from Payworld API")

#         data = result["data"]
#         data["datetime"] = datetime.datetime.now().isoformat() + "Z"

#         return {
#             "status": True,
#             "data": data
#         }

#     except Exception as e:
#         raise Exception(f"Failed to fetch data from Payworld API: {str(e)}")

def fetch_payworld_data(sender_mobile):
    """
    Fetches data from Payworld API and adds timestamp.
    """
    api_url = os.getenv("PAYWORLD_API_URL")
    retailer_mobile_no = os.getenv("RETAILER_MOBILE_NO")

    try:
        cookie_obj = cache.get("cookie_payworld")
        if not cookie_obj or "cookie" not in cookie_obj:
            return {
                "status": False,
                "message": "Payworld session cookie not found in cache"
            }

        params = {
            "action": "/get_sender_details",
            "method": "get",
            "sender_mobile_no": sender_mobile,
            "kyc_status": "0",
            "retailer_mobile_no": retailer_mobile_no,
        }

        headers = {
            "accept": "application/json, text/plain, */*",
            "priority": "u=1, i",
            "referer": "https://qmr-new.payworldindia.com/retailer/qmr",
            "x-requested-with": "XMLHttpRequest",
            "Cookie": cookie_obj["cookie"]
        }

        response = requests.get(api_url, params=params, headers=headers)

        if response.status_code != 200:
            return {
                "status": False,
                "message": f"External API HTTP {response.status_code}"
            }

        result = response.json()

        # Handle known message
        if result.get("message") == "Sender is not registered":
            return {
                "status": False,
                "message": "Sender is not registered"
            }

        if "data" not in result:
            return {
                "status": False,
                "message": "Data field missing in API response"
            }

        data = result["data"]
        data["datetime"] = datetime.datetime.now().isoformat() + "Z"

        return {
            "status": True,
            "data": data
        }

    except requests.exceptions.RequestException as req_err:
        print("Error")
        return {
            "status": False,
            "message": f"Request failed: {str(req_err)}"
        }

    except ValueError as json_err:
        return {
            "status": False,
            "message": f"Invalid JSON response from Payworld: {json_err}"
        }

    except Exception as e:
        return {
            "status": False,
            "message": f"Unexpected error: {str(e)}"
        }


def fetch_razorpay_ifsc_data(ifsc_code):
    """
    Fetches data from Razorpay IFSC API.
    """
    api_url = os.getenv("RAZORPAY_IFSC_API_URL")
    
    api_url = f"{api_url}/{ifsc_code}"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        result = response.json()

        if response.status_code != 200:
            raise Exception("Failed to fetch data from Payworld API")

        result["datetime"] = datetime.datetime.now().isoformat() + "Z"

        return {
            "status": True,
            "data": result
        }

    except Exception as e:
        raise Exception(f"Failed to fetch data from Razorpay IFSC API: {str(e)}")

def fetch_paynearby_data(mobile_number):
    """
    Fetches data from Paynearby API.
    """
    api_url = os.getenv("PAYNEARBY_API_URL")

    print("API URL: ", api_url)
    
    try:
        cookie_obj = cache.get("paynearby_credentials")
        print("Cookie: ", cookie_obj)
        if not cookie_obj or "token" not in cookie_obj:
            return {
                "status": False,
                "message": "Paynearby session cookie not found in cache"
            }

        headers={
            "Authorization":cookie_obj['token'],
            "User-Agent": "Mozilla/5.0 (compatible; MyApp/1.0; +https://myapp.com)"
        }
        
        payload = {
        "phone_number": mobile_number,
        "detail_level": "high",
        "agent_ref_id": 8785475,
        "latitude": cookie_obj["lat"],
        "longitude": cookie_obj["lng"],
        "request_channel": 11,
        "service_channel": 4,
        "checksum_data": "53a90ad3a18e87d2c7e50674d3da96152e27c6157f23cc9c09805d840e7eb8000edf238e977f3ea257094f1301a806f12784e17c0f559f4486e30d08c8f8f0ab"
    }
        print("Calling paynearby")
        response = requests.post(url=api_url, headers=headers, json=payload)
        print("Response: ", response)
        
        if response.status_code != 200:
            return {
                "status": False,
                "message": f"External API HTTP {response.status_code}"
            }
        
        result = response.json()
        
        if "data" not in result:
            return {
                "status": False,
                "message": "Data field missing in API response"
            }
        
        data = result["data"]
        filtered_data = {
            "vendor":data['vendor'],
            'bene':data['bene'],
            'monthly_transaction_limit':data['monthly_transaction_limit'],
            'remaining_limit':data['remaining_limit'],
            'datetime':datetime.datetime.now().isoformat() + "Z"
        }

        return {
            "status": True,
            "data": filtered_data
        }

    except requests.exceptions.RequestException as req_err:
        return {
            "status": False,
            "message": f"Request failed: {str(req_err)}"
        }

    except ValueError as json_err:
        return {
            "status": False,
            "message": f"Invalid JSON response from Payworld: {json_err}"
        }

    except Exception as e:
        return {
            "status": False,
            "message": f"Unexpected error: {str(e)}"
        }

        