import os
import tempfile

from dotenv import load_dotenv
from fastapi import HTTPException
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import ConversationalRetrievalChain, LLMChain, ReduceDocumentsChain, StuffDocumentsChain
from langchain_community.document_loaders import PyPDFLoader, CSVLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

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
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )

        self.embedding = AzureOpenAIEmbeddings(
            azure_endpoint=self.embedding_endpoint,
            openai_api_version=self.embedding_version,
            openai_api_key=self.embedding_key,
            deployment=self.embedding_deployment,
        )

    def process_document_and_generate_response(
        self, file_content_bytes: bytes, prompt_from_user: str, media_types: list
    ):
        # Ensure file_content_bytes is a bytes-like object
        media_type = media_types[0]
        if not isinstance(file_content_bytes, bytes):
            raise TypeError(
                "file_content_bytes must be a bytes-like object, not {}".format(type(file_content_bytes).__name__)
            )

        if media_type == "application/pdf":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_content_bytes)
                tmp_file_path = tmp_file.name
            pages = PyPDFLoader(tmp_file_path).load_and_split()
        if media_type == "text/csv":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
                tmp_file.write(file_content_bytes)
                tmp_file_path = tmp_file.name
            pages = CSVLoader(tmp_file_path).load_and_split()
        else:
            raise HTTPException(status_code=400, detail=f"error, unexpected file extension {media_type}")

        try:
            document_chain_prompt = PromptTemplate(input_variables=["page_content"], template="{page_content}")
            document_variable_name = "context"
            prompt = PromptTemplate.from_template("Summarize this content: {context}")
            llm_chain = LLMChain(llm=self.llm_chat_model, prompt=prompt, callbacks=[StreamingStdOutCallbackHandler()])
            combine_docs_chain = StuffDocumentsChain(
                llm_chain=llm_chain,
                document_prompt=document_chain_prompt,
                document_variable_name=document_variable_name,
                callbacks=[StreamingStdOutCallbackHandler()],
            )
            db = Chroma.from_documents(pages, self.embedding)
            retriever = db.as_retriever()
            reduce_chain = ReduceDocumentsChain(
                combine_documents_chain=combine_docs_chain, callbacks=[StreamingStdOutCallbackHandler()]
            )
            question_generator_chain = LLMChain(
                llm=self.llm_chat_model, prompt=prompt, callbacks=[StreamingStdOutCallbackHandler()]
            )
            chain = ConversationalRetrievalChain(
                combine_docs_chain=reduce_chain,
                retriever=retriever,
                question_generator=question_generator_chain,
                verbose=True,
                callbacks=[StreamingStdOutCallbackHandler()],
            )

            for event in chain.stream({"question": prompt_from_user, "chat_history": []}):
                if event and event["answer"]:
                    response_text = event["answer"]
                    yield response_text
                else:
                    continue

        except Exception as e:
            print(f"Ошибка при чтении PDF: {e}")
            raise HTTPException(status_code=500, detail=f"error, {e}")
        finally:
            os.remove(tmp_file_path)
