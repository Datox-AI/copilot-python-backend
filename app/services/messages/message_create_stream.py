import json
import os
from abc import ABC, abstractmethod

import openai
from dotenv import load_dotenv

load_dotenv()


def parse_questions(questions_text: str) -> list:
    """
    Преобразует текст follow-up вопросов, предположительно в формате JSON, в список строк.

    Параметры:
        questions_text (str): Текст вопросов в формате JSON.

    Возвращает:
        list: Список строк, каждая из которых является вопросом.
    """
    try:
        # Преобразуем строку JSON в список
        questions = json.loads(questions_text)

        # Убедимся, что результат является списком
        if not isinstance(questions, list):
            raise ValueError("Follow-up questions text is not a valid list")

        # Дополнительно можно проверить, что каждый элемент списка - это строка
        for question in questions:
            if not isinstance(question, str):
                raise ValueError("Each follow-up question should be a string")

        return questions
    except json.JSONDecodeError:
        # Обработка случая, когда текст не является валидным JSON
        print("Failed to decode follow-up questions from JSON.")
        return []
    except ValueError as e:
        # Любые другие ошибки значения
        print(f"Error parsing follow-up questions: {e}")
        return []


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
        self.question_prompt = """
            Generate 3 follow-up questions that the user might ask based on the previous conversation.
            These should be questions that the user might have for the assistant.
            Format the questions as a JSON-like list of strings.
            Please avoid adding any additional text outside of the JSON structure.
            """

    def stream_responses(self, messages: list, prompt: str, reply_message: str = None):
        """
        Генерирует ответы на заданный prompt в реальном времени.
        Этот метод должен быть асинхронным генератором, который yield'ит текст ответа по мере его генерации.
        """
        message_history = []
        questions_list = []
        is_question = False
        error_message = None
        message_history.append({"role": "system", "content": "You are a helpful assistant."})

        for message_obj in messages:
            message_role = None
            if message_obj.role.value == "Assistant":
                message_role = "assistant"
            elif message_obj.role.value == "User":
                message_role = "user"
            else:
                print(message_obj.__dict__)
            message_history.append({"role": message_role, "content": message_obj.text})
        message_history.append(
            {"role": "user", "content": prompt},
        )
        if reply_message:
            message_history.append(
                {
                    "role": "system",
                    "content" : "User is referring to this message: {}".format(reply_message)
                }
            )
        try:
            openai_stream = self.client.chat.completions.create(
                model=self.model,
                messages=message_history,
                temperature=0.7,
                stream=True,
            )
            for event in openai_stream:
                if event.choices and event.choices[0].delta and event.choices[0].delta.content:
                    response_text = event.choices[0].delta.content
                    yield response_text, is_question, questions_list, error_message
                else:
                    continue
            is_question = True
            message_history.append({"role": "system", "content": self.question_prompt})
            follow_up_openai_stream = self.client.chat.completions.create(
                model=self.model,
                messages=message_history,
                temperature=0.7,
                stream=True,
            )
            questions_text = ""
            for event in follow_up_openai_stream:
                if event.choices and event.choices[0].delta and event.choices[0].delta.content:
                    questions_text += event.choices[0].delta.content
                else:
                    continue
            questions_list = parse_questions(questions_text)
            yield response_text, is_question, questions_list, error_message
        except Exception as e:
            # Обработка ошибок подключения или API
            error_message = str(e)
            yield "", False, [], error_message
