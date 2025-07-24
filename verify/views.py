import datetime
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from .models import AadharVerifyReport
from .models import TrucallerVerifyReport

from payments.utils import get_amount_after_api_call, update_user_balance
from user_activities.models import UserActivity
from user_activities.utils import is_called_by_user_previously, log_user_activity

from .utils import trucallerVerify
from .utils import aadharVerify
from core.utils import create_response, get_token_from_header, get_user_from_token

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


# Create your views here.
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def handleAadhaarVerify(request):
    aadhaarNo = request.data.get('aadhaarNo')
    realtimeData = request.data.get('realtimeData')

    if not aadhaarNo:
        return Response(create_response(False, "aadhaarNo is required in the request body.", None), status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(aadhaarNo, str):
        return Response(create_response(False, "aadhaarNo must be a string.", None), status=status.HTTP_400_BAD_REQUEST)

    if len(aadhaarNo) != 12:
        return Response({"error": "aadhaarNo must be 12 digits."}, status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    payload = request.data

    balance_after_deduction = get_amount_after_api_call(api_name="aadhar_verify", user=user)
    if balance_after_deduction < 0.0:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
    
    time = datetime.datetime.now().isoformat() + 'Z'

    def last_cleaned(existing):
        if not existing or not existing.result:
            return None, None
        data_entries = existing.result.get("data", [])
        if not data_entries:
            return None, None

        last_entry = data_entries[-1]

        if not isinstance(last_entry, dict):
            return None, None
        
        last_timestamp = next(iter(last_entry))
        return last_timestamp, last_entry[last_timestamp]
    
    if realtimeData:
        try:
            result = aadharVerify(aadhaarNo)
            print("here", result)
            if not result["status"]:
                print("here it si ",result)
                return Response(create_response(False, "Aadhar verification failed", result.get("error")),status=status.HTTP_400_BAD_REQUEST)
            existing = AadharVerifyReport.objects.filter(aadhaarNo=aadhaarNo).first()

            # compare the last entry with the new result
            _, last_data = last_cleaned(existing=existing)
            obj = existing
            if last_data != result:
                if not obj:
                    obj = AadharVerifyReport.objects.create(aadhaarNo=aadhaarNo)
                existing_result = obj.result or {}
                existing_result.setdefault("datetime", [])
                existing_result.setdefault("data", [])
                existing_result["datetime"].append(time)
                existing_result["data"].append({time: result})
                # Save changes
                obj.result = existing_result
                obj.save()  

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            update_user_balance(user=user, amount=balance_after_deduction, api_name="aadhar_verify")
            return Response(create_response(True, "Data fetched successfully from external api.", obj.result), status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(create_response(False, str(e), None), status=status.HTTP_400_BAD_REQUEST)
        
    else:
        try:
            is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)
            existing = AadharVerifyReport.objects.filter(aadhaarNo=aadhaarNo).first()
            if not existing:
                result = aadharVerify(aadhaarNo)
                if not result:
                    return Response(create_response(False, "Error While Verfiying External API", None), status=status.HTTP_404_NOT_FOUND)
                data_to_store = {
                    "datetime": [time],
                    "data": [
                        {time: result}
                    ]
                }
                update_user_balance(user=user, amount=balance_after_deduction, api_name="aadhar_verify")
                obj = AadharVerifyReport.objects.create(aadhaarNo=aadhaarNo, result=data_to_store)
                return Response(create_response(True, "Data fetched successfully from external api.", data_to_store), status=status.HTTP_200_OK)
            else:
                existing_result = existing.result or {}
                log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
                if not is_called:
                    update_user_balance(user=user, amount=balance_after_deduction, api_name="aadhar_verify")
                    return Response(create_response(True, "Data fetched from Database.", existing_result), status=status.HTTP_200_OK)
                
                return Response(create_response(True, "Data fetched from Database.", existing_result), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(create_response(False, str(e), None), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def handleTrucallerVerify(request):
    mobile = request.data.get('mobile_number')
    realtimeData = request.data.get('realtimeData')

    if not mobile:
        return Response(create_response(False, "mobile is required in the request body.", None), status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(mobile, str):
        return Response(create_response(False, "mobile must be a string.", None), status=status.HTTP_400_BAD_REQUEST)

    if len(mobile) > 10:
        return Response(create_response(False, "Mobile number should be exactly 10 digits long.", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    payload = request.data

    balance_after_deduction = get_amount_after_api_call(api_name="trucaller_verify", user=user)
    if balance_after_deduction < 0.0:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
    
    time = datetime.datetime.now().isoformat() + 'Z'


    def last_cleaned(existing):
        if not existing or not existing.result:
            return None, None
        data_entries = existing.result.get("data", [])
        if not data_entries:
            return None, None

        last_entry = data_entries[-1]

        if not isinstance(last_entry, dict):
            return None, None

        last_timestamp = next(iter(last_entry))
        return last_timestamp, last_entry[last_timestamp]

    
    if realtimeData:
        try:
            result = trucallerVerify(mobile)
            if(not result["status"]):
                return Response(create_response(False, "Trucaller verification failed", result.get("error")),status=status.HTTP_400_BAD_REQUEST)
            
            existing = TrucallerVerifyReport.objects.filter(mobile=mobile).first()

            _, last_data = last_cleaned(existing=existing)
            new_result = result.get("data").get("data")
            
            obj = existing
            if last_data != new_result:
                if not obj:
                    obj = TrucallerVerifyReport.objects.create(mobile=mobile)
                existing_result = obj.result or {}
                existing_result.setdefault("datetime", [])
                existing_result.setdefault("data", [])
                existing_result["datetime"].append(time)
                existing_result["data"].append({time: new_result})
                obj.result = existing_result
                obj.save()

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            update_user_balance(user=user, amount=balance_after_deduction, api_name="trucaller_verify")
            return Response(create_response(True, "Data fetched successfully from external api.", obj.result), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(create_response(False, str(e), None), status=status.HTTP_400_BAD_REQUEST)
        
    else:
        try:
            is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)
            existing = TrucallerVerifyReport.objects.filter(mobile=mobile).first()
            if not existing:
                result = trucallerVerify(mobile)
                if(not result["status"]):
                    return Response(create_response(False, "Trucaller verification failed", result.get("error")),status=status.HTTP_400_BAD_REQUEST)
                new_result = result.get("data").get("data")
                data_to_store = {
                    "datetime": [time],
                    "data": [
                        {time: new_result}
                    ]
                }
                update_user_balance(user=user, amount=balance_after_deduction, api_name="trucaller_verify")
                obj = TrucallerVerifyReport.objects.create(mobile=mobile, result=data_to_store)
                return Response(create_response(True, "Data fetched successfully from external api.", obj.result), status=status.HTTP_200_OK)
            else:
                existing_result = existing.result or {}
                log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
                if not is_called:
                    update_user_balance(user=user, amount=balance_after_deduction, api_name="trucaller_verify")
                    return Response(create_response(True, "Data fetched from Database.", existing_result), status=status.HTTP_200_OK)
                
                return Response(create_response(True, "Data fetched from Database.", existing_result), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(create_response(False, str(e), None), status=status.HTTP_400_BAD_REQUEST)


        