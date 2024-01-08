from enum import Enum

class ChatType(Enum):
    Analytics = 0
    FileSearch = 1

    @property
    def description(self):
        descriptions = {
            ChatType.Analytics: "Used for analytics-based chats",
            ChatType.FileSearch: "Used for file search-based chats",
        }
        return descriptions[self]

class ChatModel(Enum):
    GPT3 = 1
    GPT3_16K = 2

    @property
    def engine_name(self):
        engine_names = {
            ChatModel.GPT3: "GPT3",
            ChatModel.GPT3_16K: "GPT3-16K",
        }
        return engine_names[self]

    @property
    def max_tokens(self):
        max_tokens = {
            ChatModel.GPT3: 4000,
            ChatModel.GPT3_16K: 16000,
        }
        return max_tokens[self]