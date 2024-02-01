from app.schemas.snowintegration.oauth_response import SnowflakeIdentifierResponse
from app.models.maindb.snowflake_identifier import SnowflakeIdentifier, SnowflakeWarehouse


class SnowflakeOauthMapper:
    @staticmethod
    def map_to_oauth_response(
        snowflake_identifier: SnowflakeIdentifier,
        warehouse_obj: SnowflakeWarehouse,
        authorization_url: str
    ) -> SnowflakeIdentifierResponse:

        return SnowflakeIdentifierResponse(
            id=snowflake_identifier.id,
            account_identifier=snowflake_identifier.account_identifier,
            client_id=snowflake_identifier.client_id,
            client_secret=snowflake_identifier.client_secret,
            token_endpoint=snowflake_identifier.token_endpoint,
            warehouse=warehouse_obj.name,
            authorization_url=authorization_url
        )