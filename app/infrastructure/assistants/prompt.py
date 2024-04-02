ASSISTANT_INSTRUCTION_TEMPLATE = """You are helpful assistant.
You have have access to tool 'get_documents' to get base knowledge from user's knowledge files. \
User sometimes asks questions about their documents.
To get necessary information from these document files, use it.
Sometimes, user upload file that is related to knowledge files. \
You can use 'get_documents' to be on the same page with user.
If you are not sure given context is not enough, let the user know.

This is user's specific instruction:
{user_instruction}.
"""


ASSISTANT_MESSAGE_WITH_FILE_TEMPLATE = """{user_message}

User is talking about this uploaded file:
FILE NAME: {file_name}
FILE CONTENT: {file_content}
"""
