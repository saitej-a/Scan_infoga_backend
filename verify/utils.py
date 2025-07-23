import requests
import os
import re
from dotenv import load_dotenv
import json
import time
from datetime import datetime

load_dotenv()

def aadharVerify(aadhar_number):
    try:
        getCaptchaUrl = os.getenv("AADHAR_CAPTCHA_API_URL")
        payload = json.dumps({
            "captchaLength": "6",
            "captchaType": "2",
            "audioCaptchaRequired": False
        })
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en_IN',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://myaadhaar.uidai.gov.in',
            'Pragma': 'no-cache',
            'Referer': 'https://myaadhaar.uidai.gov.in/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'appid': 'MYAADHAAR',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'x-request-id': '6b62ce2d-ea38-4c3e-a13f-4ce1694fb84b'
        }

        response = requests.request("POST", getCaptchaUrl, headers=headers, data=payload)
        if response.status_code != 200:
            raise Exception(f"Aadhar Captcha Error. Status code: {response.status_code}")
        result = response.json()
        base64_str = result.get("imageBase64")
        captchaTxnId = result.get("transactionId")
        api_key = os.getenv("TWO_CAPTCHA_API_KEY")
        
        createTaskUrl = os.getenv("TWO_CAPTCHA_CREATE_TASK_URL")
        createTaskPayload = json.dumps({
            "clientKey": api_key,
            "task": {
                "type": "ImageToTextTask",
                "body": base64_str,
                "phrase": False,
                "case": True,
                "numeric": 0,
                "math": False,
                "minLength": 6,
                "maxLength": 6,
                "comment": "enter the text you see on the image"
            },
            "languagePool": "en"
        })
        createHeaders = {
            'Content-Type': 'application/json'
        }
        
        
        createTaskResponse = requests.request("POST", createTaskUrl, headers=createHeaders, data=createTaskPayload)
        if createTaskResponse.status_code != 200:
            raise Exception(f"Error creating captcha task. Status code: {createTaskResponse.status_code}")
        task_result = createTaskResponse.json()
        task_id = task_result.get("taskId")
        time.sleep(4.0)  

        getTaskResultUrl = os.getenv("TWO_CAPTCHA_GET_TASK_URL")
        getTaskResultPayload = json.dumps({
            "clientKey": api_key,
            "errorId": 0,
            "taskId": task_id
        })
        time.sleep(1.0)
        captcha_code = None
        attempt = 0
        while not captcha_code and attempt < 5:
            getTaskResultResponse = requests.request("POST", getTaskResultUrl, headers=createHeaders, data=getTaskResultPayload)

            if getTaskResultResponse.status_code == 200:
                task_result = getTaskResultResponse.json()
                if task_result.get("status") == "ready":
                    captcha_code = task_result.get("solution", {}).get("text")
                    break
            attempt += 1
            time.sleep(1.0)
        
        aadharVerifyUrl = os.getenv("AADHAR_VERIFY_API_URL")
        aadharVerifyPayload = json.dumps({
            "uid": aadhar_number,
            "captchaTxnId": captchaTxnId,
            "captcha": captcha_code,
            "transactionId": "6b62ce2d-ea38-4c3e-a13f-4ce1694fb84b",
            "captchaLogic": "V3"
        })
        aadhaarVerifyheaders = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en_IN',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://myaadhaar.uidai.gov.in',
            'Referer': 'https://myaadhaar.uidai.gov.in/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'appid': 'MYAADHAAR',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'x-request-id': '6b62ce2d-ea38-4c3e-a13f-4ce1694fb84b'
        }
        response = requests.request("POST", aadharVerifyUrl, headers=aadhaarVerifyheaders, data=aadharVerifyPayload)
        if response.status_code == 200:
            result = response.json()
            print("Aadhar verification result:", result)
            if result.get("status") == "Success":
                return {
                    "status": True,
                    "data": result
                }
            else:
                message = result.get("errorDetails", {}).get("messageEnglish", "Unknown error")
                print("MEssage:", message)
                raise Exception(f"{message}")

        else:
            raise Exception(f"Aadhar verification API error. Status code: {response.status_code}")
    except Exception as e:
        return {
            "status": False,
            "error": str(e)
        }   



