from enum import Enum


class ChatType(Enum):
    Analytics = "Analytics"
    FileSearch = "FileSearch"
    DataAnalytics = "DataAnalytics"
    Assistants = "Assistants"

    @property
    def description(self):
        descriptions = {
            ChatType.Analytics: "Used for analytics-based chats",
            ChatType.FileSearch: "Used for file search-based chats",
            ChatType.DataAnalytics: "Used for data analytics chats",
            ChatType.Assistants: "Used for Assistants chats",
            
        }
        return descriptions[self]


class ChatModel(Enum):
    GPT3 = 1
    GPT3_16K = 2
    GPT4_32K = 3

    @property
    def engine_name(self):
        engine_names = {
            ChatModel.GPT3: "GPT3",
            ChatModel.GPT3_16K: "GPT3-16K",
            ChatModel.GPT4_32K: "GPT4-32K",
        }
        return engine_names[self]

    @property
    def max_tokens(self):
        max_tokens = {
            ChatModel.GPT3: 4000,
            ChatModel.GPT3_16K: 16000,
        }
        return max_tokens[self]
