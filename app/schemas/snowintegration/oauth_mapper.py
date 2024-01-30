from app.models.maindb.snowflake_identifier import SnowflakeIdentifier
from app.schemas.snowintegration.oauth_request import OAuthConfig


class SnowflakeOauthMapper:
    @staticmethod
    def map_to_chat_response(snowflake_identifier: SnowflakeIdentifier) -> OAuthConfig:
        return OAuthConfig(
            id=snowflake_identifier.id,
            account_identifier=snowflake_identifier.account_identifier,
            client_id=snowflake_identifier.client_id,
            client_secret=snowflake_identifier.client_secret,
            token_endpoint=snowflake_identifier.token_endpoint,
            warehouse=snowflake_identifier.warehouse,
        )
