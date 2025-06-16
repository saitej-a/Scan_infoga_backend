from pyasn1.type.univ import Null
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.utils import timezone
from core.utils import create_response
from django.core.cache import cache

from .utils import fetch_payworld_data
from .serializers import PayworldDataSerializer
from .models import PayworldData

@api_view(['POST'])
def set_cookie(request):
    cookie = request.data.get("cookie")
    
    try:
    # Save user data and otp in Redis
        cache.set("cookie_payworld", {
            "cookie":cookie,
            "timestamp": timezone.now().isoformat(),
            
        }, timeout=14400)
        return Response(create_response(True, "Cookies saved successfully", None), status=status.HTTP_200_OK)
    except Exception as e:
        return Response(create_response(False, f"Unxpected Error: {str(e)}", None), status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def payworld_data(request):
    sender_mobile = request.data.get("sender_mobile")
    realtime_data = request.data.get("realtimeData")
    
    if not sender_mobile:
        return create_response(
            status=status.HTTP_400_BAD_REQUEST,
            message="Sender mobile number is required",
            data= Null
        )
    
    if not realtime_data:
        try:
            report = PayworldData.objects.get(sender_mobile_number=sender_mobile)
            serialized = PayworldDataSerializer(report).data
            return Response(create_response(True, "Data fetched from database", serialized['result']), status=status.HTTP_200_OK)

        except PayworldData.DoesNotExist:
            pass
    
    try:
        api_response = fetch_payworld_data(sender_mobile)
        result_data = api_response['data']
        
        if api_response['message'] == 'Sender is not registered':
            return Response(create_response(False, api_response['message'], None), status=status.HTTP_404_NOT_FOUND)
        
        PayworldData.objects.update_or_create(
            sender_mobile_number=sender_mobile,
            defaults={
                'result': result_data
            }
        )
        
        return Response(create_response(True, "Data fetched from external API", result_data), status=status.HTTP_200_OK)
        
    except Exception as e:
            return Response(create_response(False, f"Unexpected error: {str(e)}", None), status=status.HTTP_404_NOT_FOUND)
    