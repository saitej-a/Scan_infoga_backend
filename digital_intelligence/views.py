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
                if result_data['status']==1:
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
                if result_data['status']==1:
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
                
                

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_address_profile_advance(request):
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
                balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_address_profile_advance', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            address = serialized['result']['result']['address']
            return Response(create_response(True, "Data fetched from database", {'address':address, 'datetime':datetime.datetime.now().isoformat() + "Z"}), status=status.HTTP_200_OK)

    
    try:
        balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_address_profile_advance', user=user)
        if balance_after_deduction<0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        api_response = fetch_profile_advance_data(mobile_number)
        
        if api_response.get('success'):
            result_data = api_response['data']

            with transaction.atomic():
                if result_data['status']==1:
                    ProfileAdvanceReport.objects.update_or_create(
                        mobile=mobile_number,
                        defaults={'result':result_data}
                    )
                update_user_balance(user=user,amount=balance_after_deduction)
            
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            try:
                address =result_data['result']['address']
                return Response(create_response(True,'Data Fetched from external API',{'address':address, 'datetime':datetime.datetime.now().isoformat() + "Z"}),status=status.HTTP_200_OK)
            except:
                return Response(create_response(True,'Data Fetched from external API', {'address':'No Data Found'}), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
       

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_document_data_profile_advance(request):
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
                balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_document_data_profile_advance', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            doc_data=serialized['result']['result']['document_data']
            return Response(create_response(True, "Data fetched from database", {'document_data':doc_data, 'datetime':datetime.datetime.now().isoformat() + "Z"}), status=status.HTTP_200_OK)

    
    try:
        balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_document_data_profile_advance', user=user)
        if balance_after_deduction<0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        api_response = fetch_profile_advance_data(mobile_number)
        
        if api_response.get('success'):
            result_data = api_response['data']

            with transaction.atomic():
                if result_data['status']==1:
                    ProfileAdvanceReport.objects.update_or_create(
                        mobile=mobile_number,
                        defaults={'result':result_data}
                    )
                update_user_balance(user=user,amount=balance_after_deduction)
            
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            try:
                doc_data=result_data['result']['document_data']
                return Response(create_response(True,'Data Fetched from external API',{'document_data':doc_data, 'datetime':datetime.datetime.now().isoformat() + "Z"}),status=status.HTTP_200_OK)
            except:
                return Response(create_response(True,'Data Fetched from external API', {'document_data':'No Data Found'}), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_personal_information_profile_advance(request):
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
                balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_personal_info_profile_advance', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            personal_info=serialized['result']['result']['personal_information']
            return Response(create_response(True, "Data fetched from database", {'personal_information':personal_info, 'datetime':datetime.datetime.now().isoformat() + "Z"}), status=status.HTTP_200_OK)

    
    try:
        balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_personal_info_profile_advance', user=user)
        if balance_after_deduction<0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        api_response = fetch_profile_advance_data(mobile_number)
        
        if api_response.get('success'):
            result_data = api_response['data']

            with transaction.atomic():
                if result_data['status']==1:
                    ProfileAdvanceReport.objects.update_or_create(
                        mobile=mobile_number,
                        defaults={'result':result_data}
                    )
                update_user_balance(user=user,amount=balance_after_deduction)
            
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            try:
                personal_info=result_data['result']['personal_information']
                return Response(create_response(True,'Data Fetched from external API',{'personal_information':personal_info, 'datetime':datetime.datetime.now().isoformat() + "Z"}),status=status.HTTP_200_OK)
            except:
                return Response(create_response(True,'Data Fetched from external API', {'personal_information':'No Data Found'}), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_to_gst_udyam_iec(request):
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
                balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_gst_udyam_iec', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            gst_list=serialized['result']['result']['key_highlights']['gst_numbers']
            udyam_number=serialized['result']['result']['key_highlights']['udyam_numbers']
            iec_number=serialized['result']['result']['key_highlights']['ie_codes']
            return Response(create_response(True, "Data fetched from database", {'gst_list':gst_list, 'udyam_number':udyam_number, 'iec_number':iec_number, 'datetime':datetime.datetime.now().isoformat() + "Z"}), status=status.HTTP_200_OK)

    
    try:
        balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_gst_udyam_iec', user=user)
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
                gst_list=result_data['result']['key_highlights']['gst_numbers']
                udyam_number=result_data['result']['key_highlights']['udyam_numbers']
                iec_number=result_data['result']['key_highlights']['ie_codes']
                return Response(create_response(True,'Data Fetched from external API',{'gst_list':gst_list, 'udyam_number':udyam_number, 'iec_number':iec_number, 'datetime':datetime.datetime.now().isoformat() + "Z"}),status=status.HTTP_200_OK)
            except:
                return Response(create_response(True,'Data Fetched from external API', {'gst_list':'No Data Found', 'udyam_number':'No Data Found', 'iec_number':'No Data Found'}), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_to_uan_esic(request):
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
                balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_esic_uan', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            esic_list=serialized['result']['result']['key_highlights']['esic_number']
            uan_list=serialized['result']['result']['key_highlights']['uan_numbers']
            return Response(create_response(True, "Data fetched from database", {'esic_list':esic_list, 'uan_list':uan_list, 'datetime':datetime.datetime.now().isoformat() + "Z"}), status=status.HTTP_200_OK)


    
    try:
        balance_after_deduction = get_amount_after_api_call(api_name='digital_intelligence_esic_uan', user=user)
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
                esic_list=result_data['result']['key_highlights']['esic_number']
                uan_list=result_data['result']['key_highlights']['uan_numbers']
                return Response(create_response(True,'Data Fetched from external API',{'esic_list':esic_list, 'uan_list':uan_list, 'datetime':datetime.datetime.now().isoformat() + "Z"}),status=status.HTTP_200_OK)
            except:
                return Response(create_response(True,'Data Fetched from external API', {'esic_list':'No Data Found', 'uan_list':'No Data Found'}), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

