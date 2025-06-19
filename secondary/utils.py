import datetime
import os
import requests
from django.core.cache import cache

def fetch_payworld_data(sender_mobile):
    """
    Fetches data from Payworld API and adds timestamp.
    """
    api_url = os.getenv("PAYWORLD_API_URL")
    retailer_mobile_no = os.getenv("RETAILER_MOBILE_NO")

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
        "Cookie": cache.get("cookie_payworld")["cookie"]
    }

    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get("message") == "Sender is not registered":
            return {
                "status": False,
                "message": "Sender is not registered"
            }

        if response.status_code != 200:
            raise Exception("Failed to fetch data from Payworld API")

        data = result["data"]
        data["datetime"] = datetime.datetime.now().isoformat() + "Z"

        return {
            "status": True,
            "data": data
        }

    except Exception as e:
        raise Exception(f"Failed to fetch data from Payworld API: {str(e)}")

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