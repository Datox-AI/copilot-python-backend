import os
import json
from uuid import UUID
from typing import Union

from dotenv import load_dotenv
from fastapi import HTTPException
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_log_to_messages
from langchain.agents.json_chat.prompt import TEMPLATE_TOOL_RESPONSE
from langchain.memory import ConversationTokenBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.tools import tool
from langchain.tools.render import render_text_description
from langchain.tools.retriever import create_retriever_tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# from langchain.retrievers import AzureCognitiveSearchRetriever
from langchain_community.retrievers.azure_cognitive_search import AzureCognitiveSearchRetriever
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI
from langchain.agents.openai_assistant import OpenAIAssistantRunnable
from langchain_core.agents import AgentFinish

from sqlalchemy.orm import Session
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from app.infrastructure.analytics_agent.agent_memory import AnalyticsAgentChatMessageHistory
from app.infrastructure.RAG_agent.output_parser import CustomJSONAgentOutputParser
from app.infrastructure.RAG_agent.prompts.system_prompt import (
    SYSTEM_MESSAGE_TEMPLATE,
)

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


class RAGAgent:
    def __init__(self, chat_id: UUID, db_session: Session):
        # setting up retriever
        self.retriever = AzureCognitiveSearchRetriever(
            service_name=os.getenv("AZURE_COGNITIVE_SEARCH_SERVICE_NAME"),
            index_name=os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_NAME"),
            api_key=os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY"),
            content_key="content",
            top_k=4,
        )

        self.llm = AzureChatOpenAI(
            deployment_name=os.getenv("GPT4_TURBO_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("GPT4_TURBO_OPENAI_API_VERSION"),
            openai_api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            temperature=0,
        )

    def test_azure_ai_logic(self, prompt: str, chat_history):
        contextualize_q_system_prompt = """Given a chat history and the latest user question \
    which might reference context in the chat history, formulate a standalone question \
    which can be understood without the chat history. Do NOT answer the question, \
    just reformulate it if needed and otherwise return it as is."""
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        print("herer"*123)
        contextualize_q_chain = contextualize_q_prompt | self.llm | StrOutputParser()

        def format_docs(docs):
            data = "\n\n".join(doc.page_content for doc in docs)
            return data


        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_MESSAGE_TEMPLATE),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        print("lol"*123)
        

        def contextualized_question(input: dict):
            if input.get("chat_history"):
                return contextualize_q_chain
            else:
                return input["question"]

        rag_chain = (
            # RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
            RunnablePassthrough.assign(context=contextualized_question | self.retriever | format_docs)
            | qa_prompt
            | self.llm
            # | StrOutputParser()
        )

        rag_chain_with_source = RunnableParallel(
            {"context": self.retriever, "question": RunnablePassthrough()}
        ).assign(answer=rag_chain)

        for event in rag_chain.stream({"question": prompt, "chat_history": chat_history}):
            yield event.content
            # if event and event.get("answer", None):
                # yield event, "answer"
            # elif event and event.get("context", None):
                # yield event, "documents"
            # else:
                # continue

    def invoke(self, user_query: str, message_objs):
        message_history = []

        for message_obj in message_objs:
            if message_obj.role.value == "Assistant":
                message_history.append(AIMessage(content=message_obj.text))
            elif message_obj.role.value == "User":
                message_history.append(HumanMessage(content=message_obj.text))
        print(message_history)
        # try:
        for response_text, response_type in self.test_azure_ai_logic(user_query, message_history):
            if response_text and response_type == "answer":
                yield response_text["answer"], response_type
            if response_text and response_type == "documents":
                yield response_text["context"], response_type
        # except Exception as e:
        #     raise HTTPException(status_code=500, detail=f"RAG Agent failed: {e}")




@tool
def get_documents(prompt):
    """This tool for get relevant documents from sharepoint"""
    relevant_docs = get_documents_from_azure_search(prompt)
    final_docs_content = ""
    for doc in relevant_docs:
        final_docs_content = final_docs_content + f"FILE CONTENT NAME: {doc['metadata_spo_item_name']}\nFILE CONTENT: {doc['content']}\n\n"
    return final_docs_content, relevant_docs


def filter_data_by_reranker_score(data, difference_threshold=0.5):
    """
        Filters a list of numbers by removing all elements after finding a difference greater or equal to 'difference_threshold' between consecutive numbers.

        :param numbers: List of numbers to be filtered.
        :param difference_threshold: Threshold value for the difference to trigger filtering.
        :return: Filtered list of numbers.
    """
    filtered_data = []
    for i in range(len(data) - 1):
        current_score = data[i].get('@search.reranker_score', 0)
        next_score = data[i + 1].get('@search.reranker_score', 0)

        filtered_data.append(data[i])

        if abs(current_score - next_score) >= difference_threshold:
            break

    return filtered_data

def get_documents_from_azure_search(user_query: str):
    credential = AzureKeyCredential(os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY"))
    azure_client = SearchClient(
        endpoint=os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_URL"),
        index_name=os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_NAME"),
        credential=credential
    )   
    results = azure_client.search(
        search_text=user_query, 
        query_type="semantic",
        semantic_configuration_name='semantic_search'
    )

    results_list = list(results)
    filtered_results = filter_data_by_reranker_score(results_list)

    return filtered_results




class RAGAssistantAgent:
    THRESHOLD = 0.5

    def __init__(self, thread_id: Union[str, None]):
        # setting up retriever
        client = AzureOpenAI(
            api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),  
            api_version=os.getenv("GPT4_ASSISTANT_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT")
        )        
        
        assistant_id = os.getenv("RAG_AZURE_ASSISTANT_ID")
        my_assistant = client.beta.assistants.retrieve(assistant_id)
        print(my_assistant.__dict__)
        if thread_id:
            self.thread_id = thread_id
        else:
            empty_thread = client.beta.threads.create()
            self.thread_id = empty_thread.id
            
        print(client.__dict__)
        print(type(client))
        self.agent = OpenAIAssistantRunnable(
            assistant_id=assistant_id,
            client=client,
            as_agent=True
        )
        

    
     
    def invoke(self, input: str):
        response = self.agent.invoke(input={
            "content": input,
            "thread_id": self.thread_id
        })
        relevant_docs = []
        while not isinstance(response, AgentFinish):
            tool_outputs = []
            print(response, " ---response")
            for action in response:

                tool_output, relevant_docs = get_documents.invoke(action.tool_input)
                
                print(action.tool, action.tool_input, tool_output, end="\n\n")
                tool_outputs.append(
                    {"output": tool_output, "tool_call_id": action.tool_call_id}
                )
            response = self.agent.invoke(
                {
                    "tool_outputs": tool_outputs,
                    "run_id": action.run_id,
                    "thread_id": action.thread_id,
                }
            )
        
        return {
            "output": response.return_values["output"],
            "thread_id": response.return_values["thread_id"],
            "relevant_docs": relevant_docs
        }
        

