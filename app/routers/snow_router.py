from typing import Annotated
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.schemas.snowintegration import OAuthConfig, RefreshTokenBody, SnowflakeRole
from app.services.snowflake_integration.snowintegration import SnowflakeIntegrationService

router = APIRouter(prefix="/api/snowflake_integration", tags=["Snowflake Integration"])


# Endpoint to initialize OAuth configuration
@router.post("/init_oauth")
def init_oauth(config: OAuthConfig, request: Request, snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]):
    return snow_integration_service.init_oauth_logic(config=config, request=request)


@router.get("/get_oauth")
def get_oauth(
    request: Request,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    
    
    return snow_integration_service.get_oauth_logic(request=request)


@router.put("/update_oauth")
def update_oauth(config: OAuthConfig, request: Request, snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]):
    return snow_integration_service.update_oauth_logic(config=config, request=request)


@router.delete("/delete_oauth")
def delete_oauth(snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]):
    snow_integration_service.delete_oauth_logic()
    return {"message": "Snowflake integration deleted successfully."}


@router.put("/change_role")
def change_role(
    request: SnowflakeRole,
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    return snow_integration_service.change_default_role_logic(new_role_request=request, token=token)


@router.get("/callback")
async def oauth_callback(code: str, request: Request, snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]):
    return await snow_integration_service.oauth_callback_logic(code=code, request=request)


@router.post("/refresh_token")
async def refresh_access_token(
    request_body: RefreshTokenBody, snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    refresh_token = request_body.refresh_token
    return await snow_integration_service.refresh_access_token_logic(refresh_token)


# Endpoint to list data warehouses
@router.get("/data_warehouses")
def list_data_warehouses(snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()], token: str = Header(...)):
    return snow_integration_service.list_data_warehouses_logic(token)


# Modified endpoint to list databases using the selected data warehouse
@router.get("/databases")
def list_databases(token: str = Header(...), snow_integration_service: SnowflakeIntegrationService = Depends()):
    return snow_integration_service.list_databases_logic(token)


# Endpoint to list schemas of a specific database in Snowflake
@router.get("/schemas/{db_name}")
def get_schemas(
    db_name: str,
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    return snow_integration_service.get_schemas_logic(token, db_name)


# Endpoint to select a schema and check separately for the existence of tables and views
@router.get("/select_schema")
def select_schema(
    db_name: str,
    schema_name: str,
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    return snow_integration_service.select_schema_logic(token, db_name, schema_name)


# Endpoint to list tables of a specific schema in a Snowflake database
@router.get("/tables/{db_name}/{schema_name}")
def get_tables(
    db_name: str,
    schema_name: str,
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    return snow_integration_service.get_tables_logic(token, db_name, schema_name)


# Endpoint to list views of a specific schema in a Snowflake database
@router.get("/views/{db_name}/{schema_name}")
def get_views(
    db_name: str,
    schema_name: str,
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    return snow_integration_service.get_views_logic(token, db_name, schema_name)


# Endpoint to list columns of a specific table or view in a Snowflake database, including name and type
@router.get("/columns/{db_name}/{schema_name}/{table_or_view_name}")
def get_columns(
    db_name: str,
    schema_name: str,
    table_or_view_name: str,
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    return snow_integration_service.get_columns_logic(token, db_name, schema_name, table_or_view_name)


@router.get("/preview/{db_name}/{schema_name}/{table_or_view_name}")
def preview_data(
    db_name: str,
    schema_name: str,
    table_or_view_name: str,
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    return {
        "data_preview": snow_integration_service.preview_data_logic(token, db_name, schema_name, table_or_view_name)
    }

@router.get("/available_roles")
def get_available_roles(
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    return snow_integration_service.get_available_roles_logic(token)