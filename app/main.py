from fastapi import (
    FastAPI,
    FastAPI,
)
import uvicorn
from dotenv import load_dotenv

from .const import (
    OPEN_API_DESCRIPTION,
    OPEN_API_TITLE,
)
from .version import __version__
from app.routers import chats, agent
from app.shared.auth import azure_scheme, AZURE_AD_FRONTEND_CLIENT_ID, current_user

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


@app.on_event("startup")
async def load_config() -> None:
    """
    Load OpenID config on startup.
    """
    await azure_scheme.openid_config.load_config()


app.include_router(chats.router)
app.include_router(agent.router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=7202,
        ssl_certfile="./SSL/fullchain.pem",
        ssl_keyfile="./SSL/localhost.key",
    )
