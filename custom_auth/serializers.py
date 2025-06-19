from rest_framework import serializers
from .models import CustomUser, DeveloperProfile, CorporateProfile, UserSession, Bookmark
import hashlib
from payments.models import Transaction, WalletBalance

class UserRegistrationSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'firstName', 'lastName']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        email = validated_data.pop('email')
        
        user = CustomUser.objects.create_user(
            email=email,
            password=hashed_password,
            user_type='USER',
            **validated_data
        )
        return user

class DeveloperRegistrationSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = DeveloperProfile
        fields = ['firstName', 'lastName', 'email', 'password']
        extra_kwargs = {'email': {'write_only': True}}

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        user = CustomUser.objects.create_user(
            email=email,
            password=hashed_password,
            user_type='DEVELOPER'
        )
        
        developer = DeveloperProfile.objects.create(
            user=user,
            **validated_data
        )
        return developer

class CorporateRegistrationSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)  # Add this line
    userType = serializers.CharField(write_only=True, default='crp')  # Add this line
    
    class Meta:
        model = CorporateProfile
        fields = ['firstName', 'lastName', 'company', 'domain', 'email', 'password', 'userType']

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        validated_data.pop('userType', None)  # Remove userType from validated_data
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        user = CustomUser.objects.create_user(
            email=email,
            password=hashed_password,
            user_type='CORPORATE'
        )
        
        corporate = CorporateProfile.objects.create(
            user=user,
            **validated_data
        )
        return corporate

class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ['user', 'created_at', 'ipAddress', 'device', 'browser', 'latitude', 'longitude']

class UserListSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    approval_status = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    domain = serializers.SerializerMethodField()
    wallet_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    last_session = serializers.SerializerMethodField()
    session_last_login = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'user_type', 'date_joined', 'session_last_login',
            'first_name', 'last_name', 'company', 'domain', 'approval_status',
            'wallet_balance', 'total_spent', 'last_session'
        ]

    # def get_first_name(self, obj):
    #     profile = getattr(obj, f'{obj.user_type.lower()}_profile', None)
    #     return profile.first_name if profile else ''

    # def get_last_name(self, obj):
    #     profile = getattr(obj, f'{obj.user_type.lower()}_profile', None)
    #     return profile.last_name if profile else ''

    def get_first_name(self, obj):
        return getattr(obj, 'profile_first_name', '') or ''

    def get_last_name(self, obj):
        return getattr(obj, 'profile_last_name', '') or ''

    def get_approval_status(self, obj):
        profile = getattr(obj, f'{obj.user_type.lower()}_profile', None)
        return profile.approval_status if profile else ''

    def get_company(self, obj):
        return obj.corporate_profile.company if obj.user_type == 'CORPORATE' and hasattr(obj, 'corporate_profile') else ''

    def get_domain(self, obj):
        return obj.corporate_profile.domain if obj.user_type == 'CORPORATE' and hasattr(obj, 'corporate_profile') else ''

    def get_last_session(self, obj):
        session = obj.usersession_set.order_by('-created_at').first()
        if session:
            return {
                'ip': session.ipAddress,
                'device': session.device,
                'browser': session.browser,
                'latitude': session.latitude,
                'longitude': session.longitude
            }
        return None
    def get_session_last_login(self, obj):
        return obj.session_last_login 

class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['id', 'bookmark_page', 'created_at']