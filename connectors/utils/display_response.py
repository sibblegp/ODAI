from openai import OpenAI
import json

try:
    from config import Settings
except ImportError as e:
    print(e)
    from ...config import Settings

SETTINGS = Settings()

OPENAI_CLIENT = OpenAI(api_key=SETTINGS.openai_api_key)


def display_response_check(prompt: str, display_response_prompt: str) -> bool:
    display_response_check = OPENAI_CLIENT.chat.completions.create(
        model="gpt-4o",
        messages=[{'role': 'user', 'content': prompt}, {"role": "user", "content": display_response_prompt}, {
            "role": "user", "content": "Return your response in json format with a boolean value called 'display_response'."}],
        response_format={"type": "json_object"}
    )
    display_response = display_response_check.choices[0].message.content
    if display_response is None:
        return False
    display_response = json.loads(display_response)
    return display_response['display_response']
