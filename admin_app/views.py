from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.db import transaction
import uuid

from payments.models import (
    WalletHistory,
    WalletBalance,
    Transaction
)

from custom_auth.models import (
    CustomUser,
    UserSession,
    Bookmark
)

from custom_auth.serializers import (
    CustomUserSerializer,
    UserSessionDataSerializer,
    BookmarkSerializer
)

# djb

from user_activities.models import UserActivity

from user_activities.serializers import UserActivitySerializer

from payments.serializers import WalletHistorySerializer

from core.utils import create_response, paginate_queryset



# Create your views here.

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def wallet_history_list(request):
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response(create_response(message="user_id is required", status=False), status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(message="User not found", status=False),
            status=status.HTTP_404_NOT_FOUND
        )

    history = WalletHistory.objects.filter(user=user).order_by('-created_at').select_related('api_pricing')
    serializer = WalletHistorySerializer(history, many=True)
    return Response(create_response(data=serializer.data, message="Wallet history fetched successfully", status=True), status=status.HTTP_200_OK)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_user_info(request):
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response(
            create_response(message="user_id is required", status=False),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(message="User not found", status=False),
            status=status.HTTP_404_NOT_FOUND
        )

    # Pass `request` into serializer context in case `context` is used
    serializer = CustomUserSerializer(user, context={'request': request})

    return Response(
        create_response(data=serializer.data, message="User info retrieved", status=True),
        status=status.HTTP_200_OK
    )


# @api_view(['GET'])
# # @permission_classes([IsAuthenticated])
# def get_login_history(request):
#     user_id = request.query_params.get('user_id')
#     if not user_id:
#         return Response(
#             create_response(message="user_id is required", status=False),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     try:
#         user = CustomUser.objects.get(id=user_id)
#     except CustomUser.DoesNotExist:
#         return Response(
#             create_response(message="User not found", status=False),
#             status=status.HTTP_404_NOT_FOUND
#         )

#     sessions = UserSession.objects.filter(user=user).order_by('created_at')
#     serializer = UserSessionDataSerializer(sessions, many=True)

#     return Response(
#         create_response(data=serializer.data, message="Login history retrieved", status=True),
#         status=status.HTTP_200_OK
#     )

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_login_history(request):
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response(
            create_response(message="user_id is required", status=False),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(message="User not found", status=False),
            status=status.HTTP_404_NOT_FOUND
        )

    queryset = UserSession.objects.filter(user=user).order_by('-created_at')

    paginated_data = paginate_queryset(request, queryset, UserSessionDataSerializer)

    return Response(
        create_response(
            status=True,
            message="Login history retrieved successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )



# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_bookmarks_by_user(request):
#     user_id = request.query_params.get('user_id')
#     if not user_id:
#         return Response(
#             create_response(message="user_id is required", status=False),
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     try:
#         user = CustomUser.objects.get(id=user_id)
#     except CustomUser.DoesNotExist:
#         return Response(
#             create_response(message="User not found", status=False),
#             status=status.HTTP_404_NOT_FOUND
#         )

#     bookmarks = Bookmark.objects.filter(user=user).order_by('-created_at')
#     serializer = BookmarkSerializer(bookmarks, many=True)

#     return Response(
#         create_response(data=serializer.data, message="Bookmarks retrieved", status=True),
#         status=status.HTTP_200_OK
#     )

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_bookmarks_by_user(request):
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response(
            create_response(message="user_id is required", status=False),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(message="User not found", status=False),
            status=status.HTTP_404_NOT_FOUND
        )

    queryset = Bookmark.objects.filter(user=user).order_by('-created_at')

    paginated_data = paginate_queryset(request, queryset, BookmarkSerializer)

    return Response(
        create_response(
            status=True,
            message="Bookmarks retrieved successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )



@api_view(['POST'])
# @permission_classes([IsAuthenticated])
def wallet_update(request):
    user_id = request.data.get('user_id')
    amount = request.data.get('amount')
    txn_type = request.data.get('txn_type')  # Should be "credit" or "debit"
    comment = request.data.get('comment', '')

    if not user_id or not amount or not txn_type:
        return Response(
            create_response(message="user_id, amount and txn_type are required", status=False),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(message="User not found", status=False),
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return Response(
            create_response(message="Amount must be a positive number", status=False),
            status=status.HTTP_400_BAD_REQUEST
        )

    # Ensure wallet exists
    wallet, created = WalletBalance.objects.get_or_create(user=user)

    with transaction.atomic():
        if txn_type == 'credit':
            wallet.balance += amount
        elif txn_type == 'debit':
            if wallet.balance < amount:
                return Response(
                    create_response(message="Insufficient balance", status=False),
                    status=status.HTTP_400_BAD_REQUEST
                )
            wallet.balance -= amount
        else:
            return Response(
                create_response(message="Invalid txn_type (must be 'credit' or 'debit')", status=False),
                status=status.HTTP_400_BAD_REQUEST
            )

        wallet.save()

        # Create Transaction record
        txn = Transaction.objects.create(
            txn_id=f"TXN-{uuid.uuid4().hex[:10]}",
            amount=amount,
            user=user,
            status=Transaction.Status.SUCCESS,
            comment=comment,
            credited_amount=amount if txn_type == 'credit' else Decimal('0.0')
        )

        # Create WalletHistory record
        WalletHistory.objects.create(
            user=user,
            wallet=wallet,
            txn_type=txn_type,
            amount=amount,
            balance_after=wallet.balance,
            comment=comment,
            transaction=txn
        )

    return Response(
        create_response(message=f"Wallet {txn_type} successful", status=True, data={
            'wallet_balance': str(wallet.balance),
            'transaction_id': txn.txn_id
        }),
        status=status.HTTP_200_OK
    )



@api_view(['GET'])
def get_user_wallet_balance(request):
    user_id = request.query_params.get('user_id')
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(message="User not found", status=False),
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        wallet = WalletBalance.objects.get(user=user)
        last_success_txn = Transaction.objects.filter(
            user=user, status=Transaction.Status.SUCCESS
        ).order_by('-created_at').first()
        
        txn_data = {
            "txn_id": last_success_txn.txn_id,
            "amount": str(last_success_txn.amount),
            "status": last_success_txn.status,
            "created_at": last_success_txn.created_at.isoformat()
        } if last_success_txn else None
        
        return Response(
            create_response(
                status=True,
                message="Wallet balance retrieved successfully",
                data={
                    "balance": str(wallet.balance),
                    "last_successful_transaction": txn_data
                }
            ),
            status=status.HTTP_200_OK
        )
    
    except WalletBalance.DoesNotExist:
        return Response(
            create_response(
                status=False,
                message="Wallet balance not found for user",
                data=None
            ),
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
# @permission_classes([IsAuthenticated])  # Uncomment if you want auth
def get_user_activity(request):
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response(
            create_response(message="user_id is required", status=False),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            create_response(message="User not found", status=False),
            status=status.HTTP_404_NOT_FOUND
        )

    queryset = UserActivity.objects.filter(email=user.email).order_by('-activity_time')

    paginated_data = paginate_queryset(request, queryset, UserActivitySerializer)

    return Response(
        create_response(
            status=True,
            message="User activity retrieved successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )
