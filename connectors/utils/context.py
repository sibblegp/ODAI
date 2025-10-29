from dataclasses import dataclass
from typing import Optional
try:
    from firebase import User
except ImportError as e:
    from ...firebase import User
    
try:
    from config import Settings
except ImportError as e:
    from ...config import Settings

from openai import OpenAI

@dataclass
class ChatContext:
    user_id: str
    logged_in: bool
    chat_id: str
    prompt: str
    production: bool
    project_id: str
    user: User
    settings: Settings
    openai_client: OpenAI
    is_google_enabled: bool = False
    is_plaid_enabled: bool = False
    
def is_google_enabled(ctx, agent) -> bool:
    return ctx.context.is_google_enabled

def is_plaid_enabled(ctx, agent) -> bool:
    return ctx.context.is_plaid_enabled