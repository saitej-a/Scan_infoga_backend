# import json
# import jwt
# import logging
# import time
# from django.conf import settings
# from django.http import JsonResponse
# from rest_framework import status
# from custom_auth.models import CustomUser as User
# from user_activities.models import UserActivity
# from .utils import create_response

# logger = logging.getLogger("django.request")
# MAX_BODY_LENGTH = 1000  # Limit large body logs

# class GlobalLoggingMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         request.start_time = time.time()

#         # Always log request (basic info, no body)
#         self.log_request(request)

#         if not (
#             request.path.startswith("/api/mobile/") or
#             request.path.startswith("/api/digital-intelligence/") or
#             request.path.startswith("/api/secondary/")
#         ):
#             self.log_user_activity(request)

#         try:
#             response = self.get_response(request)
#         except Exception as e:
#             logger.exception(f"[EXCEPTION] {request.method} {request.get_full_path()}: {str(e)}")
#             return JsonResponse(
#                 create_response(
#                     status=False,
#                     message=str(e),
#                     data=None
#                 ),
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

#         # Conditionally log response
#         self.log_response(request, response)

#         return response

#     def log_request(self, request):
#         query_params = dict(request.GET)

#         logger.info(
#             f"[REQUEST] {request.method} {request.get_full_path()} | Query Params: {query_params}"
#         )

#     def log_response(self, request, response):
#         duration = time.time() - getattr(request, 'start_time', time.time())
#         status_code = response.status_code

#         body_str = ""
#         if status_code >= 400:
#             # Only decode body for error responses
#             try:
#                 if hasattr(response, 'content'):
#                     body = response.content.decode('utf-8') if response.content else ''
#                     if len(body) > MAX_BODY_LENGTH:
#                         body = body[:MAX_BODY_LENGTH] + '... [truncated]'
#                     body_str = f" | Body: {body}"
#                 else:
#                     body_str = " | Body: <streaming response>"
#             except Exception:
#                 body_str = " | Body: <could not decode response body>"

#         logger.info(
#             f"[RESPONSE] {request.method} {request.get_full_path()} | Status: {status_code} | Duration: {duration:.3f}s{body_str}"
#         )

#     def log_user_activity(self, request):
#         try:
#             auth_header = request.headers.get("Authorization", "")
#             token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
#             email = None
#             user = None

#             if token:
#                 payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
#                 email = payload.get("email")
#                 if email:
#                     user = User.objects.filter(email=email).first()

#             client_info_raw = request.headers.get("clientInfo", "{}")
#             try:
#                 client_info = json.loads(client_info_raw)
#             except json.JSONDecodeError:
#                 client_info = {}

#             try:
#                 payload_data = json.loads(request.body.decode('utf-8')) if request.body else {}
#             except Exception:
#                 payload_data = {}

#             if user:
#                 UserActivity.objects.create(
#                     user=user,
#                     email=user.email,
#                     api_called=request.path,
#                     request_payload=payload_data,
#                     ip_address=client_info.get("ipAddress", request.META.get("REMOTE_ADDR", "")),
#                     device=client_info.get("device", ""),
#                     browser=client_info.get("browser", ""),
#                     latitude=client_info.get("latitude", ""),
#                     longitude=client_info.get("longitude", ""),
#                     status=UserActivity.Status.SUCCESS
#                 )
#                 logger.info(f"User activity logged for user {user.email} at path {request.path}")
#             else:
#                 logger.warning(f"User not found from token for path {request.path}, skipping UserActivity log")

#         except Exception as e:
#             logger.error(f"Exception in log_user_activity: {str(e)}", exc_info=True)


import json
import jwt
import time
import logging
import traceback
from django.conf import settings
from django.http import JsonResponse, HttpRequest, HttpResponse
from requests import Response
from rest_framework import status
from custom_auth.models import CustomUser as User
from user_activities.models import UserActivity
from user_activities.utils import log_user_activity
from .utils import create_response
import os

logger = logging.getLogger("django.request")
MAX_BODY_LENGTH = 1000

class GlobalLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        request.start_time = time.time()
        self.log_request(request)
        response = self.get_response(request)
        if "/mobile/digitalpayment" not in request.path:
            self.log_response(request, response)
        return response

    def log_request(self, request: HttpRequest):
        query_params = dict(request.GET)
        payload = None
        try:
            if request.method in ['POST', 'PUT', 'PATCH']:
                payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception as e:
            payload = "<Failed to decode body>"
        
        logger.info(f"[REQUEST] {request.method} {request.get_full_path()} | Params: {query_params} | Payload: {payload}")

    def log_response(self, request: HttpRequest, response: HttpResponse):
        duration = time.time() - request.start_time
        status_code = getattr(response, "status_code", 500)
        try:
            content = response.content.decode("utf-8")
            if len(content) > MAX_BODY_LENGTH:
                content = content[:MAX_BODY_LENGTH] + " ... [truncated]"
            body_snippet = f" | Body: {content}"
        except Exception:
            body_snippet = " | Body: <could not decode>"
        logger.info(
            f"[RESPONSE] {request.method} {request.get_full_path()} | Status: {status_code} | Time: {duration:.3f}s{body_snippet}"
        )
        if(status_code < 400):
            log_user_activity(request, UserActivity.Status.SUCCESS)

    def process_exception(self, request, exception):
        log_user_activity(request, UserActivity.Status.FAILED, str(exception))
        return JsonResponse(create_response(status= False, message= str(exception) if os.getenv("ENVIRONMENT") == "DEVELOPMENT" else "Error occured processing your request"), status=status.HTTP_400_BAD_REQUEST)

    

