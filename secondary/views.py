import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.utils import timezone
from rest_framework.views import APIView
from core.utils import create_response
from django.core.cache import cache
import urllib.parse

from .models import PayworldData2, RazorpayIFSCData, PaynearbyData, RazorpayIFSCData2
from core.tasks import fetch_and_store_payworld_data, fetch_and_store_razorpay_data, fetch_and_store_paynearby_data
from .utils import fetch_payworld_data, fetch_rapid_search_data, fetch_razorpay_ifsc_data, fetch_paynearby_data
from core.utils import create_response

from user_activities.utils import is_called_by_user_previously, log_user_activity
from core.utils import create_response, get_token_from_header, get_user_from_token
from payments.utils import get_amount_after_api_call, update_user_balance

from django.db import transaction
from user_activities.models import UserActivity


@api_view(['POST'])
def set_cookie(request):
    cookie = request.data.get("cookie")
    if not cookie:
        return Response(create_response(False, "Cookie value is required", None), status=400)
    try:
        cache.set("cookie_payworld", {
            "cookie": cookie,
            "timestamp": timezone.now().isoformat(),
        }, timeout=14400)   # 4 hours
        return Response(create_response(True, "Cookie saved successfully", None), status=200)
    except Exception as e:
        return Response(create_response(False, str(e), None), status=500)


@api_view(['POST'])
def set_paynearby_credentials(request):
    token = request.data.get("token")
    token = f"Bearer {token}"
    lat=request.data.get("latitude")
    lng=request.data.get("longitude")
    
    if not token or not lat or not lng:
        return Response(create_response(False, "Token, latitude, and longitude are required", None), status=400)
    try:
        cache.set("paynearby_credentials", {
            "token": token,
            "lat": lat,
            "lng": lng,
            "timestamp": timezone.now().isoformat(),
        }, timeout=14400)   # 4 hours
        return Response(create_response(True, "Credentials saved successfully", None), status=200)
    except Exception as e:
        return Response(create_response(False, str(e), None), status=500)

# @api_view(['POST'])
# def payworld_data(request):
#     sender_mobile = request.data.get("sender_mobile")
#     realtime_data = request.data.get("realtimeData")

#     if not sender_mobile:
#         return Response(create_response(False, "Sender mobile number is required", None), status=status.HTTP_400_BAD_REQUEST)

#     try:
#         obj = PayworldData.objects.get(sender_mobile_number=sender_mobile)
#         latest_entry = obj.result[-1] if obj.result else None
#     except PayworldData.DoesNotExist:
#         obj = None
#         latest_entry = None

#     if not realtime_data:
#         if latest_entry:
#             latest_timestamp = list(latest_entry.keys())[0]
#             return Response(create_response(True, "Data fetched from database", {
#                 "datetime": latest_timestamp,
#                 "data": latest_entry[latest_timestamp]
#             }), status=200)
#         else:
#             return Response(create_response(False, "No data found", None), status=404)

#     if latest_entry is None:
#         result = fetch_payworld_data(sender_mobile)
#         if result.get("status"):
#             ts = result["data"].pop("datetime")
#             data_dict = {ts: result["data"]}
#             PayworldData.objects.update_or_create(
#                 sender_mobile_number=sender_mobile,
#                 defaults={"result": [data_dict]}
#             )
#             return Response(create_response(True, "Real-time data fetched successfully", {
#                 "datetime": ts,
#                 "data": data_dict[ts]
#             }), status=status.HTTP_200_OK)
#         else:
#             return Response(create_response(False, result.get("message", "Failed to fetch data"), None), status=500)

#     api_response = fetch_payworld_data(sender_mobile)
#     fetch_and_store_payworld_data.delay(sender_mobile,api_response)
#     return Response(create_response(True, "Data fetched from API, comparing in background.", {
#         "datetime": datetime.datetime.now().isoformat() + "Z",
#         "data": api_response["data"]
#     }), status=status.HTTP_200_OK)


@api_view(['POST'])
def payworld_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    sender_mobile = request.data.get("sender_mobile")
    realtime_data = request.data.get("realtimeData")

    if not sender_mobile:
        return Response(
            create_response(False, "Sender mobile number is required", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is Called: ", is_called)

    try:
        obj = PayworldData2.objects.get(sender_mobile_number=sender_mobile)
        full_data = obj.result
        latest_entry = full_data[-1] if full_data else None
    except PayworldData2.DoesNotExist:
        obj = None
        full_data = []
        latest_entry = None

    try:
        count = len(full_data)
        datetime_list = [list(entry.keys())[0] for entry in full_data]

        if not realtime_data:
            if latest_entry:
                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name='secondary_payworld_data', user=user)
                    if balance_after_deduction < 0.0:
                        # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                    print("UPDATING")
                    update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_payworld_data')

                latest_timestamp = list(latest_entry.keys())[0]
                # log_user_activity(request, UserActivity.Status.SUCCESS)
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
            balance_after_deduction = get_amount_after_api_call(api_name='secondary_payworld_data', user=user)
            if balance_after_deduction < 0.0:
                # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        if latest_entry is None:
            result = fetch_payworld_data(sender_mobile)
            if result.get("status"):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}
                
                with transaction.atomic():
                    PayworldData2.objects.update_or_create(
                        sender_mobile_number=sender_mobile,
                        defaults={"result": [data_dict]}
                    )
                    
                    if realtime_data or not is_called:
                        update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_payworld_data')

                
                # log_user_activity(request, UserActivity.Status.SUCCESS)
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
                # log_user_activity(request, UserActivity.Status.FAILED)
                return Response(
                    create_response(False, result.get("message", "Failed to fetch data"), None),
                    status=status.HTTP_404_NOT_FOUND
                )

        api_response = fetch_payworld_data(sender_mobile)
        fetch_and_store_payworld_data.delay(sender_mobile, api_response)

        with transaction.atomic():
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_payworld_data')

        
        # log_user_activity(request, UserActivity.Status.SUCCESS)
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
        # log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def get_full_payworld_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    sender_mobile = request.data.get("sender_mobile")
    
    if not sender_mobile:
        return Response(
            create_response(False, "Missing sender_mobile in query parameters", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is Called: ", is_called)

    try:
        data_obj = PayworldData2.objects.get(sender_mobile_number=sender_mobile)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in data_obj.result
        ]
        
        if not is_called:
            balance_after_deduction = get_amount_after_api_call(api_name='secondary_payworld_all_data', user=user)
            if balance_after_deduction < 0.0:
                # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
            print("UPDATING")
            update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_payworld_all_data')


        # log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )
        
    except PayworldData2.DoesNotExist:
        print("No data in database, fetching from external api")
        
        balance_after_deduction = get_amount_after_api_call(api_name='secondary_payworld_all_data', user=user)
        if balance_after_deduction < 0.0:
            # log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        result = fetch_payworld_data(sender_mobile)
        if result.get("status"):
            ts = result["data"].pop("datetime")
            data_dict = {ts: result["data"]}
            
            with transaction.atomic():
                PayworldData2.objects.update_or_create(
                    sender_mobile_number=sender_mobile,
                    defaults={"result": [data_dict]}
                )
                update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_payworld_all_data')

            
            # log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(
                create_response(True, "Real-time data fetched successfully", [{
                    "datetime": ts,
                    "data": data_dict[ts]
                }]),
                status=status.HTTP_200_OK
            )
        else:
            # log_user_activity(request, UserActivity.Status.FAILED)
            return Response(
                create_response(False, result.get("message", "Failed to fetch data"), None),
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        # log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





# @api_view(['POST'])
# def payworld_data(request):
#     sender_mobile = request.data.get("sender_mobile")
#     realtime_data = request.data.get("realtimeData")

#     if not sender_mobile:
#         return Response(
#             create_response(False, "Sender mobile number is required", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     try:
#         obj = PayworldData2.objects.get(sender_mobile_number=sender_mobile)
#         full_data = obj.result
#         latest_entry = full_data[-1] if full_data else None
#     except PayworldData2.DoesNotExist:
#         obj = None
#         full_data = []
#         latest_entry = None

    
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
#             result = fetch_payworld_data(sender_mobile)
#             if result.get("status"):
#                 ts = result["data"].pop("datetime")
#                 data_dict = {ts: result["data"]}
#                 PayworldData2.objects.update_or_create(
#                     sender_mobile_number=sender_mobile,
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

#         api_response = fetch_payworld_data(sender_mobile)
#         fetch_and_store_payworld_data.delay(sender_mobile, api_response)

#         return Response(
#             create_response(True, "Data fetched from API, comparing in background.", {
#                 "count": count,
#                 "datetime_list": datetime_list,
#                 "datetime": api_response['data']['datetime'],
#                 "data": api_response["data"]
#             }),
#             status=status.HTTP_200_OK
#         )
    
#     except Exception as e:
#         return Response(
#             create_response(False, str(e), None),
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


# @api_view(['POST'])
# def get_full_payworld_data(request):
#     sender_mobile = request.data.get("sender_mobile")
#     if not sender_mobile:
#         return Response(
#             create_response(False, "Missing sender_mobile in query parameters", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     try:
#         data_obj = PayworldData2.objects.get(sender_mobile_number=sender_mobile)
#         full_data = [
#             {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
#             for entry in data_obj.result
#         ]
#         return Response(
#             create_response(True, "Full data fetched successfully", full_data),
#             status=status.HTTP_200_OK
#         )
#     except PayworldData2.DoesNotExist:
#         result = fetch_payworld_data(sender_mobile)
#         if result.get("status"):
#             ts = result["data"].pop("datetime")
#             data_dict = {ts: result["data"]}
#             PayworldData2.objects.update_or_create(
#                 sender_mobile_number=sender_mobile,
#                 defaults={"result": [data_dict]}
#             )
#             return Response(
#                 create_response(True, "Real-time data fetched successfully", [{
#                     "datetime": ts,
#                     "data": data_dict[ts]
#                 }]),
#                 status=status.HTTP_200_OK
#             )
#         else:
#             return Response(
#                 create_response(False, result.get("message", "Failed to fetch data"), None),
#                 status=status.HTTP_404_NOT_FOUND
#             )

# @api_view(['DELETE'])
# def delete_payworld_data(request):
#     mobile = request.query_params.get('mobile')
#     if not mobile:
#         return Response(
#             create_response(False, "Missing ?mobile parameter in query", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     records = PayworldData.objects.filter(sender_mobile_number=mobile)
#     count = records.count()

#     if count == 0:
#         return Response(
#             create_response(False, f'No data found for mobile: {mobile}', None),
#             status=status.HTTP_404_NOT_FOUND
#         )

#     records.delete()
#     return Response(
#         create_response(True, f'Successfully deleted {count} record(s) for mobile: {mobile}', None),
#         status=status.HTTP_200_OK
#     )

# @api_view(['POST'])
# def razorpay_ifsc_data(request):
#     ifsc_code = request.data.get("ifsc_code")
#     realtime_data = request.data.get("realtimeData")
#     if not ifsc_code:
#         return Response(create_response(False, "IFSC code is required", None), status=status.HTTP_400_BAD_REQUEST)

#     try:
#         obj = RazorpayIFSCData.objects.get(ifsc_code=ifsc_code)
#         latest_entry = obj.result[-1] if obj.result else None
#     except RazorpayIFSCData.DoesNotExist:
#         obj = None
#         latest_entry = None

#     if not realtime_data:
#         if latest_entry:
#             latest_timestamp = list(latest_entry.keys())[0]
#             return Response(create_response(True, "Data fetched from database", {
#                 "datetime": latest_timestamp,
#                 "data": latest_entry[latest_timestamp]
#             }), status=200)
#         else:
#             return Response(create_response(False, "No data found", None), status=404)

#     if latest_entry is None:
#         result = fetch_razorpay_ifsc_data(ifsc_code)
#         print(result) # Add this line to print the result
#         if result.get("status"):
#             ts = result["data"].pop("datetime")
#             data_dict = {ts: result["data"]}
#             RazorpayIFSCData.objects.update_or_create(
#                 ifsc_code=ifsc_code,
#                 defaults={"result": [data_dict]}
#             )
#             return Response(create_response(True, "Real-time data fetched successfully", {
#                 "datetime": ts,
#                 "data": data_dict[ts]
#             }), status=status.HTTP_200_OK)
#         else:
#             print('here')
#             return Response(create_response(False, result.get("message", "Failed to fetch data"), None), status=500)
        
#     api_response = fetch_razorpay_ifsc_data(ifsc_code)
#     fetch_and_store_razorpay_data.delay(ifsc_code,api_response)
#     return Response(create_response(True, "Data fetched from API, comparing in background.", {
#         "datetime": datetime.datetime.now().isoformat() + "Z",
#         "data": api_response["data"]
#     }), status=status.HTTP_200_OK)


@api_view(['POST'])
def razorpay_ifsc_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    ifsc_code = request.data.get("ifsc_code")
    realtime_data = request.data.get("realtimeData")
    
    if not ifsc_code:
        return Response(create_response(False, "IFSC code is required", None), status=status.HTTP_400_BAD_REQUEST)

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is Called: ", is_called)

    try:
        obj = RazorpayIFSCData2.objects.get(ifsc_code=ifsc_code)
        full_data = obj.result
        latest_entry = obj.result[-1] if obj.result else None
    except RazorpayIFSCData2.DoesNotExist:
        obj = None
        full_data = []
        latest_entry = None
    
    try:
        count = len(full_data)
        datetime_list = [list(entry.keys())[0] for entry in full_data]

        if not realtime_data:
            if latest_entry:
                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name='secondary_ifsc_data', user=user)
                    if balance_after_deduction < 0.0:
                        # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                    print("UPDATING")
                    update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_ifsc_data')


                latest_timestamp = list(latest_entry.keys())[0]
                # log_user_activity(request, UserActivity.Status.SUCCESS)
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
            balance_after_deduction = get_amount_after_api_call(api_name='secondary_ifsc_data', user=user)
            if balance_after_deduction < 0.0:
                # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        if latest_entry is None:
            result = fetch_razorpay_ifsc_data(ifsc_code)
            if result.get("status"):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}
                
                with transaction.atomic():
                    RazorpayIFSCData2.objects.update_or_create(
                        ifsc_code=ifsc_code,
                        defaults={"result": [data_dict]}
                    )
                    
                    if realtime_data or not is_called:
                        update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_ifsc_data')

                
                # log_user_activity(request, UserActivity.Status.SUCCESS)
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
                # log_user_activity(request, UserActivity.Status.FAILED)
                return Response(
                    create_response(False, result.get("message", "Failed to fetch data"), None), 
                    status=status.HTTP_404_NOT_FOUND
                )
            
        api_response = fetch_razorpay_ifsc_data(ifsc_code)
        fetch_and_store_razorpay_data.delay(ifsc_code, api_response)
        
        with transaction.atomic():
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_ifsc_data')

        
        # log_user_activity(request, UserActivity.Status.SUCCESS)
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
        # log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def get_full_razorpay_ifsc_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    ifsc_code = request.data.get("ifsc_code")
    
    if not ifsc_code:
        return Response(
            create_response(False, "Missing ifsc_code in query parameters", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is Called: ", is_called)

    try:
        data_obj = RazorpayIFSCData2.objects.get(ifsc_code=ifsc_code)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in data_obj.result
        ]
        
        if not is_called:
            balance_after_deduction = get_amount_after_api_call(api_name='secondary_ifsc_all_data', user=user)
            if balance_after_deduction < 0.0:
                # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
            print("UPDATING")
            update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_ifsc_all_data')

        # log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )
        
    except RazorpayIFSCData2.DoesNotExist:
        print("no data fetching from external")
        
        balance_after_deduction = get_amount_after_api_call(api_name='secondary_ifsc_all_data', user=user)
        if balance_after_deduction < 0.0:
            # log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        result = fetch_razorpay_ifsc_data(ifsc_code)
        if result.get("status"):
            ts = result["data"].pop("datetime")
            data_dict = {ts: result["data"]}
            
            with transaction.atomic():
                RazorpayIFSCData2.objects.update_or_create(
                    ifsc_code=ifsc_code,
                    defaults={"result": [data_dict]}
                )
                update_user_balance(user=user, amount=balance_after_deduction,api_name='secondary_ifsc_all_data')

            
            # log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(
                create_response(True, "Real-time data fetched successfully", [{
                    "datetime": ts,
                    "data": data_dict[ts]
                }]),
                status=status.HTTP_200_OK
            )
        else:
            # log_user_activity(request, UserActivity.Status.FAILED)
            return Response(
                create_response(False, result.get("message", "Failed to fetch data"), None), 
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        # log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# @api_view(['POST'])
# def razorpay_ifsc_data(request):
#     ifsc_code = request.data.get("ifsc_code")
#     realtime_data = request.data.get("realtimeData")
#     if not ifsc_code:
#         return Response(create_response(False, "IFSC code is required", None), status=status.HTTP_400_BAD_REQUEST)

#     try:
#         obj = RazorpayIFSCData.objects.get(ifsc_code=ifsc_code)
#         full_data = obj.result
#         latest_entry = obj.result[-1] if obj.result else None
#     except RazorpayIFSCData.DoesNotExist:
#         obj = None
#         full_data = []
#         latest_entry = None
    
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
#             result = fetch_razorpay_ifsc_data(ifsc_code)
#             if result.get("status"):
#                 ts = result["data"].pop("datetime")
#                 data_dict = {ts: result["data"]}
#                 RazorpayIFSCData.objects.update_or_create(
#                     ifsc_code=ifsc_code,
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
            
#         api_response = fetch_razorpay_ifsc_data(ifsc_code)
#         fetch_and_store_razorpay_data.delay(ifsc_code,api_response)
        
#         return Response(
#             create_response(True, "Data fetched from API, comparing in background.", {
#                 "count": count,
#                 "datetime_list": datetime_list,
#                 "datetime": api_response['data']['datetime'],
#                 "data": api_response["data"]
#             }),
#             status=status.HTTP_200_OK
#         )
    
#     except Exception as e:
#         return Response(
#             create_response(False, str(e), None),
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )
    


# @api_view(['POST'])
# def get_full_razorpay_ifsc_data(request):
#     ifsc_code = request.data.get("ifsc_code")
#     if not ifsc_code:
#         return Response(
#             create_response(False, "Missing ifsc_code in query parameters", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     try:
#         data_obj = RazorpayIFSCData.objects.get(ifsc_code=ifsc_code)
#         full_data = [
#             {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
#             for entry in data_obj.result
#         ]
#         return Response(
#             create_response(True, "Full data fetched successfully", full_data),
#             status=status.HTTP_200_OK
#         )
#     except RazorpayIFSCData.DoesNotExist:
#         print("no data fetching from external")
#         result = fetch_razorpay_ifsc_data(ifsc_code)
#         if result.get("status"):
#                 ts = result["data"].pop("datetime")
#                 data_dict = {ts: result["data"]}
#                 RazorpayIFSCData.objects.update_or_create(
#                     ifsc_code=ifsc_code,
#                     defaults={"result": [data_dict]}
#                 )
#                 return Response(
#                     create_response(True, "Real-time data fetched successfully", [{
#                         "datetime": ts,
#                         "data": data_dict[ts]
#                     }]),
#                     status=status.HTTP_200_OK
#                 )
#         else:
#             return Response(
#                 create_response(False, result.get("message", "Failed to fetch data"), None), 
#                 status=status.HTTP_404_NOT_FOUND
#             )
            
#     except Exception as e:
#         return Response(
#             create_response(False, str(e), None),
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )

@api_view(['POST'])
def paynearby_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    mobile_number = request.data.get("mobile_number")
    realtime_data = request.data.get("realtimeData")

    if not mobile_number:
        return Response(create_response(False, "Mobile Number is required", None), status=status.HTTP_400_BAD_REQUEST)
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path,payload=payload)
    
    print("Is Called: ", is_called)
    
    try:
        obj = PaynearbyData.objects.get(mobile_number=mobile_number)
        full_data = obj.result
        latest_entry = obj.result[-1] if obj.result else None
    except:
        obj = None
        full_data =[]
        latest_entry = None
    
    try:
        count = len(full_data)
        datetime_list = [list(entry.keys())[0] for entry in full_data]
        
        if not realtime_data:
            if latest_entry:
                if not is_called:
                    balance_after_deduction = get_amount_after_api_call(api_name='secondary_paynear_by_data', user=user)
                    if balance_after_deduction<0.0:
                        # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                        return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                    print("UPDATING")
                    update_user_balance(user=user, amount=balance_after_deduction, api_name='secondary_paynear_by_data')

                
                latest_timestamp = list(latest_entry.keys())[0]
                # log_user_activity(request, UserActivity.Status.SUCCESS)
                return Response(
                    create_response(True, "Data fetched from database", {
                        "count": count,
                        "datetime_list": datetime_list,
                        "datetime": latest_timestamp,
                        "data": latest_entry[latest_timestamp]
                    }),
                    status=status.HTTP_200_OK
                )
        
        if realtime_data or latest_entry is None:
            balance_after_deduction = get_amount_after_api_call(api_name='secondary_paynear_by_data', user=user)
            if balance_after_deduction < 0.0:
                # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        if latest_entry is None:
            result = fetch_paynearby_data(mobile_number=mobile_number)
            if result.get("status"):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}
                
                with transaction.atomic():
                    PaynearbyData.objects.update_or_create(
                        mobile_number=mobile_number,
                        defaults={"result": [data_dict]}
                    )
                    
                    if realtime_data or not is_called:
                        update_user_balance(user=user, amount=balance_after_deduction, api_name='secondary_paynear_by_data')

                
                # log_user_activity(request, UserActivity.Status.SUCCESS)
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
                # log_user_activity(request, UserActivity.Status.FAILED)
                return Response(
                    create_response(False, result.get("message", "Failed to fetch data"), None), 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        api_response = fetch_paynearby_data(mobile_number=mobile_number)
        fetch_and_store_paynearby_data.delay(mobile_number, api_response)
        
        with transaction.atomic():
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name='secondary_paynear_by_data')

        
        # log_user_activity(request, UserActivity.Status.SUCCESS)
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
        # log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def get_full_paynearby_data(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    mobile_number = request.data.get("mobile_number")
    
    if not mobile_number:
        return Response(create_response(False, "Mobile Number is required", None), status=status.HTTP_400_BAD_REQUEST)
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)

    print("Is Called: ", is_called)

    try:
        data_obj = PaynearbyData.objects.get(mobile_number=mobile_number)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in data_obj.result
        ]
        
        if not is_called:
            balance_after_deduction = get_amount_after_api_call(api_name='secondary_paynear_by_all_data', user=user)
            if balance_after_deduction < 0.0:
                # log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
            print("UPDATING")
            update_user_balance(user=user, amount=balance_after_deduction, api_name='secondary_paynear_by_all_data')


        # log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )
    
    except PaynearbyData.DoesNotExist:
        print("No data in database, fetching from external api")
        
        balance_after_deduction = get_amount_after_api_call(api_name='secondary_paynear_by_all_data', user=user)
        if balance_after_deduction<0.0:
            # log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        result = fetch_paynearby_data(mobile_number=mobile_number)
        if result.get('status'):
            ts = result["data"].pop("datetime")
            data_dict = {ts: result["data"]}
            
            with transaction.atomic():
                PaynearbyData.objects.update_or_create(
                    mobile_number=mobile_number,
                    defaults={"result": [data_dict]}
                )
                update_user_balance(user=user,amount=balance_after_deduction, api_name='secondary_paynear_by_all_data')

            
            # log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(
                create_response(True, "Real-time data fetched successfully", [{
                    "datetime": ts,
                    "data": data_dict[ts]
                }]),
                status=status.HTTP_200_OK
            )
        else:
            # log_user_activity(request, UserActivity.Status.FAILED)
            return Response(
                create_response(False, result.get("message", "Failed to fetch data"), None), 
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        # log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_rapid_search_data(request):
    token=get_token_from_header(request=request)
    user=get_user_from_token(token)
    query = request.data.get('query')
    query = urllib.parse.quote(query)
    
    if not query:
        return Response(create_response(False, 'query is required', None), status=status.HTTP_400_BAD_REQUEST)

    # payload = request.data
    # is_called = is_called_by_user_previously(user=user,api_name=request.path,payload=payload)

    try:
        api_response = fetch_rapid_search_data(query)
        response_data=api_response['data']
        
        if response_data:
            balance_after_deduction = get_amount_after_api_call(api_name='rapid_search', user=user)
            if balance_after_deduction<0.0:
                log_user_activity(request=request, status=UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
            
            update_user_balance(user=user, amount=balance_after_deduction, api_name='rapid_search')
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from api.", response_data), status=status.HTTP_200_OK)
        else:
            log_user_activity(request=request, status=UserActivity.Status.FAILED)
            return Response(create_response(False, "No data found.", None), status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    
    