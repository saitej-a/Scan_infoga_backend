import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from user_activities.models import UserActivity
from .models import HudsonRockData, SearchByEmail, SearchByIP, SearchByUsername, SearchByDomain
# from drf_yasg.utils import swagger_auto_schema
from .serializers import HudsonRockDataSerializer, SearchByEmailSerializer, SearchByIPSerializer, SearchByUsernameSerializer, SearchByDomainSerializer
from payments.utils import get_amount_after_api_call, update_user_balance
from user_activities.utils import is_called_by_user_previously, log_user_activity
from core.utils import create_response, get_token_from_header, get_user_from_token
from .utils import fetch_hudson_search_by_email, fetch_hudson_search_by_ip, fetch_hudson_search_by_domain, fetch_hudson_search_by_username
from django.db import transaction


@api_view(['POST'])
def save_hudson_data(request):
    try:
        data = request.data
        data_type = data.pop('type', None)
        
        if not data or not data_type:
            return Response(
                create_response(
                    status=False,
                    message="Data and type are required",
                    data=None
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add the type field to the data
        data['data_type'] = data_type
        
        serializer = HudsonRockDataSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                create_response(
                    status=True,
                    message="Data saved successfully",
                    data=serializer.data
                ),
                status=status.HTTP_201_CREATED
            )
        return Response(
            create_response(
                status=False,
                message="Invalid data",
                data=serializer.errors
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            create_response(
                status=False,
                message=str(e),
                data=None
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def get_hudson_data(request):
    try:
        data_type = request.GET.get('type')
        value = request.GET.get('value')
        
        if not data_type:
            return Response(
                create_response(
                    status=False,
                    message="Type parameter is required",
                    data=None
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        # Query based on data_type
        data = HudsonRockData.objects.filter(data_type=data_type)
        
        # If value is provided, filter by it
        if value:
            if data_type == 'email':
                # First get all records
                all_data = data.all()
                # Then filter in Python
                filtered_data = [
                    record for record in all_data
                    if any(
                        value.lower() in str(cred.get('username', '')).lower() 
                        for cred in record.credentials
                    )
                ]
                data = filtered_data
        
        # Use serializer appropriately based on whether data is filtered
        if isinstance(data, list):
            serializer = HudsonRockDataSerializer(data, many=True)
        else:
            serializer = HudsonRockDataSerializer(data.all(), many=True)
            
        return Response(
            create_response(
                status=True,
                message="Data retrieved successfully",
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            create_response(
                status=False,
                message=str(e),
                data=None
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def search_by_email(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    email = request.data.get("email")
    realtime_data = request.data.get("realtimeData")

    if not email:
        return Response(create_response(status=False, message="Email is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print("Is Called: ",is_called)
    
    if not realtime_data:
        report = SearchByEmail.objects.filter(email=email).first()
        if report:
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name='hudson_search_by_email', user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                print("UPDATING")
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hudson_search_by_email")

            serialized = SearchByEmailSerializer(report).data
            log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

    try:
        print("REALTIME DATA try: ")
        if realtime_data or not report:
            print("Realtine data and nit report")
            balance_after_deduction = get_amount_after_api_call(api_name='hudson_search_by_email', user=user)
            if balance_after_deduction<0.0:
                log_user_activity(request, UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
        
        api_response = fetch_hudson_search_by_email(email)
        
        result_data = api_response['data']
        with transaction.atomic():
            SearchByEmail.objects.update_or_create(
                email=email,
                defaults={
                    'result': result_data
                }
            )
            
            print("UPdating user balance")
            update_user_balance(user=user, amount=balance_after_deduction, api_name="hudson_search_by_email")
            print("Updated")
        
        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)


# @api_view(['POST'])
# def search_by_email(request):
#     email = request.data.get("email")
#     realtime_data = request.data.get("realtimeData")

#     if not email:
#         return Response(create_response(status=False, message="Email is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
#     if not realtime_data:
#         try:
#             report = SearchByEmail.objects.get(email=email)
#             serialized = SearchByEmailSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
#         except SearchByEmail.DoesNotExist:
#             pass
        
#     try:
#         api_response = fetch_hudson_search_by_email(email)
        
#         result_data = api_response['data']

#         SearchByEmail.objects.update_or_create(
#             email=email,
#             defaults={
#                 'result': result_data
#             }
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def search_by_ip(request):
    token=get_token_from_header(request=request)
    user = get_user_from_token(token)
    ip = request.data.get("ip")
    realtime_data = request.data.get("realtimeData")

    if not ip:
        return Response(create_response(status=False, message="IP is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print('Is Called: ',is_called)
    
    if not realtime_data:
        report = SearchByIP.objects.filter(ip=ip).first()
        if report:
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="hudson_search_by_ip", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                print("UPDATING")
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hudson_search_by_ip")

            serialized = SearchByIPSerializer(report).data
            log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
    try:
        # Balance check and deduction only if realtime call or new fetch
        if realtime_data or not report:
            balance_after_deduction = get_amount_after_api_call(api_name="hudson_search_by_ip", user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request, UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        # Fetch from external API
        api_response = fetch_hudson_search_by_ip(ip=ip)

        result_data = api_response['data']
        
        # Save or update the report
        with transaction.atomic():
            SearchByIP.objects.update_or_create(
                ip=ip,
                defaults={
                    'result': result_data
                }
            )

            # Deduct balance only for realtime or first time external call
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hudson_search_by_ip")
        
        log_user_activity(request, UserActivity.Status.SUCCESS)    
        return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)


# @api_view(['POST'])
# def search_by_ip(request):
#     ip = request.data.get("ip")
#     realtime_data = request.data.get("realtimeData")

#     if not ip:
#         return Response(create_response(status=False, message="IP is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
#     if not realtime_data:
#         try:
#             report = SearchByIP.objects.get(ip=ip)
#             serialized = SearchByIPSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
#         except SearchByIP.DoesNotExist:
#             pass
        
#     try:
#         api_response = fetch_hudson_search_by_ip(ip)
        
#         result_data = api_response['data']

#         SearchByIP.objects.update_or_create(
#             ip=ip,
#             defaults={
#                 'result': result_data
#             }
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def search_by_username(request):
    token=get_token_from_header(request=request)
    user = get_user_from_token(token=token)
    username = request.data.get("username")
    realtime_data = request.data.get("realtimeData")

    if not username:
        return Response(create_response(status=False, message="Username is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print('Is Called: ',is_called)
    
    if not realtime_data:
        report = SearchByUsername.objects.filter(username=username).first()
        if report:
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name='husdone_search_by_username',user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                print("UPDATING")
                update_user_balance(user=user, amount=balance_after_deduction, api_name="husdone_search_by_username")
            
            serialized = SearchByUsernameSerializer(report).data
            log_user_activity(request, UserActivity.Status.SUCCESS)  
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
    try:
        
        if realtime_data or not report:
            balance_after_deduction = get_amount_after_api_call(api_name="husdone_search_by_username", user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request, UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)


        api_response = fetch_hudson_search_by_username(username)
        
        result_data = api_response['data']

        with transaction.atomic():
            SearchByUsername.objects.update_or_create(
                username=username,
                defaults={
                    'result': result_data
                }
            )
            
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="husdone_search_by_username")
        
        log_user_activity(request, UserActivity.Status.SUCCESS)  
        return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)


# @api_view(['POST'])
# def search_by_username(request):
#     username = request.data.get("username")
#     realtime_data = request.data.get("realtimeData")

#     if not username:
#         return Response(create_response(status=False, message="Username is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
#     if not realtime_data:
#         try:
#             report = SearchByUsername.objects.get(username=username)
#             serialized = SearchByUsernameSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
#         except SearchByUsername.DoesNotExist:
#             pass
        
#     try:
#         api_response = fetch_hudson_search_by_username(username)
        
#         result_data = api_response['data']

#         SearchByUsername.objects.update_or_create(
#             username=username,
#             defaults={
#                 'result': result_data
#             }
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def search_by_domain(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token=token)
    domain = request.data.get("domain")
    realtime_data = request.data.get("realtimeData")

    if not domain:
        return Response(create_response(status=False, message="Domain is required", data=None),status=status.HTTP_400_BAD_REQUEST)
        
    payload = request.data
    is_called = is_called_by_user_previously(user=user, api_name=request.path, payload=payload)
    
    print('Is Called: ',is_called)
    

    if not realtime_data:
        report = SearchByDomain.objects.filter(domain=domain).first()
        if report:
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name='hudson_search_by_domain',user=user)
                if balance_after_deduction<0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)
                print("UPDATING")
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hudson_search_by_domain")
            
            serialized = SearchByDomainSerializer(report).data
            log_user_activity(request, UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
    try:
        if realtime_data or not report:
            balance_after_deduction = get_amount_after_api_call(api_name="hudson_search_by_domain", user=user)
            if balance_after_deduction < 0.0:
                log_user_activity(request, UserActivity.Status.FAILED)
                return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

        api_response = fetch_hudson_search_by_domain(domain)
        
        result_data = api_response['data']
        
        with transaction.atomic():
            SearchByDomain.objects.update_or_create(
                domain=domain,
                defaults={
                    'result': result_data
                }
            )
            
            if realtime_data or not is_called:
                update_user_balance(user=user, amount=balance_after_deduction, api_name="hudson_search_by_domain")
        
        log_user_activity(request, UserActivity.Status.SUCCESS)
        return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)

    except Exception as e:
        log_user_activity(request, UserActivity.Status.FAILED)
        return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)


# @api_view(['POST'])
# def search_by_domain(request):
#     domain = request.data.get("domain")
#     realtime_data = request.data.get("realtimeData")

#     if not domain:
#         return Response(create_response(status=False, message="Domain is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
#     if not realtime_data:
#         try:
#             report = SearchByDomain.objects.get(domain=domain)
#             serialized = SearchByDomainSerializer(report).data
#             return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
#         except SearchByDomain.DoesNotExist:
#             pass
        
#     try:
#         api_response = fetch_hudson_search_by_domain(domain)
        
#         result_data = api_response['data']

#         SearchByDomain.objects.update_or_create(
#             domain=domain,
#             defaults={
#                 'result': result_data
#             }
#         )
#         return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
#     except Exception as e:
#         return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)