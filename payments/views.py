from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from core.utils import (
        create_response,
        get_token_from_header,
        get_user_from_token,
        paginate_queryset,
    )
from .models import Transaction, WalletBalance, WalletHistory
from core.permissions import IsAdminUserType
from .serializers import TransactionSerializer, WalletHistorySerializer
from rest_framework import status
from decimal import Decimal

from custom_auth.models import CustomUser
from payments.models import SubscriptionHistory

import time
from django.db import connection


from django.utils import timezone

class TransactionPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allows user to pass ?page_size=...
    max_page_size = 100  # Optional: Limit to prevent very large pages



# Create your views here.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_txn(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    txn_id = request.data.get('txn_id')
    amount = request.data.get('amount')
    if not amount:
        return Response(
            create_response(
                status=False,
                message="Amount is required",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    # check if the amount is a valid number
    if not str(amount).isdigit():
        return Response(
            create_response(
                status=False,
                message="Amount is not a valid number",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    if not txn_id:
        return Response(
            create_response(
                status=False,
                message="Transaction ID is required",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user:
        return Response(
            create_response(
                status=False,
                message="User not found",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

        # Check if a pending transaction already exists
    if Transaction.objects.filter(user=user, status=Transaction.Status.PENDING).exists():
        return Response(
            create_response(False, "A pending transaction already exists", None),
            status=status.HTTP_409_CONFLICT
        )

    Transaction.objects.create(
        user=user,
        txn_id=txn_id,
        amount=amount,
        comment="Bank Transfer"
    )

    return Response(
        create_response(
            status=True,
            message="Transaction ID saved successfully",
            data=None
        ),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_txns(request):
    count = request.query_params.get('count', 20)
    page = request.query_params.get('page', 1)
    
    try:
        count = int(count)
        page = int(page)
    except ValueError:
        return Response(
            create_response(
                status=False,
                message="Invalid count or page number",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    start = (page - 1) * count
    end = start + count
    
    txns = Transaction.objects.filter(status='pending')[start:end]
    total_count = Transaction.objects.filter(status='pending').count()
    
    serialized_txns = TransactionSerializer(txns, many=True)
    return Response(
        create_response(
            status=True,
            message="Pending transactions retrieved successfully",
            data={
                'transactions': serialized_txns.data,
                'total_count': total_count,
                'page': page,
                'count': count
            }
        ),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_completed_txns(request):
    count = request.query_params.get('count', 20)
    page = request.query_params.get('page', 1)
    
    try:
        count = int(count)
        page = int(page)
    except ValueError:
        return Response(
            create_response(
                status=False,
                message="Invalid count or page number",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    start = (page - 1) * count
    end = start + count
    
    txns = Transaction.objects.filter(status='success')[start:end]
    total_count = Transaction.objects.filter(status='success').count()
    
    serialized_txns = TransactionSerializer(txns, many=True)
    return Response(
        create_response(
            status=True,
            message="Successful transactions retrieved successfully",
            data={
                'transactions': serialized_txns.data,
                'total_count': total_count,
                'page': page,
                'count': count
            }
        ),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_failed_txns(request):
    start_total = time.time()
    count = int(request.query_params.get('count', 20))
    page = int(request.query_params.get('page', 1))

    start = (page - 1) * count
    end = start + count

    db_start = time.time()
    txns = Transaction.objects.filter(status='failed') \
        .select_related('user') \
        .order_by('-created_at')[start:end]
    total_count = Transaction.objects.filter(status='failed').count()
    db_end = time.time()

    serializer_start = time.time()
    serialized_txns = TransactionSerializer(txns, many=True)
    serializer_end = time.time()

    total_end = time.time()

    print("========== TRACE ==========")
    print(f"DB Query Time:        {db_end - db_start:.3f}s")
    print(f"Serialization Time:   {serializer_end - serializer_start:.3f}s")
    print(f"Total View Time:      {total_end - start_total:.3f}s")
    print(f"DB Queries Run:       {len(connection.queries)}")
    print("===========================")

    return Response(create_response(
        status=True,
        message="Success",
        data={
            'transactions': serialized_txns.data,
            'total_count': total_count,
            'page': page,
            'count': count
        }
    ))

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_all_txns(request):
#     token = get_token_from_header(request)
#     user = get_user_from_token(token)
#     if(user.user_type != 'admin'):
#         txns = Transaction.objects.filter(user=user)
#     else:
#         txns = Transaction.objects.all()
    
#     serialized_txns = TransactionSerializer(txns, many=True)
#     return Response(
#         create_response(
#             status=True,
#             message="All transactions retrieved successfully",
#             data=serialized_txns.data
#         ),
#         status=status.HTTP_200_OK
#     )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_txns(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)

    if user.user_type != 'admin':
        queryset = Transaction.objects.filter(user=user).order_by('-created_at')
    else:
        queryset = Transaction.objects.all().order_by('-created_at')

    paginated_data = paginate_queryset(request, queryset, TransactionSerializer)

    return Response(
        create_response(
            status=True,
            message="Transactions retrieved successfully",
            data=paginated_data
        ),
        status=status.HTTP_200_OK
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_txn_status_to_success(request):
    txn_id = request.data.get('txn_id')
    amount = request.data.get('amount')
    if not amount:
        return Response(
            create_response(
                status=False,
                message="Amount is required",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    if not txn_id:
        return Response(
            create_response(
                status=False,
                message="Transaction ID is required",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    txn = Transaction.objects.get(txn_id=txn_id)

    txn.status = 'success'
    txn.amount = amount
    txn.credited_amount = Decimal(amount)*Decimal("0.82")
    txn.updated_at = timezone.now()
    txn.save()

    user = txn.user

    # Determine the new subscription plan based on amount
    if 59000 <= amount < 236000:
        if user.subscription_plan == CustomUser.SubscriptionPlans.FREE:
            user.subscription_plan = CustomUser.SubscriptionPlans.SILVER
            user.subscription_date = timezone.now()

            # Create a subscription history entry
            SubscriptionHistory.objects.create(
                user=user,
                subscription_plan=CustomUser.SubscriptionPlans.SILVER,
                txn_id=txn
            )

            user.save()

    elif 236000 <= amount < 1180000:
        if user.subscription_plan in [CustomUser.SubscriptionPlans.FREE, CustomUser.SubscriptionPlans.SILVER]:
            user.subscription_plan = CustomUser.SubscriptionPlans.GOLD
            user.subscription_date = timezone.now()

            SubscriptionHistory.objects.create(
                user=user,
                subscription_plan=CustomUser.SubscriptionPlans.GOLD,
                txn_id=txn
            )
            user.save()

    elif amount >= 1180000:
        if user.subscription_plan != CustomUser.SubscriptionPlans.PLATINUM:
            user.subscription_plan = CustomUser.SubscriptionPlans.PLATINUM
            user.subscription_date = timezone.now()

            SubscriptionHistory.objects.create(
                user=user,
                subscription_plan=CustomUser.SubscriptionPlans.PLATINUM,
                txn_id=txn
            )
            user.save()


    # update the wallet balance for the user
    wallet = WalletBalance.objects.get(user=txn.user)
    wallet.balance += Decimal(txn.amount)*Decimal("0.82")
    wallet.save()

    WalletHistory.objects.create(
            user=user,
            wallet=wallet,
            txn_type=WalletHistory.TransactionType.CREDIT,
            amount=Decimal(txn.amount)*Decimal("0.82"),
            balance_after=wallet.balance,
            comment="Manual Credit",
            transaction=txn
        )

    return Response(
        create_response(
            status=True,
            message="Transaction status updated successfully",
            data=None
        ),
        status=status.HTTP_200_OK
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_txn_status_to_failed(request):
    txn_id = request.data.get('txn_id')
    amount = request.data.get('amount')
    comment = request.data.get('comment', "")
    if not amount:
        return Response(
            create_response(
                status=False,
                message="Amount is required",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    if not txn_id:
        return Response(
            create_response(
                status=False,
                message="Transaction ID is required",
                data=None
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    txn = Transaction.objects.get(txn_id=txn_id)
    txn.status = 'failed'
    txn.comment = comment
    txn.amount = amount
    txn.updated_at = timezone.now()
    txn.save()
    return Response(
        create_response(
            status=True,
            message="Transaction status updated successfully",
            data=None
        ),
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_balance(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    
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
def is_txn_pending(request):
    token = get_token_from_header(request)
    user = get_user_from_token(token)
    is_pending = Transaction.objects.filter(user=user, status=Transaction.Status.PENDING).exists()

    return Response(
        create_response(
            status=True,
            message="Pending txn api call succesful",
            data={"isPendingTxn": is_pending}
        ),
        status=status.HTTP_200_OK
    )


import os
import uuid
import json
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta
from cashfree_pg.api_client import Cashfree

from .models import Transaction, WalletBalance

# Setup SDK
Cashfree.XClientId = settings.CASHFREE_CLIENT_ID
Cashfree.XClientSecret = settings.CASHFREE_CLIENT_SECRET
Cashfree.XEnvironment = Cashfree.PRODUCTION  # or Cashfree.PRODUCTION
x_api_version = "2023-08-01"  # Cashfree’s latest API version

from django.core.cache import cache

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    amount = request.data.get('amount')
    user = request.user

    if not user.phone:
        return Response(create_response(False, 'Phone number is required. Please update the number from profile.', None), status=status.HTTP_400_BAD_REQUEST)

    order_id = str(uuid.uuid4())

    print(f"[INITIATE PAYMENT] Initiating payment for User ID: {user.id}, Amount: {amount}, Order ID: {order_id}")

    # Cache the payment details instead of saving in DB
    cache_key = f'payment_{order_id}'
    cache_data = {
        'user_id': user.id,
        'amount': amount,
        'status': 'PENDING'
    }
    cache.set(cache_key, cache_data, timeout=15 * 60)  # Cache for 15 minutes

    print(f"[INITIATE PAYMENT] Payment data cached with key: {cache_key}")

    cf = Cashfree()



    customer = CustomerDetails(
        customer_id=f"user_{user.id}",
        customer_email=user.email,
        customer_phone= user.phone
    )

    order_meta = OrderMeta(
        return_url=f"https://dev.scaninfoga.com/payment-success?order_id={order_id}",
        notify_url="https://backend.scaninfoga.com/api/payments/cashfree-webhook"
    )

    request_obj = CreateOrderRequest(
        order_id=order_id,
        order_amount=float(amount),
        order_currency="INR",
        customer_details=customer,
        order_meta=order_meta
    )

    print(f"[INITIATE PAYMENT] Sending request to Cashfree with Order ID: {order_id}")

    response = cf.PGCreateOrder(x_api_version, request_obj)

    print(f"[CASHFREE RESPONSE] Status Code: {response.status_code}")
    print(f"[CASHFREE RESPONSE] Response Data: {response.data.__dict__}")

    if response.status_code == 200 and response.data.payment_session_id:
        print(f"[PAYMENT SESSION] Payment session created: {response.data.payment_session_id}")
        return Response(create_response(True, 'Payment session created', {'paymentSessionId': response.data.payment_session_id, 'orderId': order_id}))
        # return Response({'paymentSessionId': response.data.payment_session_id, 'orderId': order_id})
    else:
        print("[ERROR] Payment initiation failed.")
        return Response(create_response(False, 'Payment initiation failed', None), status=400)


@csrf_exempt
@require_POST
def cashfree_webhook(request):
    print("[WEBHOOK] Webhook triggered.")
    data = json.loads(request.body)
    print(f"[WEBHOOK DATA] {data}")

    order_id = data.get('data', {}).get('order', {}).get('order_id')
    payment_status = data.get('data', {}).get('payment', {}).get('payment_status')
    payment_id = data.get('data', {}).get('payment', {}).get('cf_payment_id')

    payment_mode_data = data.get('data', {}).get('payment', {}).get('payment_method', {})
    if 'upi' in payment_mode_data:
        payment_mode = 'UPI'
    else:
        payment_mode = Transaction.PaymentMode.UNKNOWN

    print(f"[WEBHOOK] Processing Order ID: {order_id}, Status: {payment_status}, Payment ID: {payment_id}")

    cache_key = f'payment_{order_id}'
    cached_data = cache.get(cache_key)

    if not cached_data:
        print("[ERROR] Payment details not found in cache.")
        return JsonResponse({'error': 'Payment details not found.'}, status=404)

    try:
        user_id = cached_data['user_id']
        amount = cached_data['amount']
        user = CustomUser.objects.get(id=user_id)

        if payment_status == 'SUCCESS':
            txn_status = Transaction.Status.SUCCESS
        else:
            txn_status = Transaction.Status.FAILED

        transaction = Transaction.objects.create(
            txn_id=order_id,
            amount=amount,
            user=user,
            status=txn_status,
            comment="Wallet Top-Up",
            cf_response = data.get('data', {}),
            credited_amount = Decimal(amount)*Decimal('0.8')
        )

        print(f"[WEBHOOK] Transaction created: {transaction.txn_id} with status: {transaction.status}")

        if txn_status == Transaction.Status.SUCCESS:
            print("TXN SUCCESS")
            wallet, created = WalletBalance.objects.get_or_create(user=user)
            credited_amount = Decimal(transaction.amount)*Decimal('0.8')
            wallet.balance += credited_amount
            wallet.save()
            print("SAVED")

            print(f"[WEBHOOK] Wallet updated. Amount credited: {credited_amount}")
        else:
            print("[WEBHOOK] Payment failed. Transaction recorded.")

        # Clean up the cache
        cache.delete(cache_key)
        WalletHistory.objects.create(
            user=user,
            wallet=wallet,
            txn_type=WalletHistory.TransactionType.CREDIT,
            amount=credited_amount,
            balance_after=wallet.balance,
            comment="Wallet Top-Up",
            transaction=transaction
        )
        return JsonResponse({'status': 'success'})

    except CustomUser.DoesNotExist:
        print("[ERROR] User not found for cached payment.")
        return Response(create_response(False, 'User not found', None), status=404)
        # return JsonResponse({'error': 'User not found.'}, status=404)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    order_id = request.GET.get('order_id')
    print(f"[VERIFY PAYMENT] Verifying payment for Order ID: {order_id}")

    try:
        txn = Transaction.objects.get(txn_id=order_id)
        print(f"[VERIFY PAYMENT] Transaction found. Status: {txn.status}")

        return Response({
            'status': txn.status,
            'payment_mode': txn.cf_response['payment']['payment_group'],
            'cashfree_payment_id': txn.txn_id
        })
    except Transaction.DoesNotExist:
        print("[VERIFY PAYMENT] Transaction not found.")
        return Response(create_response(False, 'Payment not found', None), status=404)

        