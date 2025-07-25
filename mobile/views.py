# views.py
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from payments.models import WalletBalance
from payments.utils import get_amount_after_api_call, update_user_balance
from user_activities.utils import is_called_by_user_previously
from core.utils import create_response, get_token_from_header, get_user_from_token
from django.db import transaction
from user_activities.utils import log_user_activity
from user_activities.models import UserActivity

import datetime

from decimal import Decimal

from .models import (
    AddressTraceReport,
    ChallanReport,
    Mobile360Report,
    RCVerifyReport2,
    UANHistoryReport, 
    UANEmploymentReport,
    ESICReport,
    GSTVerificationReport, 
    GSTTurnoverReport, 
    UdyamReport, 
    ProfileAdvanceReport, 
    EquifaxV3Report,
    MobileToDLLookup,
    MobileToAccountNumber,
    UanWithoutOtp,
    PanAllInOne,
    DigitalPaymentAnalyser,
    LeakOSINT,
    HunterFind,
    HunterVerify,
    UPIToAccount,
    UPIToAccount2,
    RCVerifyReport,
)


from .serializers import (
    Mobile360ReportSerializer, 
    UANHistoryReportSerializer, 
    UANEmploymentReportSerializer, 
    ESICReportSerializer, 
    GSTVerificationReportSerializer, 
    GSTVerificationReportSerializer, 
    UdyamReportSerializer, 
    ProfileAdvanceReportSerializer, 
    EquifaxV3ReportSerializer, 
    GSTTurnoverReportSerializer,
    MobileToAccountNumberSerializer,
    MobileToDLLookupSerializer,
    PanAllInOneSerializer,
    DigitalPaymentAnalyserSerializer,
    LeakOSINTSerializer,
    HunterVerifySerializer,
    HunterFindSerializer,
    UPIToAccountSerializer,
    RCVerifyReportSerializer2,
)

from .utils import (
    fetch_address_tracing_data,
    fetch_challan_data,
    fetch_mobile360_data, 
    fetch_uan_employment_data, 
    fetch_uan_history_data, 
    fetch_esic_data, 
    fetch_gst_data, 
    fetch_gst_turnover_data, 
    fetch_udyam_data, 
    fetch_mobile_to_account_data, 
    fetch_profile_advance_data,
    fetch_equifax_data,
    fetch_mobile_to_dl_data,
    get_uan_dtls_without_otp,
    fetch_pan_all_in_one_data,
    fetch_digital_payment_analyser_data,
    fetch_leak_osint_data,
    fetch_hunter_find_data,
    fetch_hunter_verify_data,
    fetch_upi_to_account,
    fetch_rc_data,
)

from core.tasks import (
    fetch_and_store_address_trace,
    fetch_and_store_challan,
    fetch_and_store_rcverify,
    fetch_and_store_upi_to_account,
)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mobile_360_search(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    mobile_number = request.data.get("mobile_number")
    realtime_data = request.data.get("realtimeData", False)
    
    if not mobile_number:
        return Response(create_response(False, "mobile_number is required", None), status=status.HTTP_400_BAD_REQUEST)
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    # Try fetching from cache/database if realtime is not requested
    api_name = "mobile360"

    if not realtime_data:
        report = Mobile360Report.objects.filter(mobile_number=mobile_number).first()
        if report:
            # Deduct balance if first time call
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name=api_name, user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                print("UPDATING")
                update_user_balance(user=user, amount=balance_after_deduction, api_name=api_name)
                
            # Increment count on successful cached data fetch
            report.count += 1
            report.save(update_fields=['count'])
                
            serialized = Mobile360ReportSerializer(report).data
            log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
    
    try:
        # Balance check and deduction only if realtime call or new fetch
        report = Mobile360Report.objects.filter(mobile_number=mobile_number).first()
        if realtime_data or not report:
            balance_after_deduction = get_amount_after_api_call(api_name=api_name, user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request, UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        # Fetch from external API
        result_data = fetch_mobile360_data(mobile_number)
        
        # Save or update the report and increment count
        with transaction.atomic():
            report, created = Mobile360Report.objects.update_or_create(
                mobile_number=mobile_number,
                defaults={"result": result_data['data']}
            )
            
            # Increment count on successful external API fetch
            if created:
                report.count = 1
            else:
                report.count += 1
            report.save(update_fields=['count'])
            
            # Deduct balance only for realtime or first time external call
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name=api_name)
        
        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(create_response(True, "Data fetched from external API", result_data['data']), status=status.HTTP_200_OK)
        
    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# New API to get mobile number call count
@api_view(["GET"])
# @permission_classes([IsAuthenticated])
def mobile_360_call_count(request):
    mobile_number = request.query_params.get("mobile_number")
    
    if not mobile_number:
        return Response(
            create_response(False, "mobile_number is required", None), 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        report = Mobile360Report.objects.filter(mobile_number=mobile_number).first()
        
        if report:
            count_data = {
                "mobile_number": mobile_number,
                "call_count": report.count,
                "first_called_at": report.created_at,
                "last_updated_at": report.updated_at
            }
            return Response(
                create_response(True, "Call count retrieved successfully", count_data), 
                status=status.HTTP_200_OK
            )
        else:
            count_data = {
                "mobile_number": mobile_number,
                "call_count": 0,
                "first_called_at": None,
                "last_updated_at": None
            }
            return Response(
                create_response(True, "Mobile number not found in records", count_data), 
                status=status.HTTP_200_OK
            )
            
    except Exception as e:
        return Response(
            create_response(False, f"Unexpected error: {str(e)}", None), 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def uan_history_search(request):
#     uan_no_list = request.data.get("uanNoList", [])
#     realtime_data = request.data.get("realtimeData", False)

#     if not uan_no_list or not isinstance(uan_no_list, list):
#         return Response(create_response(False, "uanNoList must be a non-empty list", None), status=status.HTTP_400_BAD_REQUEST)

#     results = []
#     for uan_no in uan_no_list:
#         if not realtime_data:
#             try:
#                 report = UANHistoryReport.objects.get(uan=uan_no)
#                 results.append({
#                     "uan": uan_no,
#                     "source": "database",
#                     "data": UANHistoryReportSerializer(report).data['result']
#                 })
#                 continue
#             except UANHistoryReport.DoesNotExist:
#                 pass

#         # realtime_data = True or fallback to API

#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="uan_history", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")

#         api_response = fetch_uan_history_data(uan_no)
#         if api_response.get("success"):
#             if not is_called or realtime_data:
#                 update_user_balance(user = user, amount = balance_after_deduction)
#             data = api_response["data"]
#             report, _ = UANHistoryReport.objects.update_or_create(
#                 uan=uan_no,
#                 defaults={
#                     "result": data.get("result", {})
#                 }
#             )
#             results.append({
#                 "uan": uan_no,
#                 "source": "external_api",
#                 "data": api_response["data"]['result']
#             })
#         else:
#             results.append({
#                 "uan": uan_no,
#                 "source": "external_api",
#                 "error": "External API did not respond or returned an error."
#             })
#     return Response(create_response(True, "External API did not respond or returned an error." if not api_response.get('success') else  "Data fetched from external API" if realtime_data else "Data fetched from database", results), status=status.HTTP_200_OK if api_response.get("success") else status.HTTP_404_NOT_FOUND)

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def uan_history_search(request):
    uan_no_list = request.data.get("uanNoList", [])
    realtime_data = request.data.get("realtimeData", False)

    if not uan_no_list or not isinstance(uan_no_list, list):
        return Response(create_response(False, "uanNoList must be a non-empty list", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    results = []


    for uan_no in uan_no_list:
        is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=uan_no, full_payload=False)  # unique per UAN if needed
        fetched_from_db = False

        # Try database first if realtime is not required
        if not realtime_data:
            report = UANHistoryReport.objects.filter(uan=uan_no).first()
            if report:
                results.append({
                    "uan": uan_no,
                    "source": "database",
                    "data": UANHistoryReportSerializer(report).data['result']
                })
                fetched_from_db = True

                # Deduct balance if first time call
                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name="uan_history", user=user)
                    if balance_after_deduction < 0.0:
                        log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                    update_user_balance(user=user, amount=balance_after_deduction,api_name="uan_history")

        if fetched_from_db and not realtime_data:
            continue  # Skip external API if fetched from DB and not requesting real-time data

        try:
            balance_after_deduction = get_amount_after_api_call(api_name="uan_history", user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

            api_response = fetch_uan_history_data(uan_no)

            if api_response.get("success"):
                with transaction.atomic():
                    UANHistoryReport.objects.update_or_create(
                        uan=uan_no,
                        defaults={"result": api_response["data"].get("result", {})}
                    )
                    update_user_balance(user=user, amount=balance_after_deduction,api_name="uan_history")

                results.append({
                    "uan": uan_no,
                    "source": "external_api",
                    "data": api_response["data"]["result"]
                })
            else:
                results.append({
                    "uan": uan_no,
                    "source": "external_api",
                    "error": "External API did not respond or returned an error."
                })

        except Exception as e:
            results.append({
                "uan": uan_no,
                "source": "external_api",
                "error": f"Unexpected error: {str(e)}"
            })

    overall_status = status.HTTP_200_OK
    if all('error' in item for item in results):
        overall_status = status.HTTP_404_NOT_FOUND

    if(overall_status == status.HTTP_404_NOT_FOUND):
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
    else:
        log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
    return Response(
        create_response(True, "UAN history search completed.", results),
        status=overall_status
    )


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def uan_employment_search(request):
#     uan_no_list = request.data.get("uanNoList", [])
#     realtime_data = request.data.get("realtimeData", False)

#     if not uan_no_list:
#         return Response(create_response(False, "uanNoList is required", None), status=status.HTTP_400_BAD_REQUEST)

#     results = []


#     for uan in uan_no_list:
#         if not realtime_data:
#             try:
#                 report = UANEmploymentReport.objects.get(uan=uan)
#                 serialized = UANEmploymentReportSerializer(report).data
#                 results.append({"uan": uan, "source": "db", "data": serialized['result']})
#                 continue
#             except UANEmploymentReport.DoesNotExist:
#                 pass
#         else:
#             # Real-time or fallback if DB not found
#             token = get_token_from_header(request)
#             user = get_user_from_token(token)
#             is_called = is_called_by_user_previously(user=user, api_name=request.path)
#             if not is_called or realtime_data:
#                 balance_after_deduction = get_amount_after_api_call(api_name="uan_history_v2", user=user)
#                 if(balance_after_deduction < 0.0):
#                     raise ValidationError("Insufficient balance.")
#             api_response = fetch_uan_employment_data(uan)

#             if api_response.get("success"):
#                 if not is_called or realtime_data:
#                     update_user_balance(user = user, amount = balance_after_deduction)
#                 data = api_response["data"]
#                 report, _ = UANEmploymentReport.objects.update_or_create(
#                     uan=uan,
#                     defaults={
#                         "result": data.get("result", {})
#                     }
#                 )
#                 serialized = UANEmploymentReportSerializer(report).data
#                 results.append({"uan": uan, "source": "api", "data": serialized['result']})
#             else:
#                 results.append({
#                     "uan": uan,
#                     "source": "api",
#                     "error": "API did not respond or returned an error."
#                 })

#     return Response(create_response(True, "Data processed successfully", results), status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def uan_employment_search(request):
    uan_no_list = request.data.get("uanNoList", [])
    realtime_data = request.data.get("realtimeData", False)

    if not uan_no_list or not isinstance(uan_no_list, list):
        return Response(create_response(False, "uanNoList must be a non-empty list", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    results = []

    for uan in uan_no_list:
        is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=uan, full_payload=False)  # Optional: per UAN tracking
        fetched_from_db = False

        if not realtime_data:
            report = UANEmploymentReport.objects.filter(uan=uan).first()
            if report:
                serialized = UANEmploymentReportSerializer(report).data
                results.append({"uan": uan, "source": "db", "data": serialized['result']})
                fetched_from_db = True

                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name="uan_history_v2", user=user)
                    if balance_after_deduction < 0.0:
                        log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                    update_user_balance(user=user, amount=balance_after_deduction,api_name="uan_history_v2")

        if fetched_from_db and not realtime_data:
            continue  # Skip API if already fetched from DB and not requesting real-time data

        try:
            balance_after_deduction = get_amount_after_api_call(api_name="uan_history_v2", user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

            api_response = fetch_uan_employment_data(uan)

            if api_response.get("success"):
                with transaction.atomic():
                    UANEmploymentReport.objects.update_or_create(
                        uan=uan,
                        defaults={"result": api_response["data"].get("result", {})}
                    )
                    update_user_balance(user=user, amount=balance_after_deduction,api_name="uan_history_v2")

                results.append({
                    "uan": uan,
                    "source": "api",
                    "data": api_response["data"]["result"]
                })
            else:
                results.append({
                    "uan": uan,
                    "source": "api",
                    "error": "API did not respond or returned an error."
                })

        except Exception as e:
            results.append({
                "uan": uan,
                "source": "api",
                "error": f"Unexpected error: {str(e)}"
            })

    overall_status = status.HTTP_200_OK
    if all('error' in item for item in results):
        overall_status = status.HTTP_404_NOT_FOUND
    
    if(overall_status == status.HTTP_200_OK):
        log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
    else:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)

    return Response(create_response(True, "UAN employment search completed.", results), status=overall_status)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def esic_search(request):
#     esic_number = request.data.get("esic_number")
#     realtime = request.data.get("realtimeData", False)

#     if not esic_number:
#         return Response(create_response(False, "Missing 'esic_number'", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime:
#         try:
#             report = ESICReport.objects.get(esic_number=esic_number)
#             serialized = ESICReportSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
#         except ESICReport.DoesNotExist:
#             pass
    
#     try:

#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="esic_details", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")

#         fetch_result = fetch_esic_data(esic_number)
#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)

#         # if fetch_result['success']:
#         result_data = fetch_result["data"]
#         ESICReport.objects.update_or_create(
#             esic_number=esic_number,
#             defaults={"result": result_data}
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False,f"Unexpected error: {str(e)}", None), status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def esic_search(request):
    esic_number = request.data.get("esic_number")
    realtime = request.data.get("realtimeData", False)

    if not esic_number:
        return Response(create_response(False, "Missing 'esic_number'", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime:
        report = ESICReport.objects.filter(esic_number=esic_number).first()
        if report:
            serialized = ESICReportSerializer(report).data
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="esic_details", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="esic_details")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="esic_details", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        fetch_result = fetch_esic_data(esic_number)

        if fetch_result.get('success'):
            result_data = fetch_result["data"]
            with transaction.atomic():
                ESICReport.objects.update_or_create(
                    esic_number=esic_number,
                    defaults={"result": result_data}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="esic_details")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def gst_verification_search(request):
#     gst_no = request.data.get("gst_no")
#     realtime_data = request.data.get("realtimeData", False)

#     if not gst_no:
#         return Response(create_response(False, "gst_no is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = GSTVerificationReport.objects.get(gst_no=gst_no)
#             serialized = GSTVerificationReportSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
#         except GSTVerificationReport.DoesNotExist:
#             pass
        
#     try:

#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="gst_advance", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")

#         api_response = fetch_gst_data(gst_no)
#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)

#         # if api_response['success']:
#         result_data = api_response["data"]

#         GSTVerificationReport.objects.update_or_create(
#             gst_no=gst_no,
#             defaults={"result": result_data}
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def gst_verification_search(request):
    gst_no = request.data.get("gst_no")
    realtime_data = request.data.get("realtimeData", False)

    if not gst_no:
        return Response(create_response(False, "gst_no is required", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = GSTVerificationReport.objects.filter(gst_no=gst_no).first()
        if report:
            serialized = GSTVerificationReportSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="gst_advance", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="gst_advance")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="gst_advance", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_gst_data(gst_no)

        if api_response.get('success'):
            result_data = api_response["data"]

            with transaction.atomic():
                GSTVerificationReport.objects.update_or_create(
                    gst_no=gst_no,
                    defaults={"result": result_data}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="gst_advance")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def gst_turnover_search(request):
#     gst_no = request.data.get("gst_no")
#     year = request.data.get("year")
#     realtime_data = request.data.get("realtimeData", False)

#     if not gst_no or not year:
#         return Response(create_response(False, "gst_no and year are required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = GSTTurnoverReport.objects.get(gst_no=gst_no, year=year)
#             serialized = GSTTurnoverReportSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
#         except GSTTurnoverReport.DoesNotExist:
#             pass
#     try:

#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="gst_turnover", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")

#         api_response = fetch_gst_turnover_data(gst_no, year)

#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)

#         result_data = api_response["data"]

#         GSTTurnoverReport.objects.update_or_create(
#             gst_no=gst_no,
#             year=year,
#             defaults={"result": result_data}
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def gst_turnover_search(request):
    gst_no = request.data.get("gst_no")
    year = request.data.get("year")
    realtime_data = request.data.get("realtimeData", False)

    if not gst_no or not year:
        return Response(create_response(False, "gst_no and year are required", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    # Unique tracking per GST and Year if needed
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = GSTTurnoverReport.objects.filter(gst_no=gst_no, year=year).first()
        if report:
            serialized = GSTTurnoverReportSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="gst_turnover", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction,api_name="gst_turnover")
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="gst_turnover", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_gst_turnover_data(gst_no, year)

        if api_response.get('success'):
            result_data = api_response["data"]

            with transaction.atomic():
                GSTTurnoverReport.objects.update_or_create(
                    gst_no=gst_no,
                    year=year,
                    defaults={"result": result_data}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="gst_turnover")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def udyam_verification_search(request):
#     registration_no = request.data.get("registration_no")
#     realtime_data = request.data.get("realtimeData", False)

#     if not registration_no:
#         return Response(create_response(False, "registration_no is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = UdyamReport.objects.get(registration_no=registration_no)
#             serialized = UdyamReportSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
#         except UdyamReport.DoesNotExist:
#             pass
#     try:
#         # Fetch fresh data from external API

#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="verify_udyam", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")


#         api_response = fetch_udyam_data(registration_no)
#         if not is_called or realtime_data: 
#             update_user_balance(user = user, amount = balance_after_deduction)

#         result_data = api_response["data"]
#         UdyamReport.objects.update_or_create(
#             registration_no=registration_no,
#             defaults={"result": result_data}
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def udyam_verification_search(request):
    registration_no = request.data.get("registration_no")
    realtime_data = request.data.get("realtimeData", False)

    if not registration_no:
        return Response(create_response(False, "registration_no is required", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)

    realtime_data = request.data.get("realtimeData", False)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    # Unique tracking per GST and Year if needed
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload )

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = UdyamReport.objects.get(registration_no=registration_no)
        if report:
            serialized = UdyamReportSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="verify_udyam", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="verify_udyam")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="verify_udyam", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_udyam_data(registration_no)

        if api_response.get('success'):
            result_data = api_response["data"]

            with transaction.atomic():
                UdyamReport.objects.update_or_create(
                    registration_no=registration_no,
                    defaults={"result": result_data}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="verify_udyam")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def profile_advance_search(request):
#     mobile = request.data.get("mobile_number")
#     realtime_data = request.data.get("realtimeData", False)

#     if not mobile:
#         return Response(create_response(False, "mobile is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = ProfileAdvanceReport.objects.get(mobile=mobile)
#             serialized = ProfileAdvanceReportSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
#         except ProfileAdvanceReport.DoesNotExist:
#             pass

#     try:
#     # Fetch fresh data from external API
#         token = get_token_from_header(request)
#         user = get_user_from_token(token)

#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="profile_advance", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")

#         api_response = fetch_profile_advance_data(mobile)

#         result_data = api_response["data"]

#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)

#         ProfileAdvanceReport.objects.update_or_create(
#             mobile=mobile,
#             defaults={"result": result_data}
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def profile_advance_search(request):
    mobile = request.data.get("mobile_number")
    realtime_data = request.data.get("realtimeData", False)

    if not mobile:
        return Response(create_response(False, "mobile_number is required", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)

    token = get_token_from_header(request)
    user = get_user_from_token(token)

    # Unique tracking per GST and Year if needed
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = ProfileAdvanceReport.objects.filter(mobile=mobile).first()
        if report:
            serialized = ProfileAdvanceReportSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="profile_advance", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="profile_advance")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        print('Before bal after ded')
        balance_after_deduction = get_amount_after_api_call(api_name="profile_advance", user=user)
        print('After bal after ded')
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        print("Before api resp")
        api_response = fetch_profile_advance_data(mobile)
        print("After api resp")

        if api_response.get('success'):
            result_data = api_response["data"]
            with transaction.atomic():
                if result_data['status']==1:
                    ProfileAdvanceReport.objects.update_or_create(
                        mobile=mobile,
                        defaults={"result": result_data}
                    )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="profile_advance")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def equifax_v3_search(request):
#     mobile = request.data.get("mobile")
#     name = request.data.get("name")
#     id_number = request.data.get("id_number")
#     id_type = request.data.get("id_type")
#     realtime_data = request.data.get("realtimeData", False)

#     if not all([mobile, name, id_number, id_type]):
#         return Response(create_response(False, "Missing one or more required fields: mobile, name, id_number, id_type", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = EquifaxV3Report.objects.get(mobile=mobile)
#             serialized = EquifaxV3ReportSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
#         except EquifaxV3Report.DoesNotExist:
#             pass

#     try:
#         # Fetch from external API

#         token = get_token_from_header(request)
#         user = get_user_from_token(token)

#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="equifax_v3", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")

#         api_response = fetch_equifax_data(id_number, id_type, mobile, name)

#         result_data = api_response["data"]
#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)

#         EquifaxV3Report.objects.update_or_create(
#             mobile=mobile,
#             defaults={
#                 "name": name,
#                 "id_number": id_number,
#                 "id_type": id_type,
#                 "result": result_data
#             }
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def equifax_v3_search(request):
    mobile = request.data.get("mobile")
    name = request.data.get("name")
    id_number = request.data.get("id_number")
    id_type = request.data.get("id_type")
    realtime_data = request.data.get("realtimeData", False)

    if not all([mobile, name, id_number, id_type]):
        return Response(create_response(False, "Missing one or more required fields: mobile, name, id_number, id_type", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = EquifaxV3Report.objects.filter(mobile=mobile).first()
        if report:
            serialized = EquifaxV3ReportSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="equifax_v3", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="equifax_v3")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="equifax_v3", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_equifax_data(id_number, id_type, mobile, name)

        if api_response.get('success'):
            result_data = api_response["data"]

            with transaction.atomic():
                EquifaxV3Report.objects.update_or_create(
                    mobile=mobile,
                    defaults={
                        "name": name,
                        "id_number": id_number,
                        "id_type": id_type,
                        "result": result_data
                    }
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="equifax_v3")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def get_acc_dtls_from_mobile(request):
#     mobile_number = request.data.get("mobile_number")
#     realtime_data = request.data.get("realtimeData", False)

#     if not mobile_number:
#         return Response(create_response(False, "mobile_number is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = MobileToAccountNumber.objects.get(mobile_number=mobile_number)
#             serialized = MobileToAccountNumberSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
#         except MobileToAccountNumber.DoesNotExist:
#             pass

#     try:
#         # Fetch fresh data from external API

#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="mobile_to_account", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")


#         api_response = fetch_mobile_to_account_data(mobile_number)

#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)

#         result_data = api_response["data"]

#         MobileToAccountNumber.objects.update_or_create(
#             mobile_number=mobile_number,
#             defaults={"result": result_data}
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_acc_dtls_from_mobile(request):
    mobile_number = request.data.get("mobile_number")
    realtime_data = request.data.get("realtimeData", False)

    if not mobile_number:
        return Response(create_response(False, "mobile_number is required", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = MobileToAccountNumber.objects.filter(mobile_number=mobile_number).first()
        if report:
            serialized = MobileToAccountNumberSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="mobile_to_account", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="mobile_to_account")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="mobile_to_account", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_mobile_to_account_data(mobile_number)

        if api_response.get('success'):
            result_data = api_response["data"]

            with transaction.atomic():
                MobileToAccountNumber.objects.update_or_create(
                    mobile_number=mobile_number,
                    defaults={"result": result_data}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="mobile_to_account")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def uan_passbook_without_otp(request):
#     uan_no_list = request.data.get("uanNoList", [])
#     realtime_data = request.data.get("realtimeData", False)

#     if not uan_no_list:
#         return Response(create_response(False, "uanNoList is required", None), status=status.HTTP_400_BAD_REQUEST)

#     results = []

#     for uan in uan_no_list:
#         if not realtime_data:
#             try:
#                 report = UanWithoutOtp.objects.get(uan=uan)
#                 serialized = UanWithoutOtpSerializer(report).data
#                 results.append({"uan": uan, "source": "db", "data": serialized['result']})
#                 continue
#             except UanWithoutOtp.DoesNotExist:
#                 pass
        
#         token = get_token_from_header(request)
#         user = get_user_from_token(token)

#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="uan_passbook_without_otp", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")
#         api_response = get_uan_dtls_without_otp(uan)

#         if api_response.get("success"):
#             if not is_called or realtime_data:
#                 update_user_balance(user = user, amount = balance_after_deduction)

#             data = api_response["data"]
#             report, _ = UanWithoutOtp.objects.update_or_create(
#                 uan=uan,
#                 defaults={
#                     "result": data
#                 }
#             )
#             serialized = UanWithoutOtpSerializer(report).data
#             results.append({"uan": uan, "source": "api", "data": serialized['result']})
#         else:
#             results.append({
#                 "uan": uan,
#                 "source": "api",
#                 "error": "API did not respond or returned an error."
#             })

#     return Response(create_response(True, "Data processed successfully", results), status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def uan_passbook_without_otp(request):
    uan_no_list = request.data.get("uanNoList", [])
    realtime_data = request.data.get("realtimeData", False)

    if not uan_no_list or not isinstance(uan_no_list, list):
        return Response(create_response(False, "uanNoList must be a non-empty list", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    results = []

    for uan in uan_no_list:
        is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=uan, full_payload=False)
        fetched_from_db = False

        if not realtime_data:
            report = UanWithoutOtp.objects.filter(uan=uan).first()
            if report:
                serialized = UanWithoutOtpSerializer(report).data
                results.append({"uan": uan, "source": "db", "data": serialized['result']})
                fetched_from_db = True

                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name="uan_passbook_without_otp", user=user)
                    if balance_after_deduction < 0.0:
                        log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                    update_user_balance(user=user, amount=balance_after_deduction, api_name="uan_passbook_without_otp")


        if fetched_from_db and not realtime_data:
            continue  # Skip API if fetched from DB and no real-time requested

        try:
            balance_after_deduction = get_amount_after_api_call(api_name="uan_passbook_without_otp", user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

            api_response = get_uan_dtls_without_otp(uan)

            if api_response.get("success"):
                with transaction.atomic():
                    UanWithoutOtp.objects.update_or_create(
                        uan=uan,
                        defaults={"result": api_response["data"]}
                    )
                    update_user_balance(user=user, amount=balance_after_deduction, api_name="uan_passbook_without_otp")


                results.append({
                    "uan": uan,
                    "source": "api",
                    "data": api_response["data"]
                })
            else:
                results.append({
                    "uan": uan,
                    "source": "api",
                    "error": "API did not respond or returned an error."
                })

        except Exception as e:
            results.append({
                "uan": uan,
                "source": "api",
                "error": f"Unexpected error: {str(e)}"
            })

    overall_status = status.HTTP_200_OK
    if all('error' in item for item in results):
        overall_status = status.HTTP_404_NOT_FOUND

    if(overall_status == status.HTTP_200_OK):
        log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
    else:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
    return Response(
        create_response(True, "UAN passbook without OTP search completed.", results),
        status=overall_status
    )



# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def mobile_to_dl_lookup(request):
#     mobile_number = request.data.get("mobile_number")
#     name = request.data.get("name")
#     dob = request.data.get("dob")
#     realtime_data = request.data.get("realtimeData", False)

#     if not mobile_number or not name or not dob:
#         return Response(create_response(False, "mobile_number and name and dob are required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = MobileToDLLookup.objects.get(mobile_number=mobile_number)
#             serialized = MobileToDLLookupSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
#         except MobileToDLLookup.DoesNotExist:
#             pass

#     try:
#         # Fetch fresh data from external API
#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="mobile_to_dl", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")


#         api_response = fetch_mobile_to_dl_data(mobile_number, name, dob)
#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)

#         result_data = api_response["data"]

#         MobileToDLLookup.objects.update_or_create(
#             mobile_number=mobile_number,
#             defaults={"result": result_data}
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mobile_to_dl_lookup(request):
    mobile_number = request.data.get("mobile_number")
    name = request.data.get("name")
    dob = request.data.get("dob")
    realtime_data = request.data.get("realtimeData", False)

    if not mobile_number or not name or not dob:
        return Response(create_response(False, "mobile_number, name, and dob are required.", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = MobileToDLLookup.objects.filter(mobile_number=mobile_number).first()
        if report:
            serialized = MobileToDLLookupSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="mobile_to_dl", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="mobile_to_dl")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="mobile_to_dl", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_mobile_to_dl_data(mobile_number, name, dob)

        if api_response.get('success'):
            result_data = api_response["data"]

            with transaction.atomic():
                MobileToDLLookup.objects.update_or_create(
                    mobile_number=mobile_number,
                    defaults={"result": result_data}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="mobile_to_dl")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def pan_all_in_one(request):
#     pan_number = request.data.get("pan_number")
#     realtime_data = request.data.get("realtimeData", False)

#     if not pan_number:
#         return Response(create_response(False, "pan_number is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             pan_report = PanAllInOne.objects.get(pan_number=pan_number)
#             serialized = PanAllInOneSerializer(pan_report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
#         except PanAllInOne.DoesNotExist:
#             pass
        
#     try:

#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="pan_all_in_one", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")


#         api_response = fetch_pan_all_in_one_data(pan_number)
#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)
        
#         result_data = api_response["data"]

#         PanAllInOne.objects.update_or_create(
#             pan_number=pan_number,
#             defaults={"result": result_data}
#         )

#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
    
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)
    
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pan_all_in_one(request):
    pan_number = request.data.get("pan_number")
    realtime_data = request.data.get("realtimeData", False)

    if not pan_number:
        return Response(create_response(False, "pan_number is required.", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        pan_report = PanAllInOne.objects.filter(pan_number=pan_number).first()
        if pan_report:
            serialized = PanAllInOneSerializer(pan_report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="pan_all_in_one", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="pan_all_in_one")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="pan_all_in_one", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_pan_all_in_one_data(pan_number)

        if api_response.get('success'):
            result_data = api_response["data"]

            with transaction.atomic():
                PanAllInOne.objects.update_or_create(
                    pan_number=pan_number,
                    defaults={"result": result_data}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="pan_all_in_one")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "External API did not respond or returned an error.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def digital_payment_analyser(request):
#     mobile_number = request.data.get("mobile_number")
#     realtime_data = request.data.get("realtimeData", False)

#     if not mobile_number:
#         return Response(create_response(False, "mobile_number is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = DigitalPaymentAnalyser.objects.get(mobile_number=mobile_number)
#             serialized = DigitalPaymentAnalyserSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

#         except DigitalPaymentAnalyser.DoesNotExist:
#             pass
    
#     try:
#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="digital_payment_id_analyzer", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")

        

#         api_response = fetch_digital_payment_analyser_data(mobile_number=mobile_number)
#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)
#         if api_response:
#             DigitalPaymentAnalyser.objects.update_or_create(
#                 mobile_number=mobile_number,
#                 defaults={"result": api_response}
#             )
#             return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)
        
#         else:
#             return Response(create_response(False, "No digital payments found.", data=None), status=status.HTTP_200_OK)
#     except Exception as e:

#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def digital_payment_analyser(request):
#     mobile_number = request.data.get("mobile_number")
#     realtime_data = request.data.get("realtimeData", False)

#     if not mobile_number:
#         return Response(create_response(False, "mobile_number is required.", None), status=status.HTTP_400_BAD_REQUEST)

#     token = get_token_from_header(request)
#     user = get_user_from_token(token)
#     api_name = request.path

#     payload = json.loads(request.body.decode('utf-8')) if request.body else {}
#     is_called = is_called_by_user_previously(user=user, api_name=request.path,  payload=payload)

#     # Step 1: Try fetching from database if real-time is not required
#     if not realtime_data:
#         report = DigitalPaymentAnalyser.objects.filter(mobile_number=mobile_number).first()
#         if report:
#             serialized = DigitalPaymentAnalyserSerializer(report).data

#             if not is_called:
#                 # balance_after_deduction = get_amount_after_api_call(api_name="digital_payment_id_analyzer", user=user)

#                 user_balance = WalletBalance.objects.get(user=user).balance
#                 balance_after_deduction = user_balance - serialized['billable_count']*6.0
#                 if balance_after_deduction < 0.0:
#                     return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
#                 update_user_balance(user=user, amount=balance_after_deduction)

#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

#     # Step 2: Fallback to external API
#     try:
#         balance_after_deduction = get_amount_after_api_call(api_name="digital_payment_id_analyzer", user=user)
#         if balance_after_deduction < 0.0:
#             return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

#         api_response, billable_count = fetch_digital_payment_analyser_data(mobile_number=mobile_number)

#         price_per_api =Decimal(6.0)
#         billable_amount = billable_count*price_per_api
#         wallet_obj = WalletBalance.objects.get(user=user)
#         update_user_balance(user = user, amount=wallet_obj.balance - billable_amount)

#         if api_response:
#             with transaction.atomic():
#                 DigitalPaymentAnalyser.objects.update_or_create(
#                     mobile_number=mobile_number,
#                     defaults={"result": api_response, billable_count: billable_count}
#                 )
#                 update_user_balance(user=user, amount=balance_after_deduction)

#             return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)
#         else:
#             return Response(create_response(False, "No digital payments found.", None), status=status.HTTP_404_NOT_FOUND)

#     except Exception as e:
#         return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def digital_payment_analyser(request):
    mobile_number = request.data.get("mobile_number")
    realtime_data = request.data.get("realtimeData", False)

    if not mobile_number:
        return Response(create_response(False, "mobile_number is required.", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = DigitalPaymentAnalyser.objects.filter(mobile_number=mobile_number).first()
        if report:
            serialized = DigitalPaymentAnalyserSerializer(report).data

            if not is_called:
                price_per_api = Decimal('6.0')
                user_balance = WalletBalance.objects.get(user=user).balance
                balance_after_deduction = user_balance - Decimal(serialized['billable_count']) * price_per_api

                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

                update_user_balance(user=user, amount=balance_after_deduction, api_name='digital_payment_id_analyzer')

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="digital_payment_id_analyzer", user=user)
        if balance_after_deduction < 0.0:
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response, billable_count = fetch_digital_payment_analyser_data(mobile_number=mobile_number)

        price_per_api = Decimal('6.0')
        billable_amount = Decimal(billable_count) * price_per_api
        wallet_obj = WalletBalance.objects.get(user=user)

        # update_user_balance(user=user, amount=wallet_obj.balance - billable_amount)

        if api_response:
            with transaction.atomic():
                DigitalPaymentAnalyser.objects.update_or_create(
                    mobile_number=mobile_number,
                    defaults={"result": api_response, "billable_count": billable_count}
                )
                update_user_balance(user=user, amount=wallet_obj.balance - billable_amount, api_name='digital_payment_id_analyzer')

                # update_user_balance(user=user, amount=balance_after_deduction)
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)
        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "No digital payments found.", None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def leak_osint(request):
#     request_body = request.data.get("request_body")
#     realtime_data = request.data.get("realtimeData", False)
    
#     if not request_body:
#         return Response(create_response(False, "request_body is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = LeakOSINT.objects.get(request_body=request_body)
#             serialized = LeakOSINTSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

#         except LeakOSINT.DoesNotExist:
#             pass

#     try:
#         token = get_token_from_header(request)
#         user = get_user_from_token(token)
#         is_called = is_called_by_user_previously(user=user, api_name=request.path)
#         if not is_called or realtime_data:
#             balance_after_deduction = get_amount_after_api_call(api_name="breach_info", user=user)
#             if(balance_after_deduction < 0.0):
#                 raise ValidationError("Insufficient balance.")
#         api_response = fetch_leak_osint_data(request_body=request_body)
#         if not is_called or realtime_data:
#             update_user_balance(user = user, amount = balance_after_deduction)
#         LeakOSINT.objects.update_or_create(
#             request_body=request_body,
#             defaults={"result": api_response}
#         )
#         return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)
    
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leak_osint(request):
    request_body = request.data.get("request_body")
    realtime_data = request.data.get("realtimeData", False)

    if not request_body:
        return Response(create_response(False, "request_body is required", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)

    # Step 1: Try fetching from database if real-time is not required
    if not realtime_data:
        report = LeakOSINT.objects.filter(request_body=request_body).first()
        if report:
            serialized = LeakOSINTSerializer(report).data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="breach_info", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                update_user_balance(user=user, amount=balance_after_deduction, api_name="breach_info")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    # Step 2: Fallback to external API
    try:
        balance_after_deduction = get_amount_after_api_call(api_name="breach_info", user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_leak_osint_data(request_body=request_body)

        with transaction.atomic():
            LeakOSINT.objects.update_or_create(
                request_body=request_body,
                defaults={"result": api_response}
            )
            update_user_balance(user=user, amount=balance_after_deduction, api_name="breach_info")


        log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
        return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def hunter_verify(request):
#     email = request.data.get("email")
#     realtime_data = request.data.get("realtimeData", False)

#     if not email:
#         return Response(create_response(False, "email is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = HunterVerify.objects.get(email=email)
#             serialized = HunterVerifySerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

#         except HunterVerify.DoesNotExist:
#             pass

#     try:
#         api_response = fetch_hunter_verify_data(email=email)
#         HunterVerify.objects.update_or_create(
#             email=email,
#             defaults={"result": api_response}
#         )
#         return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, f"Unxpected Error: {str(e)}", None), status=status.HTTP_404_NOT_FOUND)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def hunter_verify(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    email = request.data.get("email")
    realtime_data = request.data.get("realtimeData", False)

    if not email:
        return Response(create_response(False, "email is required", None), status=status.HTTP_400_BAD_REQUEST)
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path,payload=payload)
    
    print("Is Called: ", is_called)

    if not realtime_data:
        report = HunterVerify.objects.filter(email=email).first()
        if report:
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name='hunterverify', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                print("Updating Balance")
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hunterverify")

            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            serialized = HunterVerifySerializer(report).data
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    try:
        if realtime_data or not report:
            balance_after_deduction = get_amount_after_api_call(api_name='hunterverify', user=user)
            if(balance_after_deduction < 0.0):
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_hunter_verify_data(email=email)
        with transaction.atomic():
            HunterVerify.objects.update_or_create(
                email=email,
                defaults={"result": api_response}
            )
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hunterverify")


        log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
        return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unxpected Error: {str(e)}", None), status=status.HTTP_404_NOT_FOUND)

# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def hunter_find(request):
#     email = request.data.get("email")
#     realtime_data = request.data.get("realtimeData", False)

#     if not email:
#         return Response(create_response(False, "email is required", None), status=status.HTTP_400_BAD_REQUEST)

#     if not realtime_data:
#         try:
#             report = HunterFind.objects.get(email=email)
#             serialized = HunterFindSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

#         except HunterFind.DoesNotExist:
#             pass

#     try:
#         api_response = fetch_hunter_find_data(email=email)
#         HunterFind.objects.update_or_create(
#             email=email,
#             defaults={"result": api_response}
#         )
#         return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, f"Unxpected Error: {str(e)}", None), status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def hunter_find(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    email = request.data.get("email")
    realtime_data = request.data.get("realtimeData", False)

    if not email:
        return Response(create_response(False, "email is required", None), status=status.HTTP_400_BAD_REQUEST)

    # payload = json.loads(request.body('utf-8')) if request.body else {}
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    print("Is Called: ", is_called)

    if not realtime_data:
        report = HunterFind.objects.filter(email=email).first()
        if report:
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name='hunterfind',user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                print("Updating Balance")
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hunterfind")


            serialized = HunterFindSerializer(report).data
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    try:
        if realtime_data or not is_called:
            balance_after_deduction = get_amount_after_api_call(api_name='hunterfind', user=user)
            if(balance_after_deduction < 0.0):
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_hunter_find_data(email=email)
        
        with transaction.atomic():
            HunterFind.objects.update_or_create(
                email=email,
                defaults={"result": api_response}
            )
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hunterfind")

        log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
        return Response(create_response(True, "Data fetched from external API", api_response), status=status.HTTP_200_OK)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        return Response(create_response(False, f"Unxpected Error: {str(e)}", None), status=status.HTTP_404_NOT_FOUND)

from django.shortcuts import render
from core.services.email_service import EmailService  # Import the email service

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def send_welcome_email(user):
    # subject = 'Welcome to Our Mobile App!'
    # message = f'Hello abhinav,\nWelcome to our mobile app. We are excited to have you!'
    # success = EmailService.send_email(template_name="welcome_template", to_email="abhinav0427@gmail.com", context={"username": "Abhinav", "site_url": "https://scaninfoga.com"})
    print("Send welcome mail called")
    from core.tasks import send_welcome_email
    send_welcome_email.delay(user_email="abhinav0427@gmail.com", name="Abhinav Srivastava")
    return Response(create_response(True, "Email sent successfully", None))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upi_to_account_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    upi_id = request.data.get('upi_id')
    realtime_data = request.data.get('realtimeData', False)

    if not upi_id:
        return Response(create_response(False, 'upi_id is required', None), status=status.HTTP_400_BAD_REQUEST)

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is Called: ", is_called)

    try:
        obj = UPIToAccount2.objects.get(upi_id=upi_id)
        full_data = obj.result
        latest_entry = obj.result[-1] if obj.result else None
    except UPIToAccount2.DoesNotExist:
        full_data = []
        latest_entry = None
        obj = None

    try:
        count = len(full_data)
        datetime_list = [list(entry.keys())[0] for entry in full_data]
        
        if not realtime_data:
            if latest_entry:
                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name='upi_to_account_data', user=user)
                    if balance_after_deduction < 0.0:
                        log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                    print("UPDATING")
                    update_user_balance(user=user, amount=balance_after_deduction, api_name="upi_to_account_data")


                latest_timestamp = list(latest_entry.keys())[0]
                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Data fetched from database", {
                        "count": count,
                        "datetime_list": datetime_list,
                        "datetime": latest_timestamp,
                        "data": latest_entry[latest_timestamp]
                    }),
                    status=status.HTTP_200_OK
                )

        # For realtime data or when no cached data exists
        if realtime_data or latest_entry is None:
            balance_after_deduction = get_amount_after_api_call(api_name='upi_to_account_data', user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        if latest_entry is None:
            result = fetch_upi_to_account(upi_id)
            print("Latest None then real time: ", result)
            if result.get('success'):
                ts = result["data"].pop("datetime")
                print(result["data"])
                data_dict = {ts: result["data"]}
                
                with transaction.atomic():
                    UPIToAccount2.objects.update_or_create(
                        upi_id=upi_id,
                        defaults={"result": [data_dict]}
                    )
                    
                    if realtime_data or not is_called:
                        update_user_balance(user=user, amount=balance_after_deduction, api_name="upi_to_account_data")

                
                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Real-time data fetched successfully", {
                        "count": 1,
                        "datetime_list": [ts],
                        "datetime": ts,
                        "data": data_dict[ts]
                    }),
                    status=status.HTTP_200_OK
                )
            else:
                log_user_activity(request, UserActivity.Status.FAILED)
                return Response(
                    create_response(False, result.get("message", "Failed to fetch data"), None), 
                    status=status.HTTP_404_NOT_FOUND
                )

        api_response = fetch_upi_to_account(upi_id)
        fetch_and_store_upi_to_account.delay(upi_id, api_response)
        
        with transaction.atomic():
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="upi_to_account_data")

        
        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Data fetched from API, comparing in background.", {
                "count": count,
                "datetime_list": datetime_list,
                "datetime": api_response['data']['datetime'],
                "data": api_response["data"]
            }),
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, f"Unexpected Error: {str(e)}", None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upi_to_account_full_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    upi_id = request.data.get("upi_id")
    
    if not upi_id:
        return Response(
            create_response(False, "Missing upi_id in query parameters", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is Called: ", is_called)

    try:
        data_obj = UPIToAccount2.objects.get(upi_id=upi_id)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in data_obj.result
        ]
        
        if not is_called:
            balance_after_deduction = get_amount_after_api_call(api_name='upi_to_account_full_data', user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
            print("UPDATING")
            update_user_balance(user=user, amount=balance_after_deduction, api_name="upi_to_account_full_data")


        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )
        
    except UPIToAccount2.DoesNotExist:
        print("No data in database, fetching from external api")
        
        balance_after_deduction = get_amount_after_api_call(api_name='upi_to_account_full_data', user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        api_response = fetch_upi_to_account(upi_id)
        if api_response.get('success'):
            ts = api_response["data"].pop("datetime")
            print(api_response["data"])
            data_dict = {ts: api_response["data"]}
            
            with transaction.atomic():
                UPIToAccount2.objects.update_or_create(
                    upi_id=upi_id,
                    defaults={"result": [data_dict]}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="upi_to_account_full_data")

            
            log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(
                create_response(True, "Real-time data fetched successfully", [{
                    "datetime": ts,
                    "data": data_dict[ts]
                }]),
                status=status.HTTP_200_OK
            )
        else:
            log_user_activity(request, UserActivity.Status.FAILED)
            return Response(
                create_response(False, api_response.get("message", "Failed to fetch data"), None), 
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def upi_to_account_data(request):
#     upi_id = request.data.get('upi_id')
#     realtime_data = request.data.get('realtimeData', False)

#     if not upi_id:
#         return Response(create_response(False, 'upi_id is required', None), status=status.HTTP_400_BAD_REQUEST)

#     try:
#         obj = UPIToAccount.objects.get(upi_id=upi_id)
#         full_data = obj.result
#         latest_entry = obj.result[-1] if obj.result else None
#     except UPIToAccount.DoesNotExist:
#         full_data = []
#         latest_entry = None
#         obj = None
#     try:
#         count = len(full_data)
#         datetime_list = [list(entry.keys())[0] for entry in full_data]
        
#         if not realtime_data:
#             if latest_entry:
#                 latest_timestamp = list(latest_entry.keys())[0]
#                 return Response(
#                     create_response(True, "Data fetched from database", {
#                         "count": count,
#                         "datetime_list": datetime_list,
#                         "datetime": latest_timestamp,
#                         "data": latest_entry[latest_timestamp]
#                     }),
#                     status=status.HTTP_200_OK
#                 )
#             else:
#                 pass
        
#         if latest_entry is None:
#             result = fetch_upi_to_account(upi_id)
#             print("Latest None then real time: ",result)
#             if result.get('success'):
#                 ts = result["data"].pop("datetime")
#                 print(result["data"])
#                 data_dict = {ts: result["data"]}
#                 UPIToAccount.objects.update_or_create(
#                     upi_id=upi_id,
#                     defaults={"result": [data_dict]}
#                 )
#                 return Response(
#                     create_response(True, "Real-time data fetched successfully", {
#                         "count": 1,
#                         "datetime_list": [ts],
#                         "datetime": ts,
#                         "data": data_dict[ts]
#                     }),
#                     status=status.HTTP_200_OK
#                 )
#             else:
#                 return Response(
#                     create_response(False, result.get("message", "Failed to fetch data"), None), 
#                     status=status.HTTP_404_NOT_FOUND
#                 )
#     except Exception as e:
#         return Response(
#             create_response(False, f"Unxpected Error: {str(e)}", None),
#             status=status.HTTP_404_NOT_FOUND
#         )
    
#     api_response = fetch_upi_to_account(upi_id)
#     print("API response:", api_response['data'])
#     fetch_and_store_upi_to_account.delay(upi_id, api_response)
    
#     return Response(
#         create_response(True, "Data fetched from API, comparing in background.",{
#             "count": count,
#             "datetime_list": datetime_list,
#             "datetime": api_response['data']['datetime'],
#             "data": api_response["data"]
#         }),
#         status=status.HTTP_200_OK
#     )

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def upi_to_account_full_data(request):
#     upi_id = request.data.get("upi_id")
#     if not upi_id:
#         return Response(
#             create_response(False, "Missing upi_id in query parameters", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     try:
#         data_obj = UPIToAccount.objects.get(upi_id=upi_id)
#         full_data = [
#             {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
#             for entry in data_obj.result
#         ]
#         return Response(
#             create_response(True, "Full data fetched successfully", full_data),
#             status=status.HTTP_200_OK
#         )
#     except UPIToAccount.DoesNotExist:
#         api_response = fetch_upi_to_account(upi_id)
#         if api_response.get('success'):
#             ts = api_response["data"].pop("datetime")
#             print(api_response["data"])
#             data_dict = {ts: api_response["data"]}
#             UPIToAccount.objects.update_or_create(
#                 upi_id=upi_id,
#                 defaults={"result": [data_dict]}
#             )
#             return Response(
#         create_response(True, "Data fetched from API, comparing in background.", [
#                 {
#                     "datetime": ts,
#                     "data": api_response["data"]
#                 }
#             ]),
#             status=status.HTTP_200_OK
#         )
#         else:
#             return Response(
#                 create_response(False, api_response.get("message", "Failed to fetch data"), None), 
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
        
#     except Exception as e:
#         return Response(
#             create_response(False, str(e), None),
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
# def delete_upi_to_account_data(request):
#     upi_id = request.query_params.get('upi_id')
#     if not upi_id:
#         return Response(
#             create_response(False, "Missing?upi_id parameter in query", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     records = UPIToAccount.objects.filter(upi_id=upi_id)
#     count = records.count()   

#     if count == 0:
#         return Response(
#             create_response(False, f'No data found for upi_id: {upi_id}', None),
#             status=status.HTTP_404_NOT_FOUND
#         )

#     records.delete()
#     return Response(
#         create_response(True, f'Successfully deleted {count} record(s) for upi_id: {upi_id}', None),
#         status=status.HTTP_200_OK
#     )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rcverify_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    vehicle_no = request.data.get('vehicle_no')
    realtime_data = request.data.get('realtimeData', False)

    if not vehicle_no:
        return Response(create_response(False, 'vehicle_no is required', None), status=status.HTTP_400_BAD_REQUEST)

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    try:
        obj = RCVerifyReport2.objects.get(vehicle_no=vehicle_no)
        full_data = obj.result
        latest_entry = obj.result[-1] if obj.result else None
    except RCVerifyReport2.DoesNotExist:
        full_data = []
        latest_entry = None
        obj = None

    try:
        count = len(full_data)
        datetime_list = [list(entry.keys())[0] for entry in full_data]

        if not realtime_data:
            if latest_entry:
                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name='rc_verify_data', user=user)
                    if balance_after_deduction < 0.0:
                        log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

                    update_user_balance(user=user, amount=balance_after_deduction, api_name="rc_verify_data")

                latest_timestamp = list(latest_entry.keys())[0]
                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Data fetched from database", {
                        "count": count,
                        "datetime_list": datetime_list,
                        "datetime": latest_timestamp,
                        "data": latest_entry[latest_timestamp]
                    }),
                    status=status.HTTP_200_OK
                )

        # For realtime or no cached data
        if realtime_data or latest_entry is None:
            balance_after_deduction = get_amount_after_api_call(api_name='rc_verify_data', user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        if latest_entry is None:
            result = fetch_rc_data(vehicle_no)
            if result.get('success'):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}

                with transaction.atomic():
                    RCVerifyReport2.objects.update_or_create(
                        vehicle_no=vehicle_no,
                        defaults={"result": [data_dict]}
                    )

                    if realtime_data or not is_called:
                        update_user_balance(user=user, amount=balance_after_deduction, api_name="rc_verify_data")

                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Real-time data fetched successfully", {
                        "count": 1,
                        "datetime_list": [ts],
                        "datetime": ts,
                        "data": data_dict[ts]
                    }),
                    status=status.HTTP_200_OK
                )

        api_response = fetch_rc_data(vehicle_no)
        fetch_and_store_rcverify.delay(vehicle_no, api_response)

        with transaction.atomic():
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="rc_verify_data")

        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Data fetched from API, comparing in background.", {
                "count": count,
                "datetime_list": datetime_list,
                "datetime": api_response['data']['datetime'],
                "data": api_response["data"]
            }),
            status=status.HTTP_200_OK
        )

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, f"Unexpected Error: {str(e)}", None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rcverify_full_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    vehicle_no = request.data.get("vehicle_no")

    if not vehicle_no:
        return Response(
            create_response(False, "Missing vehicle_no in query parameters", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    try:
        data_obj = RCVerifyReport2.objects.get(vehicle_no=vehicle_no)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in data_obj.result
        ]

        if not is_called:
            balance_after_deduction = get_amount_after_api_call(api_name='rc_verify_full_data', user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

            update_user_balance(user=user, amount=balance_after_deduction, api_name="rc_verify_full_data")

        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )

    except RCVerifyReport2.DoesNotExist:
        balance_after_deduction = get_amount_after_api_call(api_name='rc_verify_full_data', user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_rc_data(vehicle_no)
        if api_response.get('success'):
            ts = api_response["data"].pop("datetime")
            data_dict = {ts: api_response["data"]}

            with transaction.atomic():
                RCVerifyReport2.objects.update_or_create(
                    vehicle_no=vehicle_no,
                    defaults={"result": [data_dict]}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="rc_verify_full_data")

            log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(
                create_response(True, "Real-time data fetched successfully", [{
                    "datetime": ts,
                    "data": data_dict[ts]
                }]),
                status=status.HTTP_200_OK
            )
        else:
            log_user_activity(request, UserActivity.Status.FAILED)
            return Response(
                create_response(False, api_response.get("message", "Failed to fetch data"), None), 
                status=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def challan_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    vehicle_no = request.data.get('vehicle_no')
    realtime_data = request.data.get('realtimeData', False)

    if not vehicle_no:
        return Response(create_response(False, 'vehicle_no is required', None), status=status.HTTP_400_BAD_REQUEST)

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    try:
        obj = ChallanReport.objects.get(vehicle_no=vehicle_no)
        full_data = obj.result
        latest_entry = obj.result[-1] if obj.result else None
    except ChallanReport.DoesNotExist:
        full_data = []
        latest_entry = None
        obj = None

    try:
        count = len(full_data)
        datetime_list = [list(entry.keys())[0] for entry in full_data]

        if not realtime_data:
            if latest_entry:
                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name='challan_data', user=user)
                    if balance_after_deduction < 0.0:
                        log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

                    update_user_balance(user=user, amount=balance_after_deduction, api_name="challan_data")

                latest_timestamp = list(latest_entry.keys())[0]
                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Data fetched from database", {
                        "count": count,
                        "datetime_list": datetime_list,
                        "datetime": latest_timestamp,
                        "data": latest_entry[latest_timestamp]
                    }),
                    status=status.HTTP_200_OK
                )

        # realtime or no data
        if realtime_data or latest_entry is None:
            balance_after_deduction = get_amount_after_api_call(api_name='challan_data', user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        if latest_entry is None:
            result = fetch_challan_data(vehicle_no)
            if result.get('success'):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}

                with transaction.atomic():
                    ChallanReport.objects.update_or_create(
                        vehicle_no=vehicle_no,
                        defaults={"result": [data_dict]}
                    )

                    if realtime_data or not is_called:
                        update_user_balance(user=user, amount=balance_after_deduction, api_name="challan_data")

                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Real-time data fetched successfully", {
                        "count": 1,
                        "datetime_list": [ts],
                        "datetime": ts,
                        "data": data_dict[ts]
                    }),
                    status=status.HTTP_200_OK
                )

        api_response = fetch_challan_data(vehicle_no)
        fetch_and_store_challan.delay(vehicle_no, api_response)

        with transaction.atomic():
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="challan_data")

        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Data fetched from API, comparing in background.", {
                "count": count,
                "datetime_list": datetime_list,
                "datetime": api_response['data']['datetime'],
                "data": api_response["data"]
            }),
            status=status.HTTP_200_OK
        )

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, f"Unexpected Error: {str(e)}", None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def challan_full_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    vehicle_no = request.data.get("vehicle_no")

    if not vehicle_no:
        return Response(
            create_response(False, "Missing vehicle_no in query parameters", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    try:
        data_obj = ChallanReport.objects.get(vehicle_no=vehicle_no)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in data_obj.result
        ]

        if not is_called:
            balance_after_deduction = get_amount_after_api_call(api_name='challan_full_data', user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

            update_user_balance(user=user, amount=balance_after_deduction, api_name="challan_full_data")

        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )

    except ChallanReport.DoesNotExist:
        balance_after_deduction = get_amount_after_api_call(api_name='challan_full_data', user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_challan_data(vehicle_no)
        if api_response.get('success'):
            ts = api_response["data"].pop("datetime")
            data_dict = {ts: api_response["data"]}

            with transaction.atomic():
                ChallanReport.objects.update_or_create(
                    vehicle_no=vehicle_no,
                    defaults={"result": [data_dict]}
                )
                update_user_balance(user=user, amount=balance_after_deduction, api_name="challan_full_data")

            log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(
                create_response(True, "Real-time data fetched successfully", [{
                    "datetime": ts,
                    "data": data_dict[ts]
                }]),
                status=status.HTTP_200_OK
            )
        else:
            log_user_activity(request, UserActivity.Status.FAILED)
            return Response(
                create_response(False, api_response.get("message", "Failed to fetch data"), None), 
                status=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def address_trace_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    mobile = request.data.get('mobile')
    realtime_data = request.data.get('realtimeData', False)

    if not mobile:
        return Response(create_response(False, 'mobile is required', None), status=status.HTTP_400_BAD_REQUEST)

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    try:
        obj = AddressTraceReport.objects.get(mobile=mobile)
        full_data = obj.result
        latest_entry = obj.result[-1] if obj.result else None
    except AddressTraceReport.DoesNotExist:
        full_data = []
        latest_entry = None
        obj = None

    try:
        count = len(full_data)
        datetime_list = [list(entry.keys())[0] for entry in full_data]

        if not realtime_data:
            if latest_entry:
                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name='address_trace_data', user=user)
                    if balance_after_deduction < 0.0:
                        log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                    update_user_balance(user=user, amount=balance_after_deduction, api_name="address_trace_data")

                latest_timestamp = list(latest_entry.keys())[0]
                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Data fetched from database", {
                        "count": count,
                        "datetime_list": datetime_list,
                        "datetime": latest_timestamp,
                        "data": latest_entry[latest_timestamp]
                    }),
                    status=status.HTTP_200_OK
                )

        # If realtime OR empty
        balance_after_deduction = get_amount_after_api_call(api_name='address_trace_data', user=user)
        if balance_after_deduction < 0.0:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        if latest_entry is None:
            result = fetch_address_tracing_data(mobile)
            if result.get('success'):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}

                with transaction.atomic():
                    AddressTraceReport.objects.update_or_create(
                        mobile=mobile,
                        defaults={"result": [data_dict]}
                    )
                    if realtime_data or not is_called:
                        update_user_balance(user=user, amount=balance_after_deduction, api_name="address_trace_data")

                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Real-time data fetched successfully", {
                        "count": 1,
                        "datetime_list": [ts],
                        "datetime": ts,
                        "data": data_dict[ts]
                    }),
                    status=status.HTTP_200_OK
                )

        api_response = fetch_address_tracing_data(mobile)
        fetch_and_store_address_trace.delay(mobile, api_response)

        with transaction.atomic():
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="address_trace_data")

        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Data fetched from API, comparing in background.", {
                "count": count,
                "datetime_list": datetime_list,
                "datetime": api_response['data']['datetime'],
                "data": api_response["data"]
            }),
            status=status.HTTP_200_OK
        )

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def address_trace_full_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    mobile = request.data.get("mobile")

    if not mobile:
        return Response(
            create_response(False, "Missing mobile in request", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    try:
        obj = AddressTraceReport.objects.get(mobile=mobile)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in obj.result
        ]

        if not is_called:
            balance_after_deduction = get_amount_after_api_call(api_name='address_trace_full_data', user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
            update_user_balance(user=user, amount=balance_after_deduction, api_name="address_trace_full_data")

        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )

    except AddressTraceReport.DoesNotExist:
        try:
            balance_after_deduction = get_amount_after_api_call(api_name='address_trace_full_data', user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

            api_response = fetch_address_tracing_data(mobile)
            if api_response.get('success'):
                ts = api_response["data"].pop("datetime")
                data_dict = {ts: api_response["data"]}

                with transaction.atomic():
                    AddressTraceReport.objects.update_or_create(
                        mobile=mobile,
                        defaults={"result": [data_dict]}
                    )
                    update_user_balance(user=user, amount=balance_after_deduction, api_name="address_trace_full_data")

                log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Real-time data fetched successfully", [{
                        "datetime": ts,
                        "data": data_dict[ts]
                    }]),
                    status=status.HTTP_200_OK
                )
            else:
                log_user_activity(request, UserActivity.Status.FAILED)
                return Response(
                    create_response(False, api_response.get("message", "Failed to fetch data"), None), 
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            log_user_activity(request, UserActivity.Status.FAILED)
            return Response(
                create_response(False, str(e), None),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

