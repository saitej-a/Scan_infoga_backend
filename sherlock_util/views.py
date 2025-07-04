from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from core.utils import create_response
from sherlock_master.sherlock_utils import get_detailed_results_async
import asyncio
import json
# Create your views here.

@api_view(['POST'])
def get_username_info_sherlock(request):
    username = request.data.get('username')
    if not username:
        return Response(create_response(False, "Username is required", None), status=status.HTTP_400_BAD_REQUEST)
    
    result = asyncio.run(get_detailed_results_async(username=username))
    # print(result)
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
