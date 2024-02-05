from enum import Enum


class MessageStatus(Enum):
    Error = "Error"
    Success = "Success"
    Cancelled = "Cancelled"
    Pending = "Pending"


class MessageRole(Enum):
    System = "System"
    User = "User"
    Assistant = "Assistant"
    Function = "Function"
