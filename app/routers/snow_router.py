from typing import Annotated
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
import base64
from fastapi import APIRouter, Query, Header, Depends, HTTPException
from fastapi import APIRouter, Query, Header, Depends, HTTPException
from typing import List, Dict


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

@router.get("/preview_data")
def preview_data(
    db_name: str,
    schema_name: str,
    table_or_view_name: str,
    chart_type: str = Query("bar", enum=["bar", "line", "scatter", "scorecard", "heatmap"]),
    token: str = Header(...),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    """
    Endpoint to preview data from a specific table or view in a Snowflake database and generate a chart.
    Specify the type of chart to generate (bar, line, scatter, scorecard, heatmap).
    """
    try:
        return snow_integration_service.preview_data_logic(token, db_name, schema_name, table_or_view_name, chart_type)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/decode_base64_to_image", responses={200: {"content": {"image/png": {}}}})
async def decode_base64_to_image(base64_str: str):
    try:
        # Decode the base64 string to get the image bytes
        image_bytes = base64.b64decode(base64_str)
        # Create a BytesIO buffer from the image bytes
        image_stream = BytesIO(image_bytes)
        image_stream.seek(0)
        # Return the image stream as a response
        return StreamingResponse(image_stream, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode base64 string: {str(e)}")




# Defining the allowed chart types and aggregation functions directly
allowed_chart_types = ["bar", "line", "scatter", "scorecard", "heatmap"]
allowed_aggregations = ["SUM", "AVG", "MIN", "MAX", "COUNT", "MEDIAN", "MODE"]

@router.get("/custom_chart", response_model=dict)
def custom_chart(
    db_name: str,
    schema_name: str,
    table_or_view_name: str,
    x_column: str,
    y_columns: List[str] = Query(..., description="Comma-separated list of columns for the y-axis"),
    aggregations: List[str] = Query(..., description="Comma-separated list of aggregation functions corresponding to y-columns", enum=allowed_aggregations),
    chart_type: str = Query("line", enum=allowed_chart_types, description="The type of chart to generate"),
    token: str = Header(..., description="Authentication token"),
    snow_integration_service: SnowflakeIntegrationService = Depends()
):
    """
    Endpoint to fetch aggregated data from a specific table or view in a Snowflake database.
    Allows users to specify the columns for the x-axis and y-axis, along with the type of aggregation for each y-axis column.
    """
    if len(y_columns) != len(aggregations):
        raise HTTPException(status_code=400, detail="The number of y_columns must match the number of aggregations provided.")

    # Combine y_columns with their corresponding aggregation functions
    y_columns_with_aggregations = [{"name": col, "aggregation": agg} for col, agg in zip(y_columns, aggregations)]

    try:
        data = snow_integration_service.generate_custom_chart_logic(
            token, db_name, schema_name, table_or_view_name, x_column, y_columns_with_aggregations, chart_type
        )
        return {"data": data}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))