from fastapi import FastAPI, APIRouter, Depends
from urllib.parse import urlencode
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from pydantic import BaseModel
from app.schemas.snowintegration import OAuthConfig
from app.services.snowflake_integration.snowintegration import SnowflakeIntegrationService


router = APIRouter()


app = FastAPI()

# Endpoint to initialize OAuth configuration
@router.post("/init_oauth")
def init_oauth(
    config: OAuthConfig, 
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return snow_integration_service.init_oauth_logic(config)

@router.get("/callback")
async def oauth_callback(
    code: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    
    return await snow_integration_service.oauth_callback_logic(code)

# Endpoint to list data warehouses
@router.get("/data_warehouses")
def list_data_warehouses(
    token: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return snow_integration_service.list_data_warehouses_logic(token)

# Endpoint to select a data warehouse # kerakmi?
@router.post("/select_warehouse")
def select_warehouse(
    token: str, 
    warehouse_name: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return snow_integration_service.select_warehouse_logic(token, warehouse_name)

# Modified endpoint to list databases using the selected data warehouse
@router.get("/databases")
def list_databases(
    token: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return snow_integration_service.list_databases_logic(token)


# Endpoint to list schemas of a specific database in Snowflake
@router.get("/schemas/{db_name}")
def get_schemas(
    token: str, 
    db_name: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return {"schemas": snow_integration_service.get_schemas_logic(token, db_name)}

# Endpoint to select a schema and check separately for the existence of tables and views
@router.get("/select_schema")
def select_schema(
    token: str, 
    db_name: str, 
    schema_name: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return snow_integration_service.select_schema_logic(token, db_name, schema_name)


# Endpoint to list tables of a specific schema in a Snowflake database
@router.get("/tables/{db_name}/{schema_name}")
def get_tables(
    token: str, 
    db_name: str,
    schema_name: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return snow_integration_service.get_tables_logic(token, db_name, schema_name)


# Endpoint to list views of a specific schema in a Snowflake database
@router.get("/views/{db_name}/{schema_name}")
def get_views(
    token: str, 
    db_name: str, 
    schema_name: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return snow_integration_service.get_views_logic(token, db_name, schema_name)


# Endpoint to list columns of a specific table or view in a Snowflake database, including name and type
@router.get("/columns/{db_name}/{schema_name}/{table_or_view_name}")
def get_columns(
    token: str, 
    db_name: str, 
    schema_name: str, 
    table_or_view_name: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
     return snow_integration_service.get_columns_logic(token, db_name, schema_name, table_or_view_name)

@router.get("/preview/{db_name}/{schema_name}/{table_or_view_name}")
def preview_data(
    token: str, 
    db_name: str, 
    schema_name: str, 
    table_or_view_name: str,
    snow_integration_service: Annotated[SnowflakeIntegrationService, Depends()]
):
    return {"data_preview": snow_integration_service.preview_data_logic(token, db_name, schema_name, table_or_view_name)}
