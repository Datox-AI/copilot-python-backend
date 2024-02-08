from abc import ABC, abstractmethod
import openai
from dotenv import load_dotenv

import os

load_dotenv()


class ChatStreamInterface(ABC):
    @abstractmethod
    def stream_responses(self, prompt: str):
        pass


class OpenAIChatStream:
    # Class variables for openai key and  etc
    api_key = os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY")
    api_endpoint = os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("GPT4_TURBO_OPENAI_API_VERSION")
    api_model = os.getenv("GPT4_TURBO_DEPLOYMENT_NAME")

    def __init__(self):
        self.model = self.api_model
        # Setting the API key and base URL for each instance
        self.client = openai.AzureOpenAI(
            api_key=self.api_key, api_version=self.api_version, azure_endpoint=self.api_endpoint
        )

    def stream_responses(self, prompt: str):
        """
        Генерирует ответы на заданный prompt в реальном времени.
        Этот метод должен быть асинхронным генератором, который yield'ит текст ответа по мере его генерации.
        """
        try:
            openai_stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                stream=True,
            )

            for event in openai_stream:
                if event.choices and event.choices[0].delta and event.choices[0].delta.content:
                    response_text = event.choices[0].delta.content
                    yield response_text
                else:
                    # Если нет данных, пропускаем итерацию
                    continue
        except Exception as e:
            # Обработка ошибок подключения или API
            print(f"Error while streaming responses: {e}")
            yield "Sorry, there was an error processing your request."
