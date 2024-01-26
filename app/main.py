from fastapi import (
    FastAPI,
    FastAPI,
)
import uvicorn
import os
from fastapi_azure_auth.auth import MultiTenantAzureAuthorizationCodeBearer
from app.routers.snow_router import router as snowflake_oauth_router

from .const import (
    OPEN_API_DESCRIPTION,
    OPEN_API_TITLE,
)
from .version import __version__
from app.routers import chats, agent
from app.shared.auth import azure_scheme, AZURE_AD_FRONTEND_CLIENT_ID

from fastapi.middleware.cors import CORSMiddleware
 
 
app = FastAPI(
    title=OPEN_API_TITLE,
    description=OPEN_API_DESCRIPTION,
    version=__version__,
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": AZURE_AD_FRONTEND_CLIENT_ID,
    },
    # dependencies=[Depends(current_user)]
)

# Adding CORS middleware
origins = [
    "http://localhost:3000",
    "http://localhost:3000/",
    "https://localhost:3000",
    "https://localhost:3000/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event('startup')
async def load_config() -> None:
    """
    Load OpenID config on startup.
    """
    await azure_scheme.openid_config.load_config()

app.include_router(chats.router)
app.include_router(agent.router)
app.include_router(snowflake_oauth_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=7202,
        ssl_certfile="./SSL/domain.crt",
        ssl_keyfile="./SSL/domain.key",
    )
