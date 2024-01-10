import httpx
import snowflake.connector
from sqlalchemy.orm import Session
from app.models.snowflake_identifier import SnowflakeIdentifier

# Function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Service function to initialize OAuth configuration
def init_oauth_service(config, db: Session):
    # Saving OAuth configuration to the database
    oauth_config = SnowflakeIdentifier(
        user_id=config.user_id,
        account_identifier=config.account_identifier,
        client_id=config.client_id,
        client_secret=config.client_secret,
        token_endpoint=config.token_endpoint
    )
    db.add(oauth_config)
    db.commit()
    db.refresh(oauth_config)
    return oauth_config

# Service function for OAuth callback handling
async def oauth_callback_service(code: str, db: Session):
    # Logic to handle OAuth callback
    # Retrieve saved OAuth configuration from the database
    oauth_config = db.query(SnowflakeIdentifier).first()  # Adjust this to fetch the correct record
    if oauth_config:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                oauth_config.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": oauth_config.redirect_uri,
                    "client_id": oauth_config.client_id,
                    "client_secret": oauth_config.client_secret
                }
            )
            response.raise_for_status()
            token_response = response.json()
            return token_response
    else:
        raise Exception("OAuth configuration not found")