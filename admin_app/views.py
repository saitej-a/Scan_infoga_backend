from django.shortcuts import render
from payments.models import WalletHistory
from payments.serializers import WalletHistorySerializer
from core.utils import create_response, paginate_queryset
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from custom_auth.models import CustomUser

# Create your views here.

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
