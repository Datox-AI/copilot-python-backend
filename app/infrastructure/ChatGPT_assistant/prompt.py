FOLLOWUP_QUESTIONS_PROMPT = """Following below are question and answer between user and AI.
user: '{question}'
ai: '{answer}'
Based on them, generate a list of 3 followup questions (or answers if AI asked a question) that user might ask in the following format
{{"questions_answers": ["question1", "question2"]}}"""
