from enum import Enum

class ErrorMessages(Enum):
    INSUFFICIENT_BALANCE = "Insufficient balance"

class InsufficientBalanceError(Exception):
    def __init__(self, message=ErrorMessages.INSUFFICIENT_BALANCE.value):
        super().__init__(message)
