from enum import Enum


class AzureTokenErrorMessagesEnum(Enum):
    default = ""
    invalid_token = "Invalid token format"
    guest_user = "Guest users not allowed"
    invalid_claims = "Token contains invalid claims"
    signature_expired = "Azure Token signature has expired"
    unable_to_validate = "Unable to validate token"
    unknown_error = "Unable to process token"


class SnowflakeTokenErrorEnum(Enum):
    invalid = "Snowflake token is invalid"
    expired = "Snowflake token is expired"
    
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))