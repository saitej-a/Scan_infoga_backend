from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.utils import timezone
from core.utils import create_response
from django.core.cache import cache

from .models import PayworldData2, RazorpayIFSCData
from core.tasks import fetch_and_store_payworld_data, fetch_and_store_razorpay_data
from .utils import fetch_payworld_data, fetch_razorpay_ifsc_data
from core.utils import create_response


@api_view(['POST'])
def set_cookie(request):
    cookie = request.data.get("cookie")
    if not cookie:
        return Response(create_response(False, "Cookie value is required", None), status=400)
    try:
        cache.set("cookie_payworld", {
            "cookie": cookie,
            "timestamp": timezone.now().isoformat(),
        }, timeout=14400)
        return Response(create_response(True, "Cookie saved successfully", None), status=200)
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
    sender_mobile = request.data.get("sender_mobile")
    realtime_data = request.data.get("realtimeData")

    if not sender_mobile:
        return Response(
            create_response(False, "Sender mobile number is required", None),
            status=status.HTTP_400_BAD_REQUEST
        )

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
                latest_timestamp = list(latest_entry.keys())[0]
                return Response(
                    create_response(True, "Data fetched from database", {
                        "count": count,
                        "datetime_list": datetime_list,
                        "datetime": latest_timestamp,
                        "data": latest_entry[latest_timestamp]
                    }),
                    status=status.HTTP_200_OK
                )
            else:
                pass

        if latest_entry is None:
            result = fetch_payworld_data(sender_mobile)
            if result.get("status"):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}
                PayworldData2.objects.update_or_create(
                    sender_mobile_number=sender_mobile,
                    defaults={"result": [data_dict]}
                )
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
                return Response(
                    create_response(False, result.get("message", "Failed to fetch data"), None),
                    status=status.HTTP_404_NOT_FOUND
                )

        api_response = fetch_payworld_data(sender_mobile)
        fetch_and_store_payworld_data.delay(sender_mobile, api_response)

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
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def get_full_payworld_data(request):
    sender_mobile = request.data.get("sender_mobile")
    if not sender_mobile:
        return Response(
            create_response(False, "Missing sender_mobile in query parameters", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        data_obj = PayworldData2.objects.get(sender_mobile_number=sender_mobile)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in data_obj.result
        ]
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )
    except PayworldData2.DoesNotExist:
        result = fetch_payworld_data(sender_mobile)
        if result.get("status"):
            ts = result["data"].pop("datetime")
            data_dict = {ts: result["data"]}
            PayworldData2.objects.update_or_create(
                sender_mobile_number=sender_mobile,
                defaults={"result": [data_dict]}
            )
            return Response(
                create_response(True, "Real-time data fetched successfully", [{
                    "datetime": ts,
                    "data": data_dict[ts]
                }]),
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                create_response(False, result.get("message", "Failed to fetch data"), None),
                status=status.HTTP_404_NOT_FOUND
            )

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
    ifsc_code = request.data.get("ifsc_code")
    realtime_data = request.data.get("realtimeData")
    if not ifsc_code:
        return Response(create_response(False, "IFSC code is required", None), status=status.HTTP_400_BAD_REQUEST)

    try:
        obj = RazorpayIFSCData.objects.get(ifsc_code=ifsc_code)
        full_data = obj.result
        latest_entry = obj.result[-1] if obj.result else None
    except RazorpayIFSCData.DoesNotExist:
        obj = None
        full_data = []
        latest_entry = None
    
    try:
        count = len(full_data)
        datetime_list = [list(entry.keys())[0] for entry in full_data]

        if not realtime_data:
            if latest_entry:
                latest_timestamp = list(latest_entry.keys())[0]
                return Response(
                    create_response(True, "Data fetched from database", {
                        "count": count,
                        "datetime_list": datetime_list,
                        "datetime": latest_timestamp,
                        "data": latest_entry[latest_timestamp]
                    }),
                    status=status.HTTP_200_OK
                )
            else:
                pass
            
        if latest_entry is None:
            result = fetch_razorpay_ifsc_data(ifsc_code)
            if result.get("status"):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}
                RazorpayIFSCData.objects.update_or_create(
                    ifsc_code=ifsc_code,
                    defaults={"result": [data_dict]}
                )
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
                return Response(
                    create_response(False, result.get("message", "Failed to fetch data"), None), 
                    status=status.HTTP_404_NOT_FOUND
                )
            
        api_response = fetch_razorpay_ifsc_data(ifsc_code)
        fetch_and_store_razorpay_data.delay(ifsc_code,api_response)
        
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
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    


@api_view(['POST'])
def get_full_razorpay_ifsc_data(request):
    ifsc_code = request.data.get("ifsc_code")
    if not ifsc_code:
        return Response(
            create_response(False, "Missing ifsc_code in query parameters", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        data_obj = RazorpayIFSCData.objects.get(ifsc_code=ifsc_code)
        full_data = [
            {"datetime": list(entry.keys())[0], "data": list(entry.values())[0]}
            for entry in data_obj.result
        ]
        return Response(
            create_response(True, "Full data fetched successfully", full_data),
            status=status.HTTP_200_OK
        )
    except RazorpayIFSCData.DoesNotExist:
        print("no data fetching from external")
        result = fetch_razorpay_ifsc_data(ifsc_code)
        if result.get("status"):
                ts = result["data"].pop("datetime")
                data_dict = {ts: result["data"]}
                RazorpayIFSCData.objects.update_or_create(
                    ifsc_code=ifsc_code,
                    defaults={"result": [data_dict]}
                )
                return Response(
                    create_response(True, "Real-time data fetched successfully", [{
                        "datetime": ts,
                        "data": data_dict[ts]
                    }]),
                    status=status.HTTP_200_OK
                )
        else:
            return Response(
                create_response(False, result.get("message", "Failed to fetch data"), None), 
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        return Response(
            create_response(False, str(e), None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# @api_view(['DELETE'])
# def delete_razorpay_ifsc_data(request):
#     ifsc_code = request.query_params.get('ifsc_code')
#     if not ifsc_code:
#         return Response(
#             create_response(False, "Missing?ifsc_code parameter in query", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     records = RazorpayIFSCData.objects.filter(ifsc_code=ifsc_code)
#     count = records.count()   

#     if count == 0:
#         return Response(
#             create_response(False, f'No data found for ifsc_code: {ifsc_code}', None),
#             status=status.HTTP_404_NOT_FOUND
#         )

#     records.delete()
#     return Response(
#         create_response(True, f'Successfully deleted {count} record(s) for ifsc_code: {ifsc_code}', None),
#         status=status.HTTP_200_OK
#     )


