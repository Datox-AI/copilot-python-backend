from snowflake.connector import ProgrammingError, OperationalError, InterfaceError
from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlencode
import httpx
import snowflake.connector
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.maindb.snowflake_identifier import SnowflakeIdentifier
from app.backend.session import create_maindb_session
from app.shared.auth.azure_scheme import current_user
from app.schemas.identity.current_user import CurrentUser


app = FastAPI()


REDIRECT_URI = "https://copilot.datox.ai/integration/2" 


class SnowflakeIntegrationService:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],

    ) -> None:
        self.session = session
        self.user = user 

    # Endpoint to initialize OAuth configuration
    def init_oauth_logic(self, config: OAuthConfig):
        authorization_endpoint = config.token_endpoint.replace("token-request", "authorize")
        print(self.user.user_id, " ---- user id")
        snowflake_identfier_obj = SnowflakeIdentifier(
            user_id=self.user.user_id,
            account_identifier=config.account_identifier,
            client_id=config.client_id,
            client_secret=config.client_secret,
            token_endpoint=config.token_endpoint,
            authorization_endpoint=authorization_endpoint,
            warehouse=config.warehouse,
        )
        self.session.add(snowflake_identfier_obj)
        self.session.commit()
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": REDIRECT_URI, 
            "account": config.account_identifier,
        }
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        return {"authorization_url": authorization_url}

    # Callback endpoint for OAuth flow
    async def oauth_callback_logic(self, code: str):
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")
        try:
            token_response = await self.exchange_code_for_token(code)
            if 'access_token' not in token_response:
                raise HTTPException(status_code=400, detail="Access token not in response")
        except Exception as e:
            print(f"Error in exchange_code_for_token: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")
        access_token = token_response['access_token']
        return {"access_token": access_token}


    def _get_snowflake_identifier_obj(self):
        snowflake_identifier_obj = self.session.query(SnowflakeIdentifier).filter(
            SnowflakeIdentifier.user_id == self.user.id
        ).first()
        return snowflake_identifier_obj
    

    # Exchanges an authorization code for an access token
    async def exchange_code_for_token(self, code: str):
        snowflake_identfier_obj = await self._get_snowflake_identifier_obj()
         
        async with httpx.AsyncClient() as client:
            response = await client.post(
                snowflake_identfier_obj.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": snowflake_identfier_obj.client_id,
                    "client_secret": snowflake_identfier_obj.client_secret
                }
            )
            response.raise_for_status()
            return response.json()

    # Creates a connection to Snowflake
    def create_snowflake_connection(self, oauth_token: str, snowflake_account: str):
        try:
            ctx = snowflake.connector.connect(
                account=snowflake_account,
                authenticator='oauth',
                token=oauth_token
            )
            return ctx
        except Exception:
            return False


    # Endpoint to list data warehouses
    def list_data_warehouses_logic(self, token: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        ctx = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
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
        return {"message": f"Data warehouse '{warehouse_name}' selected"}


    # Modified endpoint to list databases using the selected data warehouse
    def list_databases_logic(self, token: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        if not snowflake_identfier_obj.warehouse:
            raise HTTPException(status_code=400, detail="No data warehouse selected")
        conn = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
        cursor = conn.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {snowflake_identfier_obj.warehouse}")
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            return {"databases": [db[1] for db in databases]}
        finally:
            cursor.close()
            conn.close()


    def get_schemas_logic(self, token: str, db_name: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        if not snowflake_identfier_obj.warehouse:
            raise HTTPException(status_code=400, detail="No data warehouse selected")

        ctx = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {snowflake_identfier_obj.warehouse}")
            cursor.execute(f"SHOW SCHEMAS IN DATABASE {db_name}")
            schemas = cursor.fetchall()
            return {"schemas": [schema[1] for schema in schemas]}
        finally:
            cursor.close()
            ctx.close()


    # Endpoint to select a schema and check separately for the existence of tables and views
    def select_schema_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        ctx = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {snowflake_identfier_obj.warehouse}")

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
    def get_tables_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        if not snowflake_identfier_obj.warehouse:
            raise HTTPException(status_code=400, detail="No data warehouse selected")

        ctx = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {snowflake_identfier_obj.warehouse}")
            cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
            tables = cursor.fetchall()
            return {"tables": [table[1] for table in tables]}
        finally:
            cursor.close()
            ctx.close()


    # Endpoint to list views of a specific schema in a Snowflake database

    def get_views_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        if not snowflake_identfier_obj.warehouse:
            raise HTTPException(status_code=400, detail="No data warehouse selected")

        ctx = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {snowflake_identfier_obj.warehouse}")
            cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
            views = cursor.fetchall()
            return {"views": [view[1] for view in views]}
        finally:
            cursor.close()
            ctx.close()

    # Endpoint to list columns of a specific table or view in a Snowflake database, including name and type

    def get_columns_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        if not snowflake_identfier_obj.warehouse:
            raise HTTPException(status_code=400, detail="No data warehouse selected")

        ctx = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {snowflake_identfier_obj.warehouse}")
            cursor.execute(f"DESCRIBE TABLE {db_name}.{schema_name}.{table_or_view_name}")
            columns = cursor.fetchall()
            # Format the columns data to include only name and type. Adjust indices based on Snowflake's response format
            columns_data = [{"name": col[0], "type": col[1]} for col in columns]
            return {"columns": columns_data}
        finally:
            cursor.close()
            ctx.close()

    # Endpoint to preview data from a specific table or view in a Snowflake database
    def preview_data_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        if not snowflake_identfier_obj.warehouse:
            raise HTTPException(status_code=400, detail="No data warehouse selected")

        ctx = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {snowflake_identfier_obj.warehouse}")
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
