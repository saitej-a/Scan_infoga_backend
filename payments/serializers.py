from rest_framework import serializers
from .models import Transaction, WalletBalance

# class TransactionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Transaction
#         # fields = '__all__'
#         fields = ['txn_id', 'amount', 'status', 'created_at', 'comment', 'created_at']
        

class TransactionSerializer(serializers.ModelSerializer):
    payment_group = serializers.SerializerMethodField()
    bank_reference = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'txn_id',
            'amount',
            'status',
            'created_at',
            'comment',
            'payment_group',
            'bank_reference',
            'credited_amount'
        ]

    def get_payment_group(self, obj):
        try:
            return obj.cf_response.get('payment', {}).get('payment_group', None)
        except Exception:
            return None

    def get_bank_reference(self, obj):
        try:
            return obj.cf_response.get('payment', {}).get('bank_reference', None)
        except Exception:
            return None


class WalletBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletBalance
        fields = '__all__'