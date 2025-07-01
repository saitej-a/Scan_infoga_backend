import datetime
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import mobile
from payments.models import WalletBalance
from payments.utils import get_amount_after_api_call, update_user_balance
from user_activities.models import UserActivity
from user_activities.utils import is_called_by_user_previously, log_user_activity
from core.utils import create_response, get_token_from_header, get_user_from_token
from django.db import transaction

from mobile.models import Mobile360Report, ProfileAdvanceReport
from mobile.serializers import Mobile360ReportSerializer, ProfileAdvanceReportSerializer
from mobile.utils import fetch_mobile360_data, fetch_profile_advance_data


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_alternate_mobile_numbers(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    mobile_number = request.data.get("mobile_number")
    realtime_data = request.data.get("realtimeData")

    if not mobile_number:
        return create_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Mobile number is required",
            success=False,
        )
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is called: ",is_called)
    
    if not realtime_data:
        report = ProfileAdvanceReport.objects.filter(mobile=mobile_number).first()
        if report:
            serialized = ProfileAdvanceReportSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_alternate_mobile_number', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            alt_numbers = serialized['result']['result']['alternate_phone']
            return Response(create_response(True, "Data fetched from database", {'alternate_numbers':alt_numbers, 'datetime':datetime.datetime.now().isoformat() + "Z"}), status=status.HTTP_200_OK)

    
    try:
        balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_alternate_mobile_number', user=user)
        if balance_after_deduction<0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        api_response = fetch_profile_advance_data(mobile_number)
        
        if api_response.get('success'):
            result_data = api_response['data']

            with transaction.atomic():
                ProfileAdvanceReport.objects.update_or_create(
                    mobile=mobile_number,
                    defaults={'result':result_data}
                )
                update_user_balance(user=user,amount=balance_after_deduction)
            
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            try:
                alt_numbers =result_data['result']['alternate_phone']
                return Response(create_response(True,'Data Fetched from external API',{'alternate_numbers':alt_numbers, 'datetime':datetime.datetime.now().isoformat() + "Z"}),status=status.HTTP_200_OK)
            except:
                return Response(create_response(True,'Data Fetched from external API', {'alternate_numbers':'No Data Found'}), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
       

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_email(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    mobile_number = request.data.get("mobile_number")
    realtime_data = request.data.get("realtimeData")

    if not mobile_number:
        return create_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Mobile number is required",
            success=False,
        )
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is called: ",is_called)
    
    if not realtime_data:
        report = ProfileAdvanceReport.objects.filter(mobile=mobile_number).first()
        if report:
            serialized = ProfileAdvanceReportSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_email', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            alt_emails=serialized['result']['result']['email']
            return Response(create_response(True, "Data fetched from database", {'email':alt_emails, 'datetime':datetime.datetime.now().isoformat() + "Z"}), status=status.HTTP_200_OK)

    
    try:
        balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_email', user=user)
        if balance_after_deduction<0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        api_response = fetch_profile_advance_data(mobile_number)
        
        if api_response.get('success'):
            result_data = api_response['data']

            with transaction.atomic():
                ProfileAdvanceReport.objects.update_or_create(
                    mobile=mobile_number,
                    defaults={'result':result_data}
                )
                update_user_balance(user=user,amount=balance_after_deduction)
            
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            try:
                alt_emails=result_data['result']['email']
                return Response(create_response(True,'Data Fetched from external API',{'email':alt_emails, 'datetime':datetime.datetime.now().isoformat() + "Z"}),status=status.HTTP_200_OK)
            except:
                return Response(create_response(True,'Data Fetched from external API', {'email':'No Data Found'}), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_lpg_info(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    mobile_number = request.data.get("mobile_number")
    realtime_data = request.data.get("realtimeData")

    if not mobile_number:
        return create_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Mobile number is required",
            success=False,
        )
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is called: ",is_called)
    
    if not realtime_data:
        report = Mobile360Report.objects.filter(mobile_number=mobile_number).first()
        if report:
            serialized = Mobile360ReportSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_lpg_info', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            lpg_info=serialized['result']['result']['lpg_info']
            return Response(create_response(True, "Data fetched from database", {'lpg_info':lpg_info, 'datetime':datetime.datetime.now().isoformat() + "Z"}), status=status.HTTP_200_OK)

    
    try:
        balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_lpg_info', user=user)
        if balance_after_deduction<0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        api_response = fetch_mobile360_data(mobile_number)
        
        if api_response.get('success'):
            result_data = api_response['data']

            with transaction.atomic():
                Mobile360Report.objects.update_or_create(
                    mobile_number=mobile_number,
                    defaults={'result':result_data}
                )
                update_user_balance(user=user,amount=balance_after_deduction)
            
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            try:
                lpg_info=result_data['result']['lpg_info']
                return Response(create_response(True,'Data Fetched from external API',{'lpg_info':lpg_info, 'datetime':datetime.datetime.now().isoformat() + "Z"}),status=status.HTTP_200_OK)
            except:
                return Response(create_response(True,'Data Fetched from external API', {'lpg_info':'No Data Found'}), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                
         

