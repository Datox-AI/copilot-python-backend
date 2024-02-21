import os
import re

from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from app.infrastructure.analytics_agent.plot_maker.helpers import extract_python_code
from app.infrastructure.analytics_agent.prompts.plot_maker_prompts import human_input, system_message


class PlotMaker:
    def __init__(self, message_id):
        self.message_id = message_id
        # some shit to get question and stored data from azure blob storage
        self.question = None
        self.df = None

    def produce_figure(self):
        # setting up the prompt for chain
        llm_chat_model = AzureChatOpenAI(
            deployment_name=os.getenv("GPT4_TURBO_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("GPT4_TURBO_OPENAI_API_VERSION"),
            openai_api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            temperature=0,
        )
        chat_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    system_message.format(question=self.question, df_metadata=self.df.dtypes, df_head=self.df.head()),
                ),
                ("human", "{user_input}"),
            ]
        )
        # chain
        llm_chain = LLMChain(llm=llm_chat_model, prompt=chat_template)
        # invoking with human input
        response = llm_chain(chat_template.format_messages(user_input=human_input))
        # extracting the plotly code
        raw_plotly_code = self._extract_python_code(response["text"])
        plotly_code = raw_plotly_code.replace("fig.show()", "")
        # running the code
        ldict = {"df": self.df}
        exec(plotly_code, ldict)
        figure = ldict["fig"]

        return plotly_code

    def _extract_python_code(self, markdown_string: str) -> str:
        # Regex pattern to match Python code blocks
        pattern = r"```[\w\s]*python\n([\s\S]*?)```|```([\s\S]*?)```"

        # Find all matches in the markdown string
        matches = re.findall(pattern, markdown_string, re.IGNORECASE)

        # Extract the Python code from the matches
        python_code = []
        for match in matches:
            python = match[0] if match[0] else match[1]
            python_code.append(python.strip())

        if len(python_code) == 0:
            return markdown_string

        return python_code[0]
