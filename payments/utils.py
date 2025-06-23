from .models import WalletBalance, ApiPricing
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

def create_wallet(user):
    return WalletBalance.objects.create(user=user)
    

def get_amount_after_api_call(user, api_name):
    try:
        wallet = WalletBalance.objects.get(user=user)
        api_pricing = ApiPricing.objects.get(api_name=api_name)
    except WalletBalance.DoesNotExist:
        raise ValidationError("Wallet not found for user.")
    except ApiPricing.DoesNotExist:
        raise ValidationError(f"Pricing not found for API '{api_name}'.")

    balance = wallet.balance
    price = api_pricing.price

    if balance < price:
        raise ValidationError("Insufficient balance.")

    return balance - price  # returns Decimal

def update_user_balance(user, amount: Decimal):
    if amount < 0:
        raise ValidationError("Balance cannot be negative.")

    with transaction.atomic():
        wallet = WalletBalance.objects.select_for_update().get(user=user)
        wallet.balance = amount
        wallet.save()

