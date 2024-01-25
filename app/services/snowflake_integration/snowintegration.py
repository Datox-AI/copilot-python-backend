from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlencode
import httpx
import snowflake.connector
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

app = FastAPI()


# Pydantic model for OAuth configuration
class OAuthConfig(BaseModel):
    account_identifier: str
    client_id: str
    client_secret: str
    token_endpoint: str
    redirect_uri: str

# Global variables for OAuth and Snowflake details
OAUTH_CLIENT_ID = 'your_oauth_client_id'  # Replace with your OAuth client ID
OAUTH_CLIENT_SECRET = 'your_oauth_client_secret'  # Replace with your OAuth client secret
AUTHORIZATION_ENDPOINT = 'your_authorization_endpoint'  # Replace with your authorization endpoint
TOKEN_ENDPOINT = 'your_token_endpoint'  # Replace with your token endpoint
SNOWFLAKE_ACCOUNT = 'your_snowflake_account'  # Replace with your Snowflake account
REDIRECT_URI = "https://copilot.datox.ai/integration/2"  # Replace with your redirect URI
SELECTED_WAREHOUSE = None  # Variable to store the selected data warehouse

# Constructs the URL for OAuth authorization
def construct_authorization_url():
    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "account": SNOWFLAKE_ACCOUNT
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

# Endpoint to initialize OAuth configuration
def init_oauth_logic(config: OAuthConfig):
    global SNOWFLAKE_ACCOUNT, OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, AUTHORIZATION_ENDPOINT, TOKEN_ENDPOINT, REDIRECT_URI
    SNOWFLAKE_ACCOUNT = config.account_identifier
    OAUTH_CLIENT_ID = config.client_id
    OAUTH_CLIENT_SECRET = config.client_secret
    TOKEN_ENDPOINT = config.token_endpoint
    AUTHORIZATION_ENDPOINT = config.token_endpoint.replace("token-request", "authorize")
    REDIRECT_URI = config.redirect_uri
    authorization_url = construct_authorization_url()
    return {"authorization_url": authorization_url}


# Callback endpoint for OAuth flow

async def oauth_callback_logic(code: str):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    try:
        token_response = await exchange_code_for_token(code)
        if 'access_token' not in token_response:
            raise HTTPException(status_code=400, detail="Access token not in response")
    except Exception as e:
        print(f"Error in exchange_code_for_token: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    access_token = token_response['access_token']
    return {"access_token": access_token}

# Exchanges an authorization code for an access token
async def exchange_code_for_token(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET
            }
        )
        response.raise_for_status()
        return response.json()

# Creates a connection to Snowflake
def create_snowflake_connection(oauth_token: str):
    ctx = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        authenticator='oauth',
        token=oauth_token
    )
    return ctx

# Endpoint to list data warehouses
def list_data_warehouses_logic(token: str):
    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute("SHOW WAREHOUSES")
        warehouses = cursor.fetchall()
        # Assuming the first column contains the warehouse names
        warehouse_names = [wh[0] for wh in warehouses]  # Adjust the index if needed
        return {"data_warehouses": warehouse_names}
    finally:
        cursor.close()
        ctx.close()

# Endpoint to select a data warehouse
def select_warehouse_logic(token: str, warehouse_name: str):
    global SELECTED_WAREHOUSE
    SELECTED_WAREHOUSE = warehouse_name
    return {"message": f"Data warehouse '{warehouse_name}' selected"}

# Modified endpoint to list databases using the selected data warehouse

def list_databases_logic(token: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")
    conn = create_snowflake_connection(token)
    cursor = conn.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        return {"databases": [db[1] for db in databases]}
    finally:
        cursor.close()
        conn.close()



def get_schemas_logic(token: str, db_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute(f"SHOW SCHEMAS IN DATABASE {db_name}")
        schemas = cursor.fetchall()
        return {"schemas": [schema[1] for schema in schemas]}
    finally:
        cursor.close()
        ctx.close()


# Endpoint to select a schema and check separately for the existence of tables and views
def select_schema_logic(token: str, db_name: str, schema_name: str):
    global SELECTED_SCHEMA
    SELECTED_SCHEMA = schema_name

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")

        # Check if there are tables in the schema
        cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
        tables_status = len(cursor.fetchall()) > 0

        # Check if there are views in the schema
        cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
        views_status = len(cursor.fetchall()) > 0

        return {
            "message": f"Schema '{schema_name}' selected",
            "tables": tables_status,
            "views": views_status
        }
    finally:
        cursor.close()
        ctx.close()



# Endpoint to list tables of a specific schema in a Snowflake database

def get_tables_logic(token: str, db_name: str, schema_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
        tables = cursor.fetchall()
        return {"tables": [table[1] for table in tables]}
    finally:
        cursor.close()
        ctx.close()


# Endpoint to list views of a specific schema in a Snowflake database

def get_views_logic(token: str, db_name: str, schema_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
        views = cursor.fetchall()
        return {"views": [view[1] for view in views]}
    finally:
        cursor.close()
        ctx.close()

# Endpoint to list columns of a specific table or view in a Snowflake database, including name and type

def get_columns_logic(token: str, db_name: str, schema_name: str, table_or_view_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute(f"DESCRIBE TABLE {db_name}.{schema_name}.{table_or_view_name}")
        columns = cursor.fetchall()
        # Format the columns data to include only name and type. Adjust indices based on Snowflake's response format
        columns_data = [{"name": col[0], "type": col[1]} for col in columns]
        return {"columns": columns_data}
    finally:
        cursor.close()
        ctx.close()

# Endpoint to preview data from a specific table or view in a Snowflake database

def preview_data_logic(token: str, db_name: str, schema_name: str, table_or_view_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        query = f"SELECT * FROM {db_name}.{schema_name}.{table_or_view_name} LIMIT 10"
        cursor.execute(query)

        # Fetch column names
        column_names = [desc[0] for desc in cursor.description]

        # Fetch data and format rows
        data_preview = []
        for row in cursor.fetchall():
            formatted_row = {col_name: (value if value is not None else "{none}")
                             for col_name, value in zip(column_names, row)}
            data_preview.append(formatted_row)

        return {"data_preview": data_preview}
    finally:
        cursor.close()
        ctx.close()

