from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from core.utils import create_response
from .utils import check_email
# Create your views here.

@api_view(['POST'])
def get_email_info_holehe(request):
    email = request.data.get('email')
    if not email:
        return Response(create_response(False, "Email is required", None), status=status.HTTP_400_BAD_REQUEST)
    
    result = check_email(email=email, only_used=True)
    print(result)
    if not result:
        return Response(create_response(False, "No data found", None), status=status.HTTP_404_NOT_FOUND)
    
    return Response(
        create_response(
            True,
            "Data fetched successfully",
            result
        ),
        status=status.HTTP_200_OK
    )