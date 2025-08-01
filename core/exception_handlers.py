from enum import Enum

class ErrorMessages(Enum):
    INSUFFICIENT_BALANCE = "Insufficient balance"

class InsufficientBalanceError(Exception):
    def __init__(self, message=ErrorMessages.INSUFFICIENT_BALANCE.value):
        super().__init__(message)

class UserNotFoundException(Exception):
    def __init__(self, message="User not found"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message

class InvalidCredentialsException(Exception):
    def __init__(self, message="Invalid Credentials"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message

class InvalidUserTypeException(Exception):
    def __init__(self, message="Invalid User Type"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class MissingRequiredFieldsException(Exception):
    def __init__(self, message="Required fields missing"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message

class InactiveAccountException(Exception):
    def __init__(self, message="Account is inactive."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message

class DataNotFoundException(Exception):
    def __init__(self, message="No data found"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message
