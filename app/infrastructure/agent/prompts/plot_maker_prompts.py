system_message = """The following is a pandas DataFrame that contains the results of the query that answers the question the user asked: '{question}'    
The following is information about the resulting pandas DataFrame 'df': \n{df_metadata}
The following is sample data from the dataframe: \n{df_head}
"""

human_input = """Can you generate the Python plotly code to chart the results of the dataframe? 
Assume the data is in a pandas dataframe called 'df'. If there is only one value in the dataframe, use an Indicator. 

Initial python code to be updated        

```python
# todo import other required dependencies
# todo Provide the plot
```

Respond with only Python code. Do not answer with any explanations -- just the code."""