import uuid
from typing import Annotated
from urllib.parse import urlencode
import httpx, ast
import snowflake.connector
from fastapi import Depends, FastAPI, HTTPException
from httpx import ConnectTimeout, HTTPStatusError, NetworkError, ReadTimeout
from snowflake.connector.errors import DatabaseError, ForbiddenError
from sqlalchemy.orm import Session
from app.backend.session import create_maindb_session
from app.models.maindb.snowflake_identifier import SnowflakeIdentifier, SnowflakeWarehouse
from app.schemas.identity.current_user import CurrentUser
from app.schemas.snowintegration import OAuthConfig, SnowflakeOauthMapper, SnowflakeRole
from app.shared.auth.azure_scheme import current_user
import requests
import logging
from fastapi import Header
import matplotlib.pyplot as plt
import io
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
import snowflake.connector
import base64
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
import snowflake.connector
from io import BytesIO
from typing import List, Dict

# Configure logging at the start of your script/application
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()


REDIRECT_URI = "https://ashy-wave-0c6d0ea0f-dev.eastus2.4.azurestaticapps.net/callback/snowflake"


def is_url_reachable(url: str) -> bool:
    try:
        response = requests.get(url, timeout=5)  # Timeout set to 5 seconds
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        # Handles exceptions like connection errors or timeouts
        print(f"Error checking URL: {e}")
        return False


class SnowflakeIntegrationService:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ) -> None:
        self.session = session
        self.user = user

    def handle_common_errors(self, exception):
        if isinstance(exception, HTTPStatusError):
            # logging.error(f"HTTP status error occurred: {exception}")
            raise HTTPException(status_code=500, detail="HTTP status error occurred")
        elif isinstance(exception, NetworkError):
            # logging.error(f"Network error occurred: {exception}")
            raise HTTPException(status_code=500, detail="Network error occurred")
        elif isinstance(exception, (ConnectTimeout, ReadTimeout)):
            # logging.error(f"Timeout error occurred: {exception}")
            raise HTTPException(status_code=500, detail="Timeout error occurred")
        else:  # General exception
            print(exception)
            # logging.error(f"Unexpected error: {exception}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")

    def _get_snowflake_identifier_obj(self):
        existing_snowflake_identifier_obj = (
            self.session.query(SnowflakeIdentifier).filter(SnowflakeIdentifier.user_id == self.user.user_id).first()
        )
        if not existing_snowflake_identifier_obj:
            raise HTTPException(status_code=404, detail="User does not have snowflake identifier object")

        if existing_snowflake_identifier_obj:
            selected_warehouse_obj = (
                self.session.query(SnowflakeWarehouse)
                .filter(
                    SnowflakeWarehouse.identifier == existing_snowflake_identifier_obj,
                    SnowflakeWarehouse.selected == True,
                )
                .first()
            )
        else:
            selected_warehouse_obj = None
        return existing_snowflake_identifier_obj, selected_warehouse_obj

    def _select_or_create_warehouse_obj(self, snowflake_identifier_obj: SnowflakeIdentifier, warehouse_name: str):
        warehouse_objs_query = self.session.query(SnowflakeWarehouse).filter(
            SnowflakeWarehouse.identifier == snowflake_identifier_obj
        )

        if len(warehouse_objs_query.all()) != 0:
            print(len(warehouse_objs_query.all()))
            warehouse_obj_with_name = warehouse_objs_query.filter(SnowflakeWarehouse.name == warehouse_name).first()
        else:
            warehouse_obj_with_name = None

        if warehouse_obj_with_name is None:
            # creating new warehouse
            warehouse_obj_with_name = SnowflakeWarehouse(
                name=warehouse_name, identifier=snowflake_identifier_obj, selected=True
            )
            self.session.add(warehouse_obj_with_name)
        else:
            warehouse_obj_with_name.selected = True

        for warehouse_obj in warehouse_objs_query.all():
            if warehouse_obj != warehouse_obj_with_name:
                warehouse_obj.selected = False

        self.session.commit()

    # Endpoint to initialize OAuth configuration
    def init_oauth_logic(self, config: OAuthConfig):
        if len(config.client_id) != 28:
            raise HTTPException(status_code=400, detail="Please review Client ID for typos")
        if len(config.client_secret) != 44:
            raise HTTPException(status_code=400, detail="Please review Client Secret for typos")
        authorization_endpoint = config.token_endpoint.replace("token-request", "authorize")
        # Perform the verification asynchronously
        existing_snowflake_identifier_obj = (
            self.session.query(SnowflakeIdentifier).filter(SnowflakeIdentifier.user_id == self.user.user_id).first()
        )
        if existing_snowflake_identifier_obj:
            raise HTTPException(status_code=400, detail="User has already snowflake identifier object")
         

        config.account_identifier = config.account_identifier.replace(".", "-")
        snowflake_identifier_obj = SnowflakeIdentifier(
            id=uuid.uuid4(),
            user_id=self.user.user_id,
            account_identifier=config.account_identifier,
            client_id=config.client_id,
            client_secret=config.client_secret,
            token_endpoint=config.token_endpoint,
            authorization_endpoint=authorization_endpoint,
        )
        warehouse_obj = SnowflakeWarehouse(
            id=uuid.uuid4(), name=config.warehouse, identifier=snowflake_identifier_obj, selected=True
        )

        self.session.add(snowflake_identifier_obj)
        self.session.add(warehouse_obj)
        self.session.commit()
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": REDIRECT_URI,
        }
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        if is_url_reachable(authorization_url):
            return {"authorization_url": authorization_url}
        else:
            raise HTTPException(status_code=400, detail="Authorization URL is not reachable")

    def get_oauth_logic(self):
        existing_snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        authorization_endpoint = existing_snowflake_identifier_obj.token_endpoint.replace("token-request", "authorize")
        params = {
            "response_type": "code",
            "client_id": existing_snowflake_identifier_obj.client_id,
            "redirect_uri": REDIRECT_URI,
        }
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        return SnowflakeOauthMapper.map_to_oauth_response(
            snowflake_identifier=existing_snowflake_identifier_obj,
            warehouse_obj=selected_warehouse_obj,
            authorization_url=authorization_url,
        )

    def update_oauth_logic(self, config: OAuthConfig):

        config.account_identifier = config.account_identifier.replace(".", "-")
        
        if len(config.client_id) != 28:
            raise HTTPException(status_code=400, detail="Please review Client ID for typos")
        if len(config.client_secret) != 44:
            raise HTTPException(status_code=400, detail="Please review Client Secret for typos")

        existing_snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]

        authorization_endpoint = config.token_endpoint.replace("token-request", "authorize")

        existing_snowflake_identifier_obj.account_identifier = config.account_identifier
        existing_snowflake_identifier_obj.client_id = config.client_id
        existing_snowflake_identifier_obj.client_secret = config.client_secret
        existing_snowflake_identifier_obj.token_endpoint = config.token_endpoint
        existing_snowflake_identifier_obj.authorization_endpoint = authorization_endpoint
        # updating warehouses
        self._select_or_create_warehouse_obj(
            snowflake_identifier_obj=existing_snowflake_identifier_obj, warehouse_name=config.warehouse
        )
        self.session.commit()
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": REDIRECT_URI,
        }
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        # Check if the authorization URL is reachable
        if is_url_reachable(authorization_url):
            return {"authorization_url": authorization_url}
        else:
            raise HTTPException(
                status_code=500, detail="Please review the entered token endpoint for any typographical errors"
            )

    def delete_oauth_logic(self):
        existing_snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]
        self.session.delete(existing_snowflake_identifier_obj)
        self.session.commit()

    async def oauth_callback_logic(self, code: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")

        token_response = await self.exchange_code_for_token(code)
        # saving user role to DB
        if not snowflake_identifier_obj.user_role:
            scope = token_response["scope"]
            user_role = scope.split(":")[-1]
            snowflake_identifier_obj.user_role = user_role
            self.session.commit()

        try:
            if "access_token" not in token_response:
                raise HTTPException(status_code=400, detail="Access token not in response")
            return token_response
        except Exception as e:
            self.handle_common_errors(e)

    # Exchanges an authorization code for an access token
    async def exchange_code_for_token(self, code: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    snowflake_identifier_obj.token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": REDIRECT_URI,
                        "client_id": snowflake_identifier_obj.client_id,
                        "client_secret": snowflake_identifier_obj.client_secret,
                    },
                )

            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=400, detail="Please review the entered client secret for any typographical errors"
            )

    # Refresh access token logic
    async def refresh_access_token_logic(self, refresh_token: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    snowflake_identifier_obj.token_endpoint,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": snowflake_identifier_obj.client_id,
                        "client_secret": snowflake_identifier_obj.client_secret,
                    },
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(e)
            raise HTTPException(status_code=400, detail="Invalid refresh token")

    # Creates a connection to Snowflake
    def create_snowflake_connection(self, oauth_token: str, snowflake_account: str):
        print(snowflake_account, "  account sn")
        try:
            ctx = snowflake.connector.connect(account=snowflake_account, authenticator="oauth", token=oauth_token)
            return ctx
        except DatabaseError as e:
            error_message = e.raw_msg
            if "OAuth access token expired" in error_message:
                raise HTTPException(status_code=401, detail="Snowflake token expired")
            elif "Invalid OAuth access token" in error_message:
                print(oauth_token, " token")
                raise HTTPException(status_code=400, detail="Invalid snowflake token")
            else:
                raise HTTPException(status_code=500, detail=f"Snowflake connection failed: {e}")
        except ForbiddenError as e:
            raise HTTPException(status_code=400, detail=f"Snowflake account is not correct: {snowflake_account}")

    def _create_warehouse(self, warehouse_name):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        warehouse_obj = SnowflakeWarehouse(name=warehouse_name, identifier=snowflake_identifier_obj, selected=True)
        # unselecting
        selected_warehouse_obj.selected = False
        self.session.add(warehouse_obj)
        self.session.commit()

    # Endpoint to list data warehouses
    def list_data_warehouses_logic(self, token: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        if ctx is None:
            # Handle the error appropriately
            raise ConnectionError("Failed to establish a connection to Snowflake.")
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

    # Endpoint to list databases
    def list_databases_logic(self, token: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            try:
                cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            except Exception as e:
                if "Object does not exist" in str(e):
                    raise HTTPException(
                        status_code=404,
                        detail="The specified warehouse does not exist. Please select a new data warehouse.",
                    )
                else:
                    raise HTTPException(
                        status_code=500, detail="An unexpected error occurred while accessing the database."
                    )

            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            return {"databases": [db[1] for db in databases]}
        finally:
            cursor.close()
            ctx.close()

    def get_schemas_logic(self, token: str, db_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute(f"SHOW SCHEMAS IN DATABASE {db_name}")
            schemas = cursor.fetchall()
            return {"schemas": [schema[1] for schema in schemas]}
        except HTTPException as e:
        # Re-raise the exception if it's already an HTTPException
            raise e
        except Exception as e:
            self.handle_common_errors(e)
        finally:
            cursor.close()
            ctx.close()

        # Endpoint to select a schema and check separately for the existence of tables and views
    def select_schema_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
            tables_status = len(cursor.fetchall()) > 0

            cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
            views_status = len(cursor.fetchall()) > 0

            return {"message": f"Schema '{schema_name}' selected", "tables": tables_status, "views": views_status}

        except HTTPException as e:
            # Re-raise the exception if it's already an HTTPException
            raise e
        except Exception as e:
            self.handle_common_errors(e)
        finally:
            cursor.close()
            ctx.close()


    # Endpoint to list tables of a specific schema in a Snowflake database
    def get_tables_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
            tables = cursor.fetchall()
            return {"tables": [table[1] for table in tables]}
        except HTTPException as e:
            # Re-raise the exception if it's already an HTTPException
            raise e
        except Exception as e:
            self.handle_common_errors(e)
        finally:
            cursor.close()
            ctx.close()


    # Endpoint to change the user role in snowflake
    def change_default_role_logic(self, new_role_request: SnowflakeRole, token: str):
        new_role = new_role_request.role
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()
            # Get the current user's username
            cursor.execute("SELECT CURRENT_USER();")
            current_username = cursor.fetchone()[0]

            # Changing the default role for the current user in Snowflake
            try:
                cursor.execute(f"ALTER USER {current_username} SET DEFAULT_ROLE = '{new_role}'")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to change default role: {e}")
            # changing it in the DB
            snowflake_identifier_obj.user_role = new_role
            self.session.commit()

            return {"detail": f"Default role for user '{current_username}' changed to '{new_role}' successfully"}
        except Exception as e:
            error_message = str(e).lower()
            if 'role does not exist' in error_message:
                detail_msg = f"The role '{new_role}' does not exist."
                raise HTTPException(status_code=400, detail=detail_msg)
            elif 'insufficient privilege' in error_message:
                detail_msg = "Insufficient privileges to change the role."
                raise HTTPException(status_code=403, detail=detail_msg)
            elif 'default role' in error_message:
                detail_msg = f"Failed to change default role due to a configuration or permission issue."
                raise HTTPException(status_code=400, detail=detail_msg)
            else:
                # General fallback for unhandled errors
                raise HTTPException(status_code=500, detail=f"Internal Server Error: {error_message}")
        finally:
            cursor.close()
            conn.close()



    def get_views_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
            views = cursor.fetchall()
            return {"views": [view[1] for view in views]}
        except HTTPException as e:
            # Re-raise the exception if it's already an HTTPException
            raise e
        except Exception as e:
            error_message = str(e).lower()
            if 'insufficient privilege' in error_message:
                detail_msg = "Insufficient privileges to access views."
                raise HTTPException(status_code=403, detail=detail_msg)
            else:
                # General fallback for unhandled errors
                raise HTTPException(status_code=500, detail=f"Internal Server Error: {error_message}")
        finally:
            cursor.close()
            ctx.close()


    # Endpoint to list columns of a specific table or view in a Snowflake database, including name and type

    def get_columns_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute(f"DESCRIBE TABLE {db_name}.{schema_name}.{table_or_view_name}")
            columns = cursor.fetchall()
            # Format the columns data to include only name and type. Adjust indices based on Snowflake's response format
            columns_data = [{"name": col[0], "type": col[1]} for col in columns]
            return {"columns": columns_data}
        except HTTPException as e:
            # Re-raise the exception if it's already an HTTPException
            raise e
        except Exception as e:
            self.handle_common_errors(e)
        finally:
            cursor.close()
            ctx.close()

    # Endpoint to preview data from a specific table or view in a Snowflake database
    def preview_data_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            query = f"SELECT * FROM {db_name}.{schema_name}.{table_or_view_name} LIMIT 10"
            cursor.execute(query)

            # Fetch column names
            column_names = [desc[0] for desc in cursor.description]

            # Fetch data and format rows
            data_preview = []
            for row in cursor.fetchall():
                formatted_row = {
                    col_name: (value if value is not None else "{none}")
                    for col_name, value in zip(column_names, row)
                }
                data_preview.append(formatted_row)

            return {"data_preview": data_preview}
        except HTTPException as e:
            # Re-raise the exception if it's already an HTTPException
            raise e
        except Exception as e:
            self.handle_common_errors(e)
        finally:
            cursor.close()
            ctx.close()

    # list available roles
    def get_available_roles_logic(self, token: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute("SELECT CURRENT_AVAILABLE_ROLES();")
                roles = cursor.fetchall()
                available_roles = ast.literal_eval(roles[0][0])
                # available_roles = [role[0] for role in roles]

                return {"available_roles": available_roles}
            finally:
                cursor.close()
                conn.close()
        except HTTPException as http_exc:      
            raise http_exc 
        except Exception as e:
            self.handle_common_errors(e)

    def preview_data_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str, chart_type: str = "bar"):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()
        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()

        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute(f"USE DATABASE {db_name}")
            cursor.execute(f"USE SCHEMA {schema_name}")

            # Fetch the column names and data types
            column_query = f"DESC TABLE {db_name}.{schema_name}.{table_or_view_name}"
            cursor.execute(column_query)
            column_info = cursor.fetchall()
            column_metadata = [{"name": col[0], "type": col[1]} for col in column_info]

            # Fetch data for chart generation
            data_query = f"SELECT * FROM {table_or_view_name} LIMIT 10"
            cursor.execute(data_query)
            rows = cursor.fetchall()

            plt.figure()

            if chart_type == "bar":
                x_values = [row[0] for row in rows]
                y_values = [row[1] for row in rows]
                plt.bar(x_values, y_values)
            elif chart_type == "line":
                x_values = [row[0] for row in rows]
                y_values = [row[1] for row in rows]
                plt.plot(x_values, y_values)
            elif chart_type == "scatter":
                x_values = [row[0] for row in rows]
                y_values = [row[1] for row in rows]
                plt.scatter(x_values, y_values)
            elif chart_type == "heatmap":
                # For the heatmap, we need a 2D array. This is a simplistic conversion.
                # Your actual implementation might need to differ based on your data structure.
                data_matrix = [list(row) for row in rows]
                plt.imshow(data_matrix, cmap='hot', interpolation='nearest')

            plt.title(f'Data from {table_or_view_name}')
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)

            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return {"chart": image_base64, "columns": column_metadata, "data_preview": rows}
        except Exception as e:
            # Handle or log the error as needed
            raise e
        finally:
            cursor.close()
            ctx.close()

    def generate_custom_chart_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str, x_column: str, y_columns: List[Dict], chart_type: str):
        # Establishing connection and setting context
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()
        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()

        try:
            # Setting the context for the query
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute(f"USE DATABASE {db_name}")
            cursor.execute(f"USE SCHEMA {schema_name}")
            
            # Building the query with dynamic aggregation
            select_clause = f"{x_column}, " + ", ".join([f"{col['aggregation']}({col['name']}) AS {col['name']}" if col.get('aggregation') else col['name'] for col in y_columns])
            query = f"SELECT {select_clause} FROM {table_or_view_name} GROUP BY {x_column} LIMIT 10"
            cursor.execute(query)

            # Fetching the results
            rows = cursor.fetchall()

            # Preparing the data to be JSON serializable
            data = {
                "x_values": [row[0] for row in rows],
                "y_values": {col['name']: [row[i + 1] for row in rows] for i, col in enumerate(y_columns)}
            }

            return data
        except Exception as e:
            raise e
        finally:
            cursor.close()
            ctx.close()