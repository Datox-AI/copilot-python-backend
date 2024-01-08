from enum import Enum

class MessageStatus(Enum):
    Error = -1
    Success = 1
    Cancelled = 2
    Pending = 3
    
class MessageRole(Enum):
    System = 0
    User = 1
    Assistant = 2
    Function = 3