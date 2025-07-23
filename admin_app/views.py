from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
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

from payments.serializers import WalletHistorySerializer, TransactionSerializer

from core.utils import create_response, paginate_queryset



# Create your views here.

# @api_view(['GET'])
# # @permission_classes([IsAuthenticated])
# def wallet_history_list(request):
#     user_id = request.query_params.get('user_id')
#     if not user_id:
#         return Response(create_response(message="user_id is required", status=False), status=status.HTTP_400_BAD_REQUEST)

#     try:
#         user = CustomUser.objects.get(id=user_id)
#     except CustomUser.DoesNotExist:
#         return Response(
#             create_response(message="User not found", status=False),
#             status=status.HTTP_404_NOT_FOUND
#         )

#     history = WalletHistory.objects.filter(user=user).order_by('-created_at').select_related('api_pricing')
#     serializer = WalletHistorySerializer(history, many=True)
#     return Response(create_response(data=serializer.data, message="Wallet history fetched successfully", status=True), status=status.HTTP_200_OK)



@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def wallet_history_list(request):
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

    queryset = WalletHistory.objects.filter(user=user).order_by('-created_at').select_related('api_pricing')

    paginated_data = paginate_queryset(request, queryset, WalletHistorySerializer)

    return Response(
        create_response(
            status=True,
            message="Wallet history fetched successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )





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



# @api_view(['GET'])
# def get_user_wallet_balance(request):
#     user_id = request.query_params.get('user_id')
    
#     try:
#         user = CustomUser.objects.get(id=user_id)
#     except CustomUser.DoesNotExist:
#         return Response(
#             create_response(message="User not found", status=False),
#             status=status.HTTP_404_NOT_FOUND
#         )
    
#     try:
#         wallet = WalletBalance.objects.get(user=user)
#         last_success_txn = Transaction.objects.filter(
#             user=user, status=Transaction.Status.SUCCESS
#         ).order_by('-created_at').first()

#         transaction_total = transaction_total = Transaction.objects.filter(
#     user=user, 
#     status=Transaction.Status.SUCCESS
# ).aggregate(total=Sum('amount'))['total'] or 0

        
#         txn_data = {
#             "txn_id": last_success_txn.txn_id,
#             "amount": str(last_success_txn.amount),
#             "status": last_success_txn.status,
#             "created_at": last_success_txn.created_at.isoformat(),
#             "total_transaction": transaction_total
#         } if last_success_txn else None
        
#         return Response(
#             create_response(
#                 status=True,
#                 message="Wallet balance retrieved successfully",
#                 data={
#                     "balance": str(wallet.balance),
#                     "last_successful_transaction": txn_data
#                 }
#             ),
#             status=status.HTTP_200_OK
#         )
    
#     except WalletBalance.DoesNotExist:
#         return Response(
#             create_response(
#                 status=False,
#                 message="Wallet balance not found for user",
#                 data=None
#             ),
#             status=status.HTTP_404_NOT_FOUND
#         )


from django.db.models import Sum, F, ExpressionWrapper, DecimalField

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
        
        # Last successful transaction
        last_success_txn = Transaction.objects.filter(
            user=user, status=Transaction.Status.SUCCESS
        ).order_by('-created_at').first()

        transaction_total = Transaction.objects.filter(
            user=user, 
            status=Transaction.Status.SUCCESS
        ).aggregate(total=Sum('amount'))['total'] or 0

        credited_in_wallet = Transaction.objects.filter(
            user=user, 
            status=Transaction.Status.SUCCESS
        ).aggregate(total=Sum('credited_amount'))['total'] or 0

        total_debited = WalletHistory.objects.filter(
            user=user, txn_type=WalletHistory.TransactionType.DEBIT
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Total deductions: sum of (Transaction.amount - credited_amount) for all SUCCESS transactions
        transactions = Transaction.objects.filter(
            user=user, status=Transaction.Status.SUCCESS
        )

        total_deductions = 0
        for txn in transactions:
            deduction = txn.amount - txn.credited_amount
            total_deductions += deduction

        txn_data = {
            "txn_id": last_success_txn.txn_id,
            "amount": str(last_success_txn.amount),
            "status": last_success_txn.status,
            "created_at": last_success_txn.created_at.isoformat(),
            "total_transaction": transaction_total,
            "credited_in_wallet": credited_in_wallet
        } if last_success_txn else None
        
        return Response(
            create_response(
                status=True,
                message="Wallet balance retrieved successfully",
                data={
                    "balance": str(wallet.balance),
                    "last_successful_transaction": txn_data,
                    "credited_in_wallet": str(credited_in_wallet),
                    "total_transaction": str(transaction_total),
                    "total_debited": str(total_debited),
                    "total_deductions": str(total_deductions)
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


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Note
from .serializers import NoteSerializer
from custom_auth.models import CustomUser
from core.utils import create_response  # Assuming this is where your helper is defined

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_note(request):
    if request.method == 'GET':
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                create_response(
                    status=False,
                    message="user_id is required",
                    data=None
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = CustomUser.objects.get(pk=user_id)
            note = Note.objects.get(user=user)
            serializer = NoteSerializer(note)
            return Response(
                create_response(
                    status=True,
                    message="Note retrieved successfully",
                    data=serializer.data
                ),
                status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            return Response(
                create_response(
                    status=False,
                    message="User not found",
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Note.DoesNotExist:
            return Response(
                create_response(
                    status=False,
                    message="Note not found",
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )

    elif request.method == 'POST':
        user_id = request.data.get('user_id')
        note_text = request.data.get('note')

        if not user_id or note_text is None:
            return Response(
                create_response(
                    status=False,
                    message="user_id and note are required",
                    data=None
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                create_response(
                    status=False,
                    message="User not found",
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        note_obj, created = Note.objects.get_or_create(user=user)
        note_obj.note = note_text
        note_obj.save()

        serializer = NoteSerializer(note_obj)
        return Response(
            create_response(
                status=True,
                message="Note created" if created else "Note updated",
                data=serializer.data
            ),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


@api_view(['GET'])
# @permission_classes([IsAuthenticated])  # Uncomment if you want auth
def get_pending_txns(request):
    try:
        count = int(request.query_params.get('count', 20))
        page = int(request.query_params.get('page', 1))
    except ValueError:
        return Response(
            create_response(
                status=False,
                message="Invalid 'count' or 'page' parameter",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    queryset = Transaction.objects.filter(status='pending').order_by('-created_at')

    # Assuming you have a utility like this:
    paginated_data = paginate_queryset(request, queryset, TransactionSerializer)

    return Response(
        create_response(
            status=True,
            message="Pending transactions retrieved successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
# @permission_classes([IsAuthenticated])  # Uncomment if you want auth
def get_completed_txns(request):
    try:
        count = int(request.query_params.get('count', 20))
        page = int(request.query_params.get('page', 1))
    except ValueError:
        return Response(
            create_response(
                status=False,
                message="Invalid 'count' or 'page' parameter",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    queryset = Transaction.objects.filter(status='success').order_by('-created_at')

    paginated_data = paginate_queryset(request, queryset, TransactionSerializer)

    return Response(
        create_response(
            status=True,
            message="Successful transactions retrieved successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
# @permission_classes([IsAuthenticated])  # Uncomment if you want auth
def get_failed_txns(request):
    import time
    from django.db import connection

    try:
        count = int(request.query_params.get('count', 20))
        page = int(request.query_params.get('page', 1))
    except ValueError:
        return Response(
            create_response(
                status=False,
                message="Invalid 'count' or 'page' parameter",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    start_total = time.time()

    queryset = Transaction.objects.filter(status='failed').select_related('user').order_by('-created_at')

    db_start = time.time()
    paginated_data = paginate_queryset(request, queryset, TransactionSerializer)
    db_end = time.time()

    total_end = time.time()

    print("========== TRACE ==========")
    print(f"DB Query + Pagination Time: {db_end - db_start:.3f}s")
    print(f"Total View Time:            {total_end - start_total:.3f}s")
    print(f"DB Queries Run:             {len(connection.queries)}")
    print("===========================")

    return Response(
        create_response(
            status=True,
            message="Failed transactions retrieved successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )
