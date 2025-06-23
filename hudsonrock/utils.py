import requests
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def fetch_hudson_search_by_email(email):
    api_url = os.getenv("HUDSONROCK_SEARCH_BY_EMAIL_URL")

    params = {
        "email":email,
    }

    response = requests.get(api_url, params=params)
    data = response.json()
    parts = re.split(r'\.', data['message'])
    data['message'] = f"{parts[0]}."

    
        
    if response.status_code == 200:
        return {
            'success':True,
            'data':data
        }
    
    raise Exception(f"Error fetching data for email {email}. Status code: {response.status_code}")


def fetch_hudson_search_by_ip(ip):
    api_url = os.getenv("HUDSONROCK_SEARCH_BY_IP_URL")

    params = {
        "ip":ip,

    }

    response = requests.get(api_url, params=params)
    data = response.json()
    parts = re.split(r'\.', data['message'])
    data['message'] = f"{parts[0]}."

    
        
    if response.status_code == 200:
        return {
            'success':True,
            'data':data
        }
    
    raise Exception(f"Error fetching data for ip {ip}. Status code: {response.status_code}")  