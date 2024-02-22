from langchain.chains import ConversationalRetrievalChain, LLMChain, ReduceDocumentsChain, StuffDocumentsChain
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
import os

from dotenv import load_dotenv

load_dotenv()


class LangChainService:
    # Class variables for openai key and  etc
    api_key = os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY")
    api_endpoint = os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("GPT4_TURBO_OPENAI_API_VERSION")
    api_model = os.getenv("GPT4_TURBO_DEPLOYMENT_NAME")

    embedding_key = os.getenv("GPT4_TURBO_AZURE_EMBEDDING_KEY")
    embedding_endpoint = os.getenv("GPT4_TURBO_AZURE_EMBEDDING_ENDPOINT")
    embedding_version = os.getenv("GPT4_TURBO_AZURE_EMBEDDING_VERSION")
    embedding_deployment = os.getenv("GPT4_TURBO_AZURE_EMBEDDING_DEPLOYMENT")

    def __init__(self):
        # Использование значений по умолчанию из переменных окружения
        self.llm_chat_model = AzureChatOpenAI(
            deployment_name=self.api_model,
            azure_endpoint=self.api_endpoint,
            openai_api_version=self.api_version,
            openai_api_key=self.api_key,
            temperature=0,
        )

        self.embedding = AzureOpenAIEmbeddings(
            azure_endpoint=self.embedding_endpoint,
            openai_api_version=self.embedding_version,
            openai_api_key=self.embedding_key,
            deployment=self.embedding_deployment,
        )

    def process_document_and_generate_response(self, file_content_bytes, prompt):
        # Загрузка и обработка документа
        pages = PyPDFLoader(file_content=file_content_bytes).load_and_split()
        db = Chroma.from_documents(pages, self.embedding)
        retriever = db.as_retriever()

        document_chain_prompt = PromptTemplate(input_variables=["page_content"], template="{page_content}")
        document_variable_name = "context"
        llm_chain = LLMChain(llm=self.llm_chat_model, prompt=PromptTemplate.from_template(prompt))
        combine_docs_chain = StuffDocumentsChain(
            llm_chain=llm_chain, document_prompt=document_chain_prompt, document_variable_name=document_variable_name
        )
        reduce_chain = ReduceDocumentsChain(combine_documents_chain=combine_docs_chain)

        chain = ConversationalRetrievalChain(
            combine_docs_chain=reduce_chain, retriever=retriever, question_generator=llm_chain, verbose=True
        )

        return chain.invoke({"question": prompt, "chat_history": []})
