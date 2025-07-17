from rest_framework.response import Response
from rest_framework import status
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


from payments.utils import get_amount_after_api_call, update_user_balance
from user_activities.models import UserActivity
from user_activities.utils import is_called_by_user_previously, log_user_activity

from .utils import get_cbse_dataset_dynamodb_table, get_corporate_dataset_dynamodb_table, get_leaked_credentials_dynamodb_table,get_jobseeker_dynamodb_table, get_olx_dataset_dynamodb_table, get_zomato_dataset_dynamodb_table
from .serializers import DynamoDBItemSerializer, DynamoDBOLXItemSerializer
from core.utils import create_response, get_token_from_header, get_user_from_token

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated



# class GetPassword(APIView):
#     def post(self, request, format=None):
#         email = request.data.get('email')

#         if not email:
#             return Response(create_response(True, "Email is required in the request body.", None),status=status.HTTP_400_BAD_REQUEST)
#         if not isinstance(email, str):
#             return Response(create_response(True, "Email must be a string.", None),status=status.HTTP_400_BAD_REQUEST)

#         try:
#             users_table = get_leaked_credentials_dynamodb_table()
#             response = users_table.get_item(
#                 Key={'email': email}
#             )
#             item = response.get('Item')

#             if item:
#                 serializer = DynamoDBItemSerializer(item)
#                 response = serializer.data
#                 return Response(create_response(True, "Data fetched from Database.", response), status=status.HTTP_200_OK)
#             else:
#                 return Response(create_response(False, "Email not found in database.", None),status=status.HTTP_404_NOT_FOUND)
#         except ClientError as e:
#             if e.response['Error']['Code'] == 'ResourceNotFoundException':
#                 return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             print(f"DynamoDB ClientError: {e}")
#             return Response(create_response(False, "A DynamoDB error occurred while searching.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         except Exception as e:
#             print(f"Unexpected error: {e}")
#             return Response(create_response(False, "An unexpected error occurred.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class GetJobSeekerData(APIView):
#     def post(self, request, format=None):
#         mobno = request.data.get('mobile')
#         if not mobno:
#             return Response(create_response(True, "Mobile number is required in the request body.", None),status=status.HTTP_400_BAD_REQUEST)
#         if not isinstance(mobno, str):
#             return Response(create_response(True, "Mobile number must be a string.", None),status=status.HTTP_400_BAD_REQUEST)

#         if len(mobno) != 10:
#             return Response({"error": "Mobile number must be 10 digits."},
#                             status=status.HTTP_400_BAD_REQUEST)
#         try:
#             users_table = get_jobseeker_dynamodb_table()
#             response = users_table.get_item(
#                 Key={'mobile_number': mobno}
#             )
#             item = response.get('Item')

#             if item:
#                 serializer = DynamoDBItemSerializer(item)
#                 response = serializer.data
#                 return Response(create_response(True, "Data fetched from Database.", response), status=status.HTTP_200_OK)
#             else:
#                 return Response(create_response(False, "Mobile number not found in database.", None),status=status.HTTP_404_NOT_FOUND)
#         except ClientError as e:
#             if e.response['Error']['Code'] == 'ResourceNotFoundException':
#                 return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             print(f"DynamoDB ClientError: {e}")
#             return Response(create_response(False, "A DynamoDB error occurred while searching.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         except Exception as e:
#             print(f"Unexpected error: {e}")
#             return Response(create_response(False, "An unexpected error occurred.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class GetCorporateData(APIView):
#     def post(self,request,format=None):
#         mobno = request.data.get('mobile')
#         if not mobno:
#             return Response(create_response(True, "Mobile number is required in the request body.", None),status=status.HTTP_400_BAD_REQUEST)
#         if not isinstance(mobno, str):
#             return Response(create_response(True, "Mobile number must be a string.", None),status=status.HTTP_400_BAD_REQUEST)

#         if len(mobno) != 10:
#             return Response({"error": "Mobile number must be 10 digits."},
#                             status=status.HTTP_400_BAD_REQUEST)
#         try:
#             users_table = get_corporate_dataset_dynamodb_table()
#             response = users_table.get_item(
#                 Key={'mobile_number': mobno}
#             )
#             item = response.get('Item')

#             if item:
#                 serializer = DynamoDBItemSerializer(item)
#                 response = serializer.data
#                 return Response(create_response(True, "Data fetched from Database.", response), status=status.HTTP_200_OK)
#             else:
#                 return Response(create_response(False, "Mobile number not found in database.", None),status=status.HTTP_404_NOT_FOUND)
#         except ClientError as e:
#             if e.response['Error']['Code'] == 'ResourceNotFoundException':
#                 return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             print(f"DynamoDB ClientError: {e}")
#             return Response(create_response(False, "A DynamoDB error occurred while searching.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         except Exception as e:
#             print(f"Unexpected error: {e}")
#             return Response(create_response(False, "An unexpected error occurred.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class GetZomatoData(APIView):
#     def post(self,request,format=None):
#         mobno=request.data.get('mobile')
#         if not mobno:
#             return Response(create_response(True, "Mobile number is required in the request body.", None),status=status.HTTP_400_BAD_REQUEST)
#         if not isinstance(mobno, str):
#             return Response(create_response(True, "Mobile number must be a string.", None),status=status.HTTP_400_BAD_REQUEST)
#         if len(mobno) != 10:
#             return Response({"error": "Mobile number must be 10 digits."},
#                             status=status.HTTP_400_BAD_REQUEST)
#         try:
#             users_table = get_zomato_dataset_dynamodb_table()
#             response = users_table.get_item(
#                 Key={'mobile_number': mobno}
#             )
#             item = response.get('Item')

#             if item:
#                 serializer = DynamoDBItemSerializer(item)
#                 response = serializer.data
#                 return Response(create_response(True, "Data fetched from Database.", response), status=status.HTTP_200_OK)
#             else:
#                 return Response(create_response(False, "Mobile number not found in database.", None),status=status.HTTP_404_NOT_FOUND)
#         except ClientError as e:
#             if e.response['Error']['Code'] == 'ResourceNotFoundException':
#                 return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             print(f"DynamoDB ClientError: {e}")
#             return Response(create_response(False, "A DynamoDB error occurred while searching.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         except Exception as e:
#             print(f"Unexpected error: {e}")
#             return Response(create_response(False, "An unexpected error occurred.", None),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_password(request):
    email = request.data.get('email')

    if not email:
        return Response(create_response(False, "Email is required in the request body.", None), status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(email, str):
        return Response(create_response(False, "Email must be a string.", None), status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    payload = request.data

    is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)

    try:
        users_table = get_leaked_credentials_dynamodb_table()
        response = users_table.get_item(
            Key={'email': email}
        )
        item = response.get('Item')
        

        if item:
            serializer = DynamoDBItemSerializer(item)
            response_data = serializer.data
            
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="leak_data_get_password", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

                update_user_balance(user=user, amount=balance_after_deduction, api_name="leak_data_get_password")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from Database.", response_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data not found in database.", None), status=status.HTTP_200_OK)

    except ClientError as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)

        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        print(f"DynamoDB ClientError: {e}")
        return Response(create_response(False, "A DynamoDB error occurred while searching.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        print(f"Unexpected error: {e}")
        return Response(create_response(False, "An unexpected error occurred.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_job_seeker_data(request):
    mobno = request.data.get('mobile')
    if not mobno:
        return Response(create_response(False, "Mobile number is required in the request body.", None), status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(mobno, str):
        return Response(create_response(False, "Mobile number must be a string.", None), status=status.HTTP_400_BAD_REQUEST)

    if len(mobno) != 10:
        return Response({"error": "Mobile number must be 10 digits."}, status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    payload = request.data

    is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)

    try:
        users_table = get_jobseeker_dynamodb_table()
        response = users_table.get_item(
            Key={'mobile_number': mobno}
        )
        item = response.get('Item')

        if item:
            serializer = DynamoDBItemSerializer(item)
            response_data = serializer.data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="leak_data_get_job_seeker_data", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

                update_user_balance(user=user, amount=balance_after_deduction, api_name="leak_data_get_job_seeker_data")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from Database.", response_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data not found in database.", None), status=status.HTTP_200_OK)

    except ClientError as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)

        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        print(f"DynamoDB ClientError: {e}")
        return Response(create_response(False, "A DynamoDB error occurred while searching.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        print(f"Unexpected error: {e}")
        return Response(create_response(False, "An unexpected error occurred.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_corporate_data(request):
    mobno = request.data.get('mobile')
    if not mobno:
        return Response(create_response(False, "Mobile number is required in the request body.", None), status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(mobno, str):
        return Response(create_response(False, "Mobile number must be a string.", None), status=status.HTTP_400_BAD_REQUEST)

    if len(mobno) != 10:
        return Response({"error": "Mobile number must be 10 digits."}, status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    payload = request.data

    is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)

    try:
        users_table = get_corporate_dataset_dynamodb_table()
        response = users_table.get_item(
            Key={'mobile_number': mobno}
        )
        item = response.get('Item')
            
        if item:
            serializer = DynamoDBItemSerializer(item)
            response_data = serializer.data

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="leak_data_get_corporate_data", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

                update_user_balance(user=user, amount=balance_after_deduction, api_name="leak_data_get_corporate_data")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from Database.", response_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data not found in database.", None), status=status.HTTP_200_OK)

    except ClientError as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)

        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        print(f"DynamoDB ClientError: {e}")
        return Response(create_response(False, "A DynamoDB error occurred while searching.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        print(f"Unexpected error: {e}")
        return Response(create_response(False, "An unexpected error occurred.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_zomato_data(request):
    mobno = request.data.get('mobile')
    if not mobno:
        return Response(create_response(False, "Mobile number is required in the request body.", None), status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(mobno, str):
        return Response(create_response(False, "Mobile number must be a string.", None), status=status.HTTP_400_BAD_REQUEST)

    if len(mobno) != 10:
        return Response({"error": "Mobile number must be 10 digits."}, status=status.HTTP_400_BAD_REQUEST)

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    payload = request.data

    is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)

    try:
        users_table = get_zomato_dataset_dynamodb_table()
        response = users_table.get_item(
            Key={'mobile_number': mobno}
        )
        item = response.get('Item')

        if item:
            serializer = DynamoDBItemSerializer(item)
            response_data = serializer.data
        
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="leak_data_get_zomato_data", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

                update_user_balance(user=user, amount=balance_after_deduction, api_name="leak_data_get_zomato_data")



            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from Database.", response_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data not found in database.", None), status=status.HTTP_200_OK)

    except ClientError as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)

        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        print(f"DynamoDB ClientError: {e}")
        return Response(create_response(False, "A DynamoDB error occurred while searching.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        print(f"Unexpected error: {e}")
        return Response(create_response(False, "An unexpected error occurred.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_cbse_data(request):
    mobno = request.data.get('mobile')
    if not mobno:
        return Response(create_response(False, "Mobile number is required in the request body.", None), status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(mobno, str):
        return Response(create_response(False, "Mobile number must be a string.", None), status=status.HTTP_400_BAD_REQUEST)

    if len(mobno) != 10:
        return Response({"error": "Mobile number must be 10 digits."}, status=status.HTTP_400_BAD_REQUEST)
    
    token=get_token_from_header(request)
    user=get_user_from_token(token)
    api_name=request.path
    payload=request.data

    is_called = is_called_by_user_previously(user=user,api_name=api_name,payload=payload)
    
    try:
        users_table=get_cbse_dataset_dynamodb_table()
        response = users_table.get_item(
            Key={'mobile_number': mobno}
        )
        item = response.get('Item')
        
        if item:
            serializer = DynamoDBItemSerializer(item)
            response_data = serializer.data
        
            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="leak_data_get_cbse_data", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

                update_user_balance(user=user, amount=balance_after_deduction, api_name="leak_data_get_cbse_data")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data fetched from Database.", response_data), status=status.HTTP_200_OK)

        else:
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(create_response(True, "Data not found in database.", None), status=status.HTTP_200_OK)
    except ClientError as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        print(f"DynamoDB ClientError: {e}")
        return Response(create_response(False, "A DynamoDB error occurred while searching.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        print(f"Unexpected error: {e}")
        return Response(create_response(False, f"An unexpected error occurred.{e}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(['POST'])
# def get_olx_data(request):
#     mobno = request.data.get('mobile')
#     if not mobno:
#         return Response(create_response(False, "Mobile number is required in the request body.", None), status=status.HTTP_400_BAD_REQUEST)
#     if not isinstance(mobno, str):
#         return Response(create_response(False, "Mobile number must be a string.", None), status=status.HTTP_400_BAD_REQUEST)

#     if len(mobno) != 10:
#         return Response({"error": "Mobile number must be 10 digits."}, status=status.HTTP_400_BAD_REQUEST)
    
#     token=get_token_from_header(request)
#     user=get_user_from_token(token)
#     api_name=request.path
#     payload=request.data

#     is_called = is_called_by_user_previously(user=user,api_name=api_name,payload=payload)
    
#     try:
#         users_table=get_olx_dataset_dynamodb_table()
#         response = users_table.get_item(
#             Key={'mobile_number': mobno}
#         )
#         item = response.get('Item')
        
#         if item:
#             serializer = DynamoDBItemSerializer(item)
#             response_data = serializer.data
        
#             if not is_called:
#                 balance_after_deduction = get_amount_after_api_call(api_name="leak_data_get_olx_data", user=user)
#                 if balance_after_deduction < 0.0:
#                     log_user_activity(request=request, status=UserActivity.Status.FAILED)
#                     return Response(create_response(False, "Insufficient balance.", None), status=status.HTTP_402_PAYMENT_REQUIRED)

#                 update_user_balance(user=user, amount=balance_after_deduction)

#             log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
#             return Response(create_response(True, "Data fetched from Database.", response_data), status=status.HTTP_200_OK)

#         else:
#             log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
#             return Response(create_response(True, "Data not found in database.", None), status=status.HTTP_200_OK)
#     except ClientError as e:
#         log_user_activity(request=request, status=UserActivity.Status.FAILED)
#         if e.response['Error']['Code'] == 'ResourceNotFoundException':
#             return Response(create_response(False, "DynamoDB table not found. Check DYNAMODB_TABLE_NAME setting.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         print(f"DynamoDB ClientError: {e}")
#         return Response(create_response(False, "A DynamoDB error occurred while searching.", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     except Exception as e:
#         log_user_activity(request=request, status=UserActivity.Status.FAILED)
#         print(f"Unexpected error: {e}")
#         return Response(create_response(False, f"An unexpected error occurred.{e}", None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(['POST'])
# def get_olx_data(request):
#     mobno = request.data.get('mobile')
#     if not mobno:
#         return Response(
#             create_response(False, "Mobile number is required in the request body.", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     if not isinstance(mobno, str):
#         return Response(
#             create_response(False, "Mobile number must be a string.", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     if len(mobno) != 10:
#         return Response(
#             create_response(False, "Mobile number must be 10 digits.", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     try:
#         table = get_olx_dataset_dynamodb_table()

#         response = table.query(
#         IndexName='mobile_number-index',  # GSI name
#         KeyConditionExpression=Key('mobile_number').eq(mobno)
#         )

#         items = response.get('Items', [])
#         print(items)

#         if items:
#             serialized = DynamoDBOLXItemSerializer.serialize(items)
#             return Response(
#                 create_response(True, "Data fetched from OLX database.", serialized),
#                 status=status.HTTP_200_OK
#             )
#         else:
#             return Response(
#                 create_response(False, "Mobile number not found in OLX database.", None),
#                 status=status.HTTP_404_NOT_FOUND
#             )

#     except ClientError as e:
#         if e.response['Error']['Code'] == 'ResourceNotFoundException':
#             return Response(
#                 create_response(False, "OLX DynamoDB table or GSI not found.", None),
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
#         print(f"DynamoDB ClientError: {e}")
#         return Response(
#             create_response(False, "A DynamoDB error occurred while searching.", None),
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )
#     except Exception as e:
#         print(f"Unexpected error: {e}")
#         return Response(
#             create_response(False, "An unexpected error occurred.", None),
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


@api_view(['POST'])
def get_olx_data(request):
    mobno = request.data.get('mobile')
    if not mobno:
        return Response(
            create_response(False, "Mobile number is required in the request body.", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    if not isinstance(mobno, str):
        return Response(
            create_response(False, "Mobile number must be a string.", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(mobno) != 10:
        return Response(
            create_response(False, "Mobile number must be 10 digits.", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    token = get_token_from_header(request)
    user = get_user_from_token(token)
    api_name = request.path
    payload = request.data

    is_called = is_called_by_user_previously(user=user, api_name=api_name, payload=payload)

    try:
        table = get_olx_dataset_dynamodb_table()

        response = table.query(
            IndexName='mobile_number-index',  # GSI name
            KeyConditionExpression=Key('mobile_number').eq(mobno)
        )

        items = response.get('Items', [])
        # print(items)

        if items:
            serialized = DynamoDBOLXItemSerializer.serialize(items)
            # Deduplicate by all fields except `id`
            unique_items = []
            seen = set()

            for item in serialized:
                # Build a tuple of fields except `id`
                dedup_key = tuple(
                    (k, v) for k, v in item.items() if k != "id"
                )
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    unique_items.append(item)

            if not is_called:
                balance_after_deduction = get_amount_after_api_call(api_name="leak_data_get_olx_data", user=user)
                if balance_after_deduction < 0.0:
                    log_user_activity(request=request, status=UserActivity.Status.FAILED)
                    return Response(
                        create_response(False, "Insufficient balance.", None),
                        status=status.HTTP_402_PAYMENT_REQUIRED
                    )

                update_user_balance(user=user, amount=balance_after_deduction, api_name="leak_data_get_olx_data")


            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)

            return Response(
                create_response(True, "Data fetched from the database.", unique_items),
                status=status.HTTP_200_OK
            )
        else:
            log_user_activity(request=request, status=UserActivity.Status.SUCCESS)
            return Response(
                create_response(False, "Mobile number not found in the database.", None),
                status=status.HTTP_404_NOT_FOUND
            )

    except ClientError as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return Response(
                create_response(False, "OLX DynamoDB table or GSI not found.", None),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        print(f"DynamoDB ClientError: {e}")
        return Response(
            create_response(False, "A DynamoDB error occurred while searching.", None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        log_user_activity(request=request, status=UserActivity.Status.FAILED)
        print(f"Unexpected error: {e}")
        return Response(
            create_response(False, f"An unexpected error occurred: {e}", None),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
