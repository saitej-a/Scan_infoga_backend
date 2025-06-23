from django.contrib.auth import get_user_model
from .models import UserActivity
import json

User = get_user_model()

def add_activity(email, api_called, request_payload=None):
    """
    Utility function to add a new user activity record
    
    Args:
        email (str): User's email
        api_called (str): Name of the API that was called
        request_payload (dict, optional): The payload sent with the request
    
    Returns:
        UserActivity: The created UserActivity instance
    """
    try:
        user = User.objects.get(email=email)
        
        if isinstance(request_payload, str):
            try:
                request_payload = json.loads(request_payload)
            except json.JSONDecodeError:
                request_payload = {"raw_content": request_payload}
        
        if request_payload is None:
            request_payload = {}
            
        activity = UserActivity.objects.create(
            user=user,
            email=email,
            api_called=api_called,
            request_payload=request_payload
        )
        return activity
    
    except User.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error adding activity for {email}: {str(e)}")
        return None

# def is_called_by_user_previously(user, api_name):
#     try:
#         user_activity = UserActivity.objects.filter(user=user, api_called=api_name)
#         return user_activity.exists()
#     except UserActivity.DoesNotExist:
#         return False 

# def is_called_by_user_previously(user, api_name, payload, full_payload = True):
#     if full_payload:
#         count = UserActivity.objects.filter(user=user, api_called=api_name, request_payload=payload).count()
#         return count > 1
#     else:
#         count = UserActivity.objects.filter(
#             user=user,
#             api_called=api_name,
#             request_payload__contains=[payload])
#         return count > 1

# def is_called_by_user_previously(user, api_name, payload, full_payload=True):
#     """
#     Checks if the API was previously called by the user.
#     'realtimeData' is always ignored during comparison.

#     - If full_payload: compares the entire payload excluding 'realtimeData'.
#     - If not full_payload: searches if 'payload' exists inside any list in the stored payload (excluding 'realtimeData').
#     """
#     if full_payload:
#         # Compare by excluding 'realtimeData' key
#         filtered_payload = {k: v for k, v in payload.items() if k != "realtimeData"}

#         matching_activities = UserActivity.objects.filter(user=user, api_called=api_name)

#         for activity in matching_activities:
#             db_payload = {k: v for k, v in activity.request_payload.items() if k != "realtimeData"}
#             if db_payload == filtered_payload:
#                 return True
#         return False

#     else:
#         # Check if 'payload' exists inside any array of the JSON payload (excluding 'realtimeData')
#         matching_activities = UserActivity.objects.filter(user=user, api_called=api_name)

#         for activity in matching_activities:
#             for key, value in activity.request_payload.items():
#                 if key == "realtimeData":
#                     continue  # skip
#                 if isinstance(value, list) and payload in value:
#                     return True
#         return False

def is_called_by_user_previously(user, api_name, payload, full_payload=True):
    """
    Checks if the API was previously called by the user.
    'realtimeData' is always ignored during comparison.

    - If full_payload: compares the entire payload excluding 'realtimeData'.
    - If not full_payload: searches if 'payload' exists inside any list in the stored payload (excluding 'realtimeData').
    - In both cases, at least two occurrences (count > 1) are required to return True.
    """
    if full_payload:
        filtered_payload = {k: v for k, v in payload.items() if k != "realtimeData"}
        matching_activities = UserActivity.objects.filter(user=user, api_called=api_name)

        count = 0
        for activity in matching_activities:
            db_payload = {k: v for k, v in activity.request_payload.items() if k != "realtimeData"}
            if db_payload == filtered_payload:
                count += 1
                if count > 1:
                    return True
        return False

    else:
        matching_activities = UserActivity.objects.filter(user=user, api_called=api_name)

        count = 0
        for activity in matching_activities:
            for key, value in activity.request_payload.items():
                if key == "realtimeData":
                    continue  # skip
                if isinstance(value, list) and payload in value:
                    count += 1
                    if count > 1:
                        return True
        return False

