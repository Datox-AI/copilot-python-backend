query_and_save_tool_description = """Use this tool if you want to run and save the query. 
Input to this tool is dictionary of a detailed and correct SQL query, and the user's message ID, output is a result from the database and result's stored ID.
Input should be like this: {"query": query, "message_id": Message ID}
The query input should not be in quotes and MUST be in one line. 
If the query is not correct, an error message will be returned. 
If an error is returned, check and rewrite the query and try again.
If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.
DO NOT put backslash before double quotes."""

sql_db_query_description = """You should use this tool to see examples of the column(s).
Input to this tool is a detailed and correct SQL query, output is a result from the database.
The query you are inputing should not be in quotes and MUST be in one line like the example below. 
If the query is not correct, an error message will be returned. 
If an error is returned, rewrite the query, check the query, and try again.
If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.
DO NOT put backslash before double quotes."""

sql_db_schema_description = """Input to this tool is a comma-separated list of tables, \
output is the schema and sample rows for those tables. Make sure that the tables actually exist by calling sql_db_list_tables first! 
There should be one space between table names and DO NOT put any '\n' at the end. 
YOU MUST follow this example input format: table_name_1, table_name_2, table_name_3"""
