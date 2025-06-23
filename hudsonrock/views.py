from cffi import api
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import HudsonRockData, SearchByEmail, SearchByIP
# from drf_yasg.utils import swagger_auto_schema
from .serializers import HudsonRockDataSerializer, SearchByEmailSerializer, SearchByIPSerializer
from core.utils import create_response
from .utils import fetch_hudson_search_by_email, fetch_hudson_search_by_ip

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
    email = request.data.get("email")
    realtime_data = request.data.get("realtimeData")

    if not email:
        return Response(create_response(status=False, message="Email is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
    if not realtime_data:
        try:
            report = SearchByEmail.objects.get(email=email)
            serialized = SearchByEmailSerializer(report).data
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
        except SearchByEmail.DoesNotExist:
            pass
        
    try:
        api_response = fetch_hudson_search_by_email(email)
        
        result_data = api_response['data']

        SearchByEmail.objects.update_or_create(
            email=email,
            defaults={
                'result': result_data
            }
        )
        return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
    except Exception as e:
        return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def search_by_ip(request):
    ip = request.data.get("ip")
    realtime_data = request.data.get("realtimeData")

    if not ip:
        return Response(create_response(status=False, message="ip is required", data=None),status=status.HTTP_400_BAD_REQUEST)
    
    if not realtime_data:
        try:
            report = SearchByIP.objects.get(ip=ip)
            serialized = SearchByIPSerializer(report).data
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)
        
        except SearchByIP.DoesNotExist:
            pass
        
    try:
        api_response = fetch_hudson_search_by_ip(ip)
        
        result_data = api_response['data']

        SearchByIP.objects.update_or_create(
            ip=ip,
            defaults={
                'result': result_data
            }
        )
        return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
    except Exception as e:
        return Response(create_response(False, str(e), None), status=status.HTTP_404_NOT_FOUND)