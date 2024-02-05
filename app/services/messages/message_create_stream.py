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
    api_key = os.getenv("OPENAI_API_KEY")
    api_endpoint = os.getenv("OPENAI_ENDPOINT")
    api_version = os.getenv("OPENAI_API_VERSION")

    def __init__(self, model: str):
        self.model = model
        # Setting the API key and base URL for each instance
        self.client = openai.AzureOpenAI(
            api_key=self.api_key, api_version=self.api_version, azure_endpoint=self.api_endpoint
        )

    def stream_responses(self, prompt: str):
        openai_stream = self.client.chat.completions.create(
            model=self.model,
            # engine=self.engine,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            stream=True,
        )
        for event in openai_stream:
            if event.choices and event.choices[0].delta and event.choices[0].delta.content:
                yield event.choices[0].delta.content
            else:
                # If there is no data, skip the iteration
                continue
