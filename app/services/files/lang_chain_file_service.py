from langchain.chains import ConversationalRetrievalChain, LLMChain, ReduceDocumentsChain, StuffDocumentsChain
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from fastapi import HTTPException
import os
import tempfile
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

    def process_document_and_generate_response(self, file_content_bytes, prompt_from_user):
        # Ensure file_content_bytes is a bytes-like object
        if not isinstance(file_content_bytes, bytes):
            raise TypeError(
                "file_content_bytes must be a bytes-like object, not {}".format(type(file_content_bytes).__name__)
            )

        # Step 1: Save file_content_bytes to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content_bytes)
            tmp_file_path = tmp_file.name

        try:
            pages = PyPDFLoader(tmp_file_path).load_and_split()
            document_chain_prompt = PromptTemplate(input_variables=["page_content"], template="{page_content}")
            document_variable_name = "context"
            prompt = PromptTemplate.from_template("Summarize this content: {context}")
            llm_chain = LLMChain(llm=self.llm_chat_model, prompt=prompt)
            combine_docs_chain = StuffDocumentsChain(
                llm_chain=llm_chain,
                document_prompt=document_chain_prompt,
                document_variable_name=document_variable_name,
            )
            db = Chroma.from_documents(pages, self.embedding)
            retriever = db.as_retriever()
            reduce_chain = ReduceDocumentsChain(
                combine_documents_chain=combine_docs_chain,
            )
            question_generator_chain = LLMChain(llm=self.llm_chat_model, prompt=prompt)
            chain = ConversationalRetrievalChain(
                combine_docs_chain=reduce_chain,
                retriever=retriever,
                question_generator=question_generator_chain,
                verbose=True,
            )
            return chain.invoke({"question": prompt_from_user, "chat_history": []})
        except Exception as e:
            print(f"Ошибка при чтении PDF: {e}")
            raise HTTPException(status_code=500, detail=f"error, {e}")
        finally:
            os.remove(tmp_file_path)
