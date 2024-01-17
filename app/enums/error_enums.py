from enum import Enum


class AzureTokenErrorMessagesEnum(Enum):
    default = ""
    invalid_token = "Invalid token format"
    guest_user = "Guest users not allowed"
    invalid_claims = "Token contains invalid claims"
    signature_expired = "Token signature has expired"
    unable_to_validate = "Unable to validate token"
    unknown_error = "Unable to process token"
