from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import CharField
from django.db.models import Max
import pyotp
import qrcode
import base64
from io import BytesIO
from django.db.models.functions import Coalesce
from .serializers import UserRegistrationSerializer, CorporateRegistrationSerializer, DeveloperRegistrationSerializer, UserSessionSerializer, UserListSerializer, BookmarkSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
import hashlib
from .models import UserSession, CustomUser, Bookmark
# from .models import CustomUser
from user_agents import parse
from django.utils import timezone
from core.utils import create_response, paginate_queryset
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.decorators import parser_classes
from django.http import HttpResponse
import json
from core.tasks import send_welcome_email
from core.utils import get_token_from_header, get_user_from_token
from core.services.email_service import EmailService
from core.tasks import send_welcome_email, send_otp_email
import random
import string
from django.core.cache import cache
from datetime import datetime, timedelta


from .utils import fetch_map, fetch_location_map
from payments.utils import create_wallet


from payments.models import WalletBalance, Transaction
from django.db.models import Sum, F, OuterRef, Subquery, DecimalField, Q, When, Case, Value

# @api_view(['POST'])
# def registerUser(request):
#     serializer = UserRegistrationSerializer(data=request.data)
#     if serializer.is_valid():
#         user = serializer.save()
#         # Generate secret key and QR code after user is created
#         secret_key = pyotp.random_base32()
#         user.otp_secret = secret_key
#         user.save()

#         # create wallet for user after user is created 
#         # and by default add 2000 credit
#         create_wallet(user)
        
#         # Generate QR code
#         qr_code = generate_qr_code(user.email, secret_key)
        
#         response_data = serializer.data
#         response_data['qr_code'] = qr_code
        
#         return Response(
#             create_response(
#                 status=True,
#                 message="User registered successfully. Please scan the QR code to setup 2FA.",
#                 data=response_data
#             ),
#             status=status.HTTP_201_CREATED
#         )
#     return Response(
#         create_response(
#             status=False,
#             message="Registration failed",
#             data=serializer.errors
#         ),
#         status=status.HTTP_400_BAD_REQUEST
#     )

# @api_view(['POST'])
# def registerUser(request):
#     serializer = UserRegistrationSerializer(data=request.data)
#     if serializer.is_valid():
#         user = serializer.save()
        
#         # Generate secret key and QR code after user is created
#         secret_key = pyotp.random_base32()
#         user.otp_secret = secret_key
#         user.save()

#         # Generate OTP and save it to the OTP model
#         otp_obj = OTP.objects.create(user=user)
#         otp = otp_obj.generate_otp()  # OTP is now generated and stored hashed in DB
        
#         # Send OTP via Email
#         context = {"otp": otp, "name": user.}
#         email_sent = EmailService.send_email(template_name="otp_template", to_email=user.email, context=context)
        
#         if email_sent:
#             response_data = serializer.data
#             response_data['otp'] = otp  # Include the OTP in the response (for testing)
            
#             return Response(
#                 create_response(
#                     status=True,
#                     message="User registered successfully. OTP sent to email.",
#                     data=response_data
#                 ),
#                 status=status.HTTP_201_CREATED
#             )
#         else:
#             return Response(
#                 create_response(
#                     status=False,
#                     message="Failed to send OTP email",
#                     data=None
#                 ),
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
#     return Response(
#         create_response(
#             status=False,
#             message="Registration failed",
#             data=serializer.errors
#         ),
#         status=status.HTTP_400_BAD_REQUEST
#     )


@api_view(['POST'])
def registerUser(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user_data = serializer.validated_data
        print("USER DATA: ", user_data)
        email = user_data['email']

        # Check if user already exists in DB
        if CustomUser.objects.filter(email=email).exists():
            return Response(
                create_response(False, "User already exists", None),
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate secret and OTP
        secret_key = pyotp.random_base32()
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        print("THIS IS OTP", otp)
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()

        # Save user data and otp in Redis
        cache.set(f"user_data:{email}", {
            "data": user_data,
            "secret": secret_key,
            "otp_hash": otp_hash,
            "timestamp": timezone.now().isoformat()
        }, timeout=3600)  # 60 minutes

        # Send OTP via email
        name = user_data["first_name"] + " " + user_data["last_name"]
        send_otp_email.delay(name=name, otp=otp, user_email=email)

        return Response(
            create_response(True, "OTP sent to email", data=None),
            status=status.HTTP_200_OK
        )
    return Response(
        create_response(False, "Validation failed", serializer.errors),
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['POST'])
def verifyOTP(request):
    email = request.data.get("email")
    otp = request.data.get("otp")

    cached = cache.get(f"user_data:{email}")
    if not cached:
        return Response(
            create_response(False, "OTP expired or not requested", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    expected_hash = cached["otp_hash"]
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    if otp_hash != expected_hash:
        return Response(
            create_response(False, "Invalid OTP", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    # Save the user to the database
    data = cached['data']
    payload = {
        "firstName": data["first_name"],
        "lastName": data["last_name"],
        "email": data["email"],
        "password": data["password"]
    }
    serializer = UserRegistrationSerializer(data=payload)
    if serializer.is_valid():
        user = serializer.save()
        user.otp_secret = cached["secret"]
        user.save()

        # Optional: delete cache after success
        cache.delete(f"user_data:{email}")

        # Send welcome email via Celery
        send_welcome_email.delay(user_email=email, name=user.first_name + " " + user.last_name)
        # create wallet for user after user is created 
        # and by default add 2000 credit
        create_wallet(user)
        qr_code = generate_qr_code(email, user.otp_secret)
        return Response(
            create_response(True, "OTP verified, user created", {"qr_code": qr_code}),
            status=status.HTTP_201_CREATED
        )
    else:
        return Response(
            create_response(False, "User creation failed", serializer.errors),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['POST'])
def forget_password(request):
    email = request.data.get("email")

    if not email:
        return Response(
            create_response(False, "Email is required", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(False, "User not found", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate secret and OTP
    secret_key = pyotp.random_base32()
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    # Save OTP and email in Redis
    cache.set(f"user_data_pass_reset:{email}", {
        "email": email,
        "secret": secret_key,
        "otp_hash": otp_hash,
        "timestamp": timezone.now().isoformat()
    }, timeout=3600)  # 60 minutes

    # Send OTP via email
    send_otp_email.delay(name=user.first_name + " " + user.last_name, otp=otp, user_email=email, reset_password=True)

    return Response(
        create_response(True, "Please enter the OTP sent on email", None),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
def verify_password_reset_otp(request):
    email = request.data.get("email")
    otp = request.data.get("otp")
    new_password = request.data.get("newPassword")

    if not (email and otp and new_password):
        return Response(
            create_response(False, "Email, OTP, and new password are required", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    cached = cache.get(f"user_data_pass_reset:{email}")
    if not cached:
        return Response(
            create_response(False, "OTP expired or not requested", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    expected_hash = cached["otp_hash"]
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    if otp_hash != expected_hash:
        return Response(
            create_response(False, "Invalid OTP", None),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if(email != cached["email"]):
        return Response(
            create_response(False, "Email does not match", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(False, "User not found", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    # Update password and secret
    new_password_hashed = hashlib.sha256(new_password.encode()).hexdigest()
    user.set_password(new_password_hashed)
    user.otp_secret = cached["secret"]
    user.save()

    # Optional: clear cache
    cache.delete(f"user_data_pass_reset:{email}")

    qr_code = generate_qr_code(email, user.otp_secret)


    return Response(
        create_response(True, "Password reset successful", {"qr_code": qr_code}),
        status=status.HTTP_200_OK
    )



# def change_password(request):
#     email = request.data.get("email")
#     password = request.data.get("newPassword")

#     if not email:
#         return Response(
#             create_response(False, "Email is required", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     user = CustomUser.objects.get(email=email)
#     if not user:
#         return Response(
#             create_response(False, "User not found", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     secret_key = pyotp.random_base32()
#     otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
#     otp_hash = hashlib.sha256(otp.encode()).hexdigest()


#       # Save user data and otp in Redis
#     cache.set(f"user_data_pass_reset:{email}", {
#         "data": user_data,
#         "secret": secret_key,
#         "otp_hash": otp_hash,
#         "timestamp": timezone.now().isoformat()
#     }, timeout=3600)  # 60 minutes



# @api_view(['POST'])
# def verifyOTP(request):
#     otp = request.data.get('otp')
#     user_email = request.data.get('email')
    
#     # Get the user from the email
#     try:
#         user = User.objects.get(email=user_email)
#     except User.DoesNotExist:
#         return Response(
#             create_response(
#                 status=False,
#                 message="User not found",
#                 data=None
#             ),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # Fetch the OTP from the database
#     try:
#         otp_obj = OTP.objects.filter(user=user).latest('created_at')
#         if otp_obj.is_expired():
#             return Response(
#                 create_response(
#                     status=False,
#                     message="OTP expired",
#                     data=None
#                 ),
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#     except OTP.DoesNotExist:
#         return Response(
#             create_response(
#                 status=False,
#                 message="OTP not found",
#                 data=None
#             ),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # Hash the entered OTP and compare with stored hash
#     otp_hash = hashlib.sha256(otp.encode()).hexdigest()
#     send_welcome_email.delay(user_email="abhinav0427@gmail.com", name="Abhinav Srivastava")
#     if otp_hash == otp_obj.otp_hash:
#         qr_code = generate_qr_code(user.email, user.otp_secret)
#         return Response(
#             create_response(
#                 status=True,
#                 message="OTP verified successfully",
#                 data={"qr_code": qr_code}
#             ),
#             status=status.HTTP_200_OK
#         )
#     else:
#         return Response(
#             create_response(
#                 status=False,
#                 message="Invalid OTP",
#                 data=None
#             ),
#             status=status.HTTP_400_BAD_REQUEST
#         )

# @api_view(['POST'])
# def resendOTP(request):
#     user_email = request.data.get('email')
    
#     # Get the user from the email
#     try:
#         user = User.objects.get(email=user_email)
#     except User.DoesNotExist:
#         return Response(
#             create_response(
#                 status=False,
#                 message="User not found",
#                 data=None
#             ),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # Fetch the latest OTP or create a new one
#     otp_obj, created = OTP.objects.get_or_create(user=user)
    
#     if created:
#         otp = otp_obj.generate_otp()  # Generate and save OTP if it's the first time
#     else:
#         if otp_obj.is_expired():
#             otp = otp_obj.generate_otp()  # Generate a new OTP if expired
#         else:
#             return Response(
#                 create_response(
#                     status=False,
#                     message="OTP is still valid, please wait until it expires",
#                     data=None
#                 ),
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#     # Send OTP via Email
#     context = {"otp": otp}
#     email_sent = EmailService.send_email("otp_email", user.email, from_email="no-reply@scaninfoga.com", context=context)
    
#     if email_sent:
#         return Response(
#             create_response(
#                 status=True,
#                 message="OTP resent successfully",
#                 data=None
#             ),
#             status=status.HTTP_200_OK
#         )
#     else:
#         return Response(
#             create_response(
#                 status=False,
#                 message="Failed to resend OTP",
#                 data=None
#             ),
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


@api_view(['POST'])
def resendOTP(request):
    email = request.data.get('email')
    otp_type = request.data.get('type', 'registration')  # registration or password_reset

    if not email:
        return Response(
            create_response(False, "Email is required", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    if otp_type == 'registration':
        cache_key = f"user_data:{email}"
    elif otp_type == 'password_reset':
        cache_key = f"user_data_pass_reset:{email}"
    else:
        return Response(
            create_response(False, "Invalid OTP type", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    cached = cache.get(cache_key)
    if not cached:
        return Response(
            create_response(False, "No OTP found. Please register or initiate password reset first.", None),
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if OTP is still valid (less than 60 mins)
    timestamp = timezone.datetime.fromisoformat(cached['timestamp'])
    elapsed = (timezone.now() - timestamp).total_seconds()

    # if elapsed < 300:  # Allow resend only if more than 5 minutes passed
    #     return Response(
    #         create_response(False, "OTP is still valid. Please wait before requesting a new OTP.", None),
    #         status=status.HTTP_400_BAD_REQUEST
    #     )

    # Generate new OTP
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    print("THIS IS NEW OTP", otp)
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    cached['otp_hash'] = otp_hash
    cached['timestamp'] = timezone.now().isoformat()

    # Update cache
    cache.set(cache_key, cached, timeout=3600)

    name = None
    if otp_type == 'registration':
        user_data = cached.get("data")
        name = user_data["first_name"] + " " + user_data["last_name"]
    else:
        try:
            user = CustomUser.objects.get(email=email)
            name = user.first_name + " " + user.last_name
        except CustomUser.DoesNotExist:
            name = "User"

    # Send OTP via email
    send_otp_email.delay(name=name, otp=otp, user_email=email)

    return Response(
        create_response(True, "OTP resent successfully", None),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
def loginUser(request):
    all_headers = dict(request.headers)
    email = request.data.get('email')
    password = request.data.get('password')
    otp = request.data.get('otp')
    userType = request.data.get('userType')
    
    # First step: Email and password authentication
    if not all([email, password, userType]):
        return Response(
            create_response(
                status=False,
                message="Please provide email, password and user type",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    if userType not in ['crp', 'dev', 'user', 'admin']:
        return Response(
            create_response(
                status=False,
                message="Invalid user type",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    hashedPassword = hashlib.sha256(password.encode()).hexdigest()
    user = authenticate(email=email, password=hashedPassword)

    if not user:
        return Response(
            create_response(
                status=False,
                message="Invalid credentials",
                data=None
            ),
            status=status.HTTP_401_UNAUTHORIZED
        )
        
    user_type_map = {
        'crp': 'CORPORATE',
        'dev': 'DEVELOPER',
        'user': 'USER',
        'admin': 'ADMIN'
    }
    
    if user.user_type != user_type_map.get(userType):
        return Response(
            create_response(
                status=False,
                message=f"Invalid login. Please use {user.user_type.lower()} login",
                data=None
            ),
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Second step: Request OTP
    if not otp:
        return Response(
            create_response(
                status=True,
                message="Please provide OTP",
                data={'require_otp': True}
            ),
            status=status.HTTP_200_OK
        )

    # # Third step: Verify OTP and generate token
    # totp = pyotp.TOTP(user.otp_secret)
    # if not totp.verify(otp):
    #     return Response(
    #         create_response(
    #             status=False,
    #             message="Invalid OTP",
    #             data=None
    #         ),
    #         status=status.HTTP_401_UNAUTHORIZED
    #     )

    # Generate token and complete login
    from core.utils import create_token
    # token = create_token(user)
    refresh = RefreshToken.for_user(user)
    token = str(refresh.access_token)

    raw = request.headers.get('Clientinfo')
    clientinfo = {}
    if raw:
        try:
            clientinfo = json.loads(raw)
        except json.JSONDecodeError:
            return Response(
                create_response(False, "Malformed Clientinfo header", None),
                status=status.HTTP_400_BAD_REQUEST
            )

    user_data = {
        'email': user.email,
        'firstName': user.first_name,
        'lastName': user.last_name,
        'userType': user.user_type,
        'dateJoined': user.date_joined,
        "ipAddress": clientinfo.get('ip') or request.META.get('REMOTE_ADDR'),
        "device": clientinfo.get('device', 'Unknown'),
        "browser": clientinfo.get('browser', 'Unknown'),
        "latitude": clientinfo.get('latitude', '0'),
        "longitude": clientinfo.get('longitude', '0'),
        "subscriptionPlan": user.subscription_plan,
        "subscriptionDate": user.subscription_date,
        "phone": user.phone,
    }

    UserSession.objects.create(
        user=user,
        ipAddress=clientinfo.get('ip') or request.META.get('REMOTE_ADDR'),
        device=clientinfo.get('device', 'Unknown'),
        browser=clientinfo.get('browser', 'Unknown'),
        latitude=clientinfo.get('latitude', '0'),
        longitude=clientinfo.get('longitude', '0'),

        userAgent=clientinfo.get('userAgent', ''),
        platform=clientinfo.get('platform', ''),
        language=clientinfo.get('language', ''),
        cookiesEnabled=clientinfo.get('cookiesEnabled', True),
        javascriptEnabled=clientinfo.get('javascriptEnabled', True),
        touchSupport=clientinfo.get('touchSupport', False),
        deviceType=clientinfo.get('deviceType', ''),
        cpuCores=clientinfo.get('cpuCores'),
        memory=clientinfo.get('memory', ''),
        screenSize=clientinfo.get('screenSize', ''),
        batteryLevel=clientinfo.get('batteryLevel', ''),
        isCharging=clientinfo.get('isCharging', False),
        gpuRenderer=clientinfo.get('gpuRenderer', ''),
        cameras=clientinfo.get('cameras', ''),
        microphones=clientinfo.get('microphones', ''),
        publicIp=clientinfo.get('publicIp', ''),
        isp=clientinfo.get('isp', ''),
        asn=clientinfo.get('asn', ''),
        city=clientinfo.get('city', ''),
        country=clientinfo.get('country', ''),
        possibleIoT=clientinfo.get('possibleIoT', False)
    )

    return Response(
        create_response(
            status=True,
            message="Login successful",
            data={'user': user_data, 'accessToken': token}
        ),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protectedApi(request):
    return Response(
        create_response(
            status=True,
            message="Access granted to protected API",
            data={
                'user': {
                    'email': request.user.email,
                    'firstName': request.user.first_name,
                    'lastName': request.user.last_name
                }
            }
        )
    )

@api_view(['POST'])
def googleAuth(request):
    try:
        idToken = request.data.get('idToken')
        backend = request.data.get('backend')
        grant_type = request.data.get('grant_type')

        if not all([idToken, backend, grant_type]):
            return Response(
                create_response(
                    status=False,
                    message="ID token, backend, and grant_type are required",
                    data=None
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        if backend != 'google-oauth2' or grant_type != 'convert_token':
            return Response(
                create_response(
                    status=False,
                    message="Invalid backend or grant_type",
                    data=None
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify Google token
        idInfo = id_token.verify_oauth2_token(
            idToken,
            requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID
        )

        # Additional verification
        if idInfo['aud'] != settings.GOOGLE_OAUTH_CLIENT_ID:
            raise ValueError('Invalid audience')
        if idInfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid issuer')

        email = idInfo['email']
        firstName = idInfo.get('given_name', '')
        lastName = idInfo.get('family_name', '')

        # Check if user exists or create new one
        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                'first_name': firstName,
                'last_name': lastName,
            }
        )

        # Generate JWT token
        refresh = RefreshToken.for_user(user)

        # Create user session
        userAgentString = request.META.get('HTTP_USER_AGENT', '')
        userAgent = parse(userAgentString)
        
        UserSession.objects.create(
            user=user,
            ipAddress=request.META.get('REMOTE_ADDR', ''),
            device=f"{userAgent.device.family} {userAgent.device.model}",
            browser=f"{userAgent.browser.family} {userAgent.browser.version_string}",
            location=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')),
            sessionStartTime=timezone.now()
        )

        return Response(
            create_response(
                status=True,
                message="Google authentication successful",
                data={
                    'user': {
                        'email': user.email,
                        'firstName': user.first_name,
                        'lastName': user.last_name,
                        'isNewUser': created
                    },
                    'accessToken': str(refresh.access_token)
                }
            ),
            status=status.HTTP_200_OK
        )


    except ValueError as e:
        return Response(
            create_response(
                status=False,
                message="Invalid Google token",
                data=str(e)
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
def registerDeveloper(request):
    serializer = DeveloperRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        developer = serializer.save()
        return Response(
            create_response(
                status=True,
                message="Developer registered successfully",
                data={
                    'email': developer.user.email,
                    'firstName': developer.first_name,
                    'lastName': developer.last_name
                }
            ),
            status=status.HTTP_201_CREATED
        )
    return Response(
        create_response(
            status=False,
            message="Registration failed",
            data=serializer.errors
        ),
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['POST'])
def registerCorporate(request):
    serializer = CorporateRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        corporate = serializer.save()
        return Response(
            create_response(
                status=True,
                message="Corporate registration submitted for approval",
                data={
                    'email': corporate.user.email,
                    'firstName': corporate.first_name,
                    'lastName': corporate.last_name,
                    'company': corporate.company,
                    'domain': corporate.domain,
                    'approvalStatus': corporate.approval_status
                }
            ),
            status=status.HTTP_201_CREATED
        )
    return Response(
        create_response(
            status=False,
            message="Registration failed",
            data=serializer.errors
        ),
        status=status.HTTP_400_BAD_REQUEST
    )

    if CustomUser.objects.filter(email=email).exists():
        return Response(
            create_response(
                status=False,
                message="This email is already registered. Please use a different email.",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

def generate_qr_code(email, secret_key):
    totp = pyotp.TOTP(secret_key)
    provisioning_uri = totp.provisioning_uri(email, issuer_name="YourApp")
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_code = base64.b64encode(buffer.getvalue()).decode()
    
    return qr_code

@api_view(['POST'])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def get_user_map(request):
    user_location_lng = request.data.get('userLng')
    user_location_lat = request.data.get('userLat')
    address = request.data.get('address')
    
    if not all([user_location_lat, user_location_lng, address]):
        return Response(
            create_response(
                status=False,
                message="Please provide user's location and address location",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        api_response = fetch_map(
            starting_point_lng=user_location_lng, 
            starting_point_lat=user_location_lat, 
            address=address
        )
        
        # Option 1: Return base64 encoded image in JSON response
        return Response(
            create_response(
                status=api_response['success'],
                message="Map fetched successfully",
                data=api_response['data']
            ),
            status=status.HTTP_200_OK
        )
        
        # Option 2: Return image directly
        # image_data = base64.b64decode(api_response['data']['image'])
        # return HttpResponse(
        #     image_data,
        #     content_type=api_response.get('content_type', 'image/png')
        # )
    
    except Exception as e:
        return Response(
            create_response(
                status=False,
                message="Error fetching map",
                data=str(e)
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def changePassword(request):
    email = request.data.get('email')
    password = request.data.get('oldPassword')
    newPassword = request.data.get('newPassword')
    otp = request.data.get("otp")
    if not all([email, password, newPassword]):
        return Response(
            create_response(
                status=False,
                message="Please provide email, password and new password",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    hashedPassword = hashlib.sha256(password.encode()).hexdigest()
    user = authenticate(email=email, password=hashedPassword)
    if not user:
        return Response(
            create_response(
                status=False,
                message="Invalid credentials",
                data=None
            ),
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not otp:
        return Response(
            create_response(
                status=True,
                message="Please provide OTP",
                data={'require_otp': True}
            ),
            status=status.HTTP_200_OK
        )
    # Third step: Verify OTP and generate token
    totp = pyotp.TOTP(user.otp_secret)
    if not totp.verify(otp):
        return Response(
            create_response(
                status=False,
                message="Invalid OTP",
                data=None
            ),
            status=status.HTTP_401_UNAUTHORIZED
        )

    newPasswordHashed = hashlib.sha256(newPassword.encode()).hexdigest()
    user.set_password(newPasswordHashed)
    user.save()

    return Response(
        create_response(
            status=True,
            message="Password changed successfully",
            data=None
        ),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
def changeEmail(request):
    current_email = request.data.get('email')
    password = request.data.get('password')
    new_email = request.data.get('newEmail')
    otp = request.data.get("otp")

    if not all([current_email, password, new_email]):
        return Response(
            create_response(
                status=False,
                message="Please provide current email, password, and new email",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    hashedPassword = hashlib.sha256(password.encode()).hexdigest()
    user = authenticate(email=current_email, password=hashedPassword)

    new_email_exists = CustomUser.objects.filter(email=new_email).exists()

    if(new_email_exists):
        return Response(
            create_response(
                status=False,
                message="This email is already registered. Please use a different email.",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    if(new_email == current_email):
        return Response(
            create_response(
                status=False,
                message="New email cannot be current email.",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user:
        return Response(
            create_response(
                status=False,
                message="Invalid credentials",
                data=None
            ),
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not otp:
        return Response(
            create_response(
                status=True,
                message="Please provide OTP",
                data={'require_otp': True}
            ),
            status=status.HTTP_200_OK
        )

    totp = pyotp.TOTP(user.otp_secret)
    if not totp.verify(otp):
        return Response(
            create_response(
                status=False,
                message="Invalid OTP",
                data=None
            ),
            status=status.HTTP_401_UNAUTHORIZED
        )

    secret_key = pyotp.random_base32()
    user.email = new_email
    user.otp_secret = secret_key
    user = user.save()
    qr_code = generate_qr_code(user.email, secret_key)

    return Response(
        create_response(
            status=True,
            message="Email changed successfully",
            data={'qr_code': qr_code}
        ),
        status=status.HTTP_200_OK
    )

@api_view(['POST'])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def get_user_location_map(request):
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    
    if not all([lat, lng]):
        return Response(
            create_response(
                status=False,
                message="Please provide user's location",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        api_response = fetch_location_map(
            lat=lat,
            lng=lng
        )
        print("API Response: ", api_response)
        return Response(
            create_response(
                status=api_response['success'],
                message="Map fetched successfully",
                data=api_response['data']
            ),
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            create_response(
                status=False,
                message="Error fetching map",
                data=str(e)
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_user_session(request):
#     token = get_token_from_header(request)
#     user = get_user_from_token(token)

#     session_list = UserSession.objects.filter(user=user)
#     serialized = UserSessionSerializer(session_list, many=True)

#     return Response(
#         create_response(
#             status=True,
#             message="User sessions fetched successfully",
#             data=serialized.data
#         ),
#         status=status.HTTP_200_OK
#     )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_session(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)

    queryset = UserSession.objects.filter(user=user).order_by('-created_at')

    paginated_data = paginate_queryset(request, queryset, UserSessionSerializer)

    return Response(
        create_response(
            status=True,
            message="User sessions fetched successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )

# @api_view(['GET'])
# def get_all_users(request):
#     try:
#         count = int(request.query_params.get('count', 25))
#         page = int(request.query_params.get('page', 1))
#         if page < 1 or count < 1:
#             raise ValueError
#     except ValueError:
#         return Response(
#             create_response(False, "Invalid count or page number", None),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     users = CustomUser.objects.select_related('corporate_profile', 'developer_profile', 'wallet')

#     # 🔍 Global Search
#     search = request.GET.get('search')
#     if search:
#         users = users.filter(
#             Q(email__icontains=search) |
#             Q(corporate_profile__first_name__icontains=search) |
#             Q(corporate_profile__last_name__icontains=search) |
#             Q(corporate_profile__company__icontains=search) |
#             Q(corporate_profile__domain__icontains=search) |
#             Q(developer_profile__first_name__icontains=search) |
#             Q(developer_profile__last_name__icontains=search)
#         )

#     # ✅ Dynamic filters: exact, startswith, endswith, icontains
#     dynamic_filters = {
#         'email': ['email'],
#         'first_name': ['first_name', 'corporate_profile__first_name', 'developer_profile__first_name'],
#         'last_name': ['last_name', 'corporate_profile__last_name', 'developer_profile__last_name'],
#         'company': ['corporate_profile__company'],
#         'domain': ['corporate_profile__domain'],
#         'approval_status': ['corporate_profile__approval_status', 'developer_profile__approval_status'],
#     }

#     for param, paths in dynamic_filters.items():
#         for suffix in ['', '__exact', '__startswith', '__endswith', '__icontains']:
#             key = f"{param}{suffix}"
#             if val := request.GET.get(key):
#                 q = Q()
#                 for path in paths:
#                     try:
#                         q |= Q(**{f"{path}{suffix}": val})
#                     except Exception:
#                         pass  # Avoid OneToOneRel join errors
#                 users = users.filter(q)

#     # 🔁 Simple filters
#     simple_filters = {
#         'id': 'id',
#         'user_type': 'user_type',
#         'is_active': 'is_active',
#         'is_staff': 'is_staff',
#     }
#     for param, field in simple_filters.items():
#         if val := request.GET.get(param):
#             users = users.filter(**{field: val})

#     # 📆 Date filters
#     for field in ['date_joined', 'last_login']:
#         if val := request.GET.get(f'{field}__gte'):
#             users = users.filter(**{f'{field}__gte': val})
#         if val := request.GET.get(f'{field}__lte'):
#             users = users.filter(**{f'{field}__lte': val})

#     # 💸 Annotations
#     spent_subquery = Transaction.objects.filter(
#         user=OuterRef('pk'),
#         status='success'
#     ).values('user').annotate(total=Sum('amount')).values('total')

#     users = users.annotate(
#         wallet_balance=Coalesce(
#             F('wallet__balance'),
#             Value(0),
#             output_field=DecimalField(max_digits=10, decimal_places=2)
#         ),
#         total_spent=Coalesce(
#             Subquery(spent_subquery, output_field=DecimalField(max_digits=10, decimal_places=2)),
#             Value(0),
#             output_field=DecimalField(max_digits=10, decimal_places=2)
#         ),
#         profile_first_name=Case(
#             When(user_type='CORPORATE', then=F('corporate_profile__first_name')),
#             When(user_type='DEVELOPER', then=F('developer_profile__first_name')),
#             When(user_type='USER', then=F('first_name')),
#             default=Value(''),
#             output_field=CharField()
#         ),
#         profile_last_name=Case(
#             When(user_type='CORPORATE', then=F('corporate_profile__last_name')),
#             When(user_type='DEVELOPER', then=F('developer_profile__last_name')),
#             When(user_type='USER', then=F('last_name')),
#             default=Value(''),
#             output_field=CharField()
#         ),
#         session_last_login=Max('usersession__created_at')
#     )

#     # 🔢 Range filters
#     for field in ['wallet_balance', 'total_spent', 'session_last_login']:
#         if val := request.GET.get(f'{field}__gte'):
#             users = users.filter(**{f'{field}__gte': val})
#         if val := request.GET.get(f'{field}__lte'):
#             users = users.filter(**{f'{field}__lte': val})

#     # 📊 Ordering
#     ordering = request.GET.get('ordering', 'email')
#     valid_ordering_fields = [
#         'email', 'date_joined', 'session_last_login',
#         'wallet_balance', 'total_spent',
#         'profile_first_name', 'profile_last_name', 'id'
#     ]
#     if ordering.lstrip('-') in valid_ordering_fields:
#         users = users.order_by(ordering)

#     # 📄 Pagination
#     total_count = users.count()
#     paginated_users = users[(page - 1) * count: page * count]

#     serializer = UserListSerializer(paginated_users, many=True)
#     return Response(
#         create_response(
#             True,
#             "Users retrieved successfully",
#             data={
#                 'users': serializer.data,
#                 'total_count': total_count,
#                 'page': page,
#                 'count': count
#             }
#         ),
#         status=status.HTTP_200_OK
#     )

from decimal import Decimal
from django.db.models import (
    Q, F, Value, Case, When, Max, OuterRef, Subquery, Sum, DecimalField, CharField
)
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET'])
def get_all_users(request):
    users = CustomUser.objects.select_related('corporate_profile', 'developer_profile', 'wallet')

    # 🔍 Global Search
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(corporate_profile__first_name__icontains=search) |
            Q(corporate_profile__last_name__icontains=search) |
            Q(corporate_profile__company__icontains=search) |
            Q(corporate_profile__domain__icontains=search) |
            Q(developer_profile__first_name__icontains=search) |
            Q(developer_profile__last_name__icontains=search)
        )

    # ✅ Dynamic filters
    dynamic_filters = {
        'email': ['email'],
        'first_name': ['first_name', 'corporate_profile__first_name', 'developer_profile__first_name'],
        'last_name': ['last_name', 'corporate_profile__last_name', 'developer_profile__last_name'],
        'company': ['corporate_profile__company'],
        'domain': ['corporate_profile__domain'],
        'approval_status': ['corporate_profile__approval_status', 'developer_profile__approval_status'],
    }
    for param, paths in dynamic_filters.items():
        for suffix in ['', '__exact', '__startswith', '__endswith', '__icontains']:
            key = f"{param}{suffix}"
            if val := request.GET.get(key):
                q = Q()
                for path in paths:
                    try:
                        q |= Q(**{f"{path}{suffix}": val})
                    except Exception:
                        pass
                users = users.filter(q)

    # 🔁 Simple filters
    simple_filters = {
        'id': 'id',
        'user_type': 'user_type',
        'is_active': 'is_active',
        'is_staff': 'is_staff',
    }
    for param, field in simple_filters.items():
        if val := request.GET.get(param):
            users = users.filter(**{field: val})

    # 📆 Date filters
    # for field in ['date_joined', 'last_login', 'created_at']:
    #     if val := request.GET.get(f'{field}__gte'):
    #         users = users.filter(**{f'{field}__gte': val})
    #     if val := request.GET.get(f'{field}__lte'):
    #         users = users.filter(**{f'{field}__lte': val})
    for field in ['date_joined', 'last_login', 'created_at']:
        if val := request.GET.get(f'{field}__gte'):
            users = users.filter(**{f'{field}__gte': val})
        if val := request.GET.get(f'{field}__lte'):
            try:
                # Parse the date and extend to end of day
                date_val = datetime.strptime(val, '%Y-%m-%d') + timedelta(days=1)
                users = users.filter(**{f'{field}__lt': date_val})
            except ValueError:
                # If full datetime is passed, use it as is
                users = users.filter(**{f'{field}__lte': val})

    # 💸 Annotations
    spent_subquery = Transaction.objects.filter(
        user=OuterRef('pk'),
        status='success'
    ).values('user').annotate(total=Sum('amount')).values('total')

    users = users.annotate(
        wallet_balance=Coalesce(
            F('wallet__balance'),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ),
        total_spent=Coalesce(
            Subquery(
                spent_subquery,
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ),
        profile_first_name=Case(
            When(user_type='CORPORATE', then=F('corporate_profile__first_name')),
            When(user_type='DEVELOPER', then=F('developer_profile__first_name')),
            When(user_type='USER', then=F('first_name')),
            default=Value(''),
            output_field=CharField()
        ),
        profile_last_name=Case(
            When(user_type='CORPORATE', then=F('corporate_profile__last_name')),
            When(user_type='DEVELOPER', then=F('developer_profile__last_name')),
            When(user_type='USER', then=F('last_name')),
            default=Value(''),
            output_field=CharField()
        ),
        session_last_login=Max('usersession__created_at')
    )

    # 🔢 Range filters for annotated fields
    for field in ['wallet_balance', 'total_spent', 'session_last_login']:
        if val := request.GET.get(f'{field}__gte'):
            users = users.filter(**{f'{field}__gte': val})
        if val := request.GET.get(f'{field}__lte'):
            users = users.filter(**{f'{field}__lte': val})

    # 📊 Ordering
    ordering = request.GET.get('ordering', 'email')
    valid_ordering_fields = [
        'email', 'date_joined', 'session_last_login',
        'wallet_balance', 'total_spent',
        'profile_first_name', 'profile_last_name', 'id'
    ]
    if ordering.lstrip('-') in valid_ordering_fields:
        users = users.order_by(ordering)

    # 📄 Pagination using shared paginate_queryset helper
    paginated_data = paginate_queryset(request, users, UserListSerializer)

    return Response(
        create_response(
            status=True,
            message="Users retrieved successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_bookmark(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)

    bookmark_page = request.data.get("bookmarkPage")
    payload = request.data.get("payload")
    latitude = request.data.get("latitude")
    longitude = request.data.get("longitude")
    investigator = request.data.get("investigator")
    case_type = request.data.get("caseType")
    case_description = request.data.get("caseDescription")
    

    if not bookmark_page or not payload or not latitude or not longitude or not investigator or not case_type or not case_description:
        return Response(create_response(False, "Bookmark Page, Payload, Latitude, Longitude, Investigator, Case Type, Case Description is required", None), status=status.HTTP_400_BAD_REQUEST)

    saved_obj = Bookmark.objects.create(user=user, bookmark_page=bookmark_page, payload=payload, latitude=latitude, longitude=longitude, investigator=investigator, case_type=case_type, case_description=case_description)

    return Response(create_response(True, f'Bookmark added successfully with case ID: {saved_obj.id}', data={"case_id": saved_obj.id}), status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_bookmark_list(request):
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)
    
    bookmark_list = Bookmark.objects.filter(user=user)
    serializer = BookmarkSerializer(bookmark_list, many=True)
    return Response(create_response(True, "Bookmark list retrieved successfully", serializer.data), status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_bookmark_by_id(request):
    """
    Deletes a Bookmark by formatted ID (e.g., SCA000123)
    """

    bookmark_id = request.data.get("caseId")
    try:
        token = get_token_from_header(request=request)
        user = get_user_from_token(token)

        # Extract the raw integer ID from formatted ID
        if not bookmark_id.startswith('SCA'):
            return Response(create_response(False, 'Invalid Bookmark ID format', None), status=status.HTTP_400_BAD_REQUEST)

        raw_id = int(bookmark_id.replace('SCA', '').lstrip('0'))

        bookmark = Bookmark.objects.get(user=user, pk=raw_id)
        bookmark.delete()

        return Response(create_response(True, 'Bookmark deleted successfully', None), status=status.HTTP_200_OK)

    except Bookmark.DoesNotExist:
        return Response(create_response(False, 'Bookmark not found', None), status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response(create_response(False, f'An error occurred: {str(e)}', None), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def update_bookmark_status(request):
    id = request.data.get("caseId")
    case_status = request.data.get('status')
    investigator = request.data.get('investigator')

    if(not id or not case_status or not investigator or not case_status in ['pending', 'success']):
        return Response(create_response(False, 'Invalid request', None), status=status.HTTP_400_BAD_REQUEST)
    
    token = get_token_from_header(request=request)
    user = get_user_from_token(token)

    # Extract the raw integer ID from formatted ID
    if not id.startswith('SCA'):
        return Response(create_response(False, 'Invalid Bookmark ID format', None), status=status.HTTP_400_BAD_REQUEST)

    raw_id = int(id.replace('SCA', '').lstrip('0'))

    bookmark = Bookmark.objects.get(user=user, pk=raw_id)
    bookmark.status = case_status
    bookmark.investigator = investigator
    bookmark.updated_at = timezone.now()
    bookmark.save()

    return Response(create_response(True, 'Bookmark status updated successfully', None), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_phone(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    phone = request.data.get('phone')
    if not phone:
        return Response(create_response(False, 'Phone number is required', None), status=status.HTTP_400_BAD_REQUEST)
    
    user.phone = phone
    user.save()
    return Response(create_response(True, 'Phone number updated successfully', None), status=status.HTTP_200_OK)