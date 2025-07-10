# import json
# import jwt
# from django.conf import settings
# from django.utils.timezone import now
# from custom_auth.models import CustomUser as User
# from django.http import JsonResponse
# from rest_framework import status
# from user_activities.models import UserActivity
# from .utils import create_response

# class GlobalExceptionMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         if not (request.path.startswith("/api/mobile/") or request.path.startswith("/api/digital-intelligence/") or request.path.startswith("/api/secondary/")):
#             print("Log called from middleware")
#             print(request.path)
#             self.log_user_activity(request)
#         # self.log_user_activity(request)
#         response = self.get_response(request)
#         return response

#     def process_exception(self, request, exception):
#         print("Exception from middleware: ", request.path, str(exception))
#         return JsonResponse(
#             create_response(
#                 status=False,
#                 message=str(exception),
#                 data=None
#             ),
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )

#     def log_user_activity(self, request):
#         try:
#             # 1. Decode JWT Token
#             auth_header = request.headers.get("Authorization", "")
#             token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
#             email = None
#             user = None

#             if token:
#                 payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
#                 email = payload.get("email")  # Adjust key if needed (e.g., 'email')
#                 if email:
#                     user = User.objects.filter(email=email).first()

#             # 2. Parse clientInfo
#             client_info_raw = request.headers.get("clientInfo", "{}")

#             try:
#                 client_info = json.loads(client_info_raw)
#             except json.JSONDecodeError as e:
#                 client_info = {}

#             # 3. Parse payload
#             try:
#                 payload_data = json.loads(request.body.decode('utf-8')) if request.body else {}
#             except Exception:
#                 payload_data = {}

#             # 4. Save to DB
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
#                     status= UserActivity.Status.SUCCESS
#                 )

#                 print("Created user activity")
#             else:
#                 print("User not found did not create")
#         except Exception as e:
#             # Don't break request flow if activity logging fails
#             print("Exception from middleware log user activity: ", str(e))
#             pass

import json
import jwt
import logging
import time
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from custom_auth.models import CustomUser as User
from user_activities.models import UserActivity
from .utils import create_response

logger = logging.getLogger("django.request")
MAX_BODY_LENGTH = 1000  # Limit large body logs

class GlobalLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.start_time = time.time()

        # Always log request (basic info, no body)
        self.log_request(request)

        if not (
            request.path.startswith("/api/mobile/") or
            request.path.startswith("/api/digital-intelligence/") or
            request.path.startswith("/api/secondary/")
        ):
            self.log_user_activity(request)

        try:
            response = self.get_response(request)
        except Exception as e:
            logger.exception(f"[EXCEPTION] {request.method} {request.get_full_path()}: {str(e)}")
            return JsonResponse(
                create_response(
                    status=False,
                    message=str(e),
                    data=None
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Conditionally log response
        self.log_response(request, response)

        return response

    def log_request(self, request):
        query_params = dict(request.GET)

        logger.info(
            f"[REQUEST] {request.method} {request.get_full_path()} | Query Params: {query_params}"
        )

    def log_response(self, request, response):
        duration = time.time() - getattr(request, 'start_time', time.time())
        status_code = response.status_code

        body_str = ""
        if status_code >= 400:
            # Only decode body for error responses
            try:
                if hasattr(response, 'content'):
                    body = response.content.decode('utf-8') if response.content else ''
                    if len(body) > MAX_BODY_LENGTH:
                        body = body[:MAX_BODY_LENGTH] + '... [truncated]'
                    body_str = f" | Body: {body}"
                else:
                    body_str = " | Body: <streaming response>"
            except Exception:
                body_str = " | Body: <could not decode response body>"

        logger.info(
            f"[RESPONSE] {request.method} {request.get_full_path()} | Status: {status_code} | Duration: {duration:.3f}s{body_str}"
        )

    def log_user_activity(self, request):
        try:
            auth_header = request.headers.get("Authorization", "")
            token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
            email = None
            user = None

            if token:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                email = payload.get("email")
                if email:
                    user = User.objects.filter(email=email).first()

            client_info_raw = request.headers.get("clientInfo", "{}")
            try:
                client_info = json.loads(client_info_raw)
            except json.JSONDecodeError:
                client_info = {}

            try:
                payload_data = json.loads(request.body.decode('utf-8')) if request.body else {}
            except Exception:
                payload_data = {}

            if user:
                UserActivity.objects.create(
                    user=user,
                    email=user.email,
                    api_called=request.path,
                    request_payload=payload_data,
                    ip_address=client_info.get("ipAddress", request.META.get("REMOTE_ADDR", "")),
                    device=client_info.get("device", ""),
                    browser=client_info.get("browser", ""),
                    latitude=client_info.get("latitude", ""),
                    longitude=client_info.get("longitude", ""),
                    status=UserActivity.Status.SUCCESS
                )
                logger.info(f"User activity logged for user {user.email} at path {request.path}")
            else:
                logger.warning(f"User not found from token for path {request.path}, skipping UserActivity log")

        except Exception as e:
            logger.error(f"Exception in log_user_activity: {str(e)}", exc_info=True)
