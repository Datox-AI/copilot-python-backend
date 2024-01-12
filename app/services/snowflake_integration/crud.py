# crud.py

from sqlalchemy.orm import Session
from app.models.maindb.snowflake_identifier import SnowflakeIdentifier
from app.routers.snow_router import OAuthConfig
def create_snowflake_identifier(db: Session, oauth_config: OAuthConfig):
    db_item = SnowflakeIdentifier(
        account_identifier=oauth_config.account_identifier,
        client_id=oauth_config.client_id,
        client_secret=oauth_config.client_secret,
        token_endpoint=oauth_config.token_endpoint
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
