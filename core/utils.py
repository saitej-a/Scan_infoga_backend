import jwt
from django.conf import settings
from custom_auth.models import CustomUser

def create_response(status, message, data = None):
    return {
        "responseStatus": {
            "status": status,
            "message": message
        },
        "responseData": data
    }

def get_token_from_header(request):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        return token
    return None
    
def get_email_from_token(token):
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    email = payload.get("email")
    return email

def create_token(user):
    payload = {
        "email": user.email,
        "user_type": user.user_type
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token

def get_user_from_token(token):
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    email = payload.get("email")
    user = CustomUser.objects.get(email=email)
    return user

import math

def paginate_queryset(request, queryset, serializer_class):
    try:
        page = int(request.query_params.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = int(request.query_params.get('page_size', 10))
        if page_size < 1:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    total_count = queryset.count()
    total_pages = math.ceil(total_count / page_size)

    offset = (page - 1) * page_size

    # ✅ Only the required rows are fetched from the DB
    paginated_queryset = queryset[offset:offset + page_size]

    serialized_data = serializer_class(paginated_queryset, many=True).data

    pagination_details = {
        "count": total_count,
        "next": page + 1 if page < total_pages else None,
        "previous": page - 1 if page > 1 else None,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size
    }

    return {
        "result": serialized_data,
        "paginationDetails": pagination_details
    }
