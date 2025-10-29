"""Twitter authentication module.

This module provides Twitter OAuth authentication functionality.
Currently contains configuration for Twitter API authentication handlers.
"""

import datetime
import os.path
from agents import Agent, function_tool, RunContextWrapper
import tweepy

try:
    from config import Settings
except ImportError as e:
    print(e)
    from ..config import Settings
    
SETTINGS = Settings()

# TWITTER_OAUTH_1_HANDLER = tweepy.OAuth1UserHandler(
#     consumer_key=SETTINGS.twitter_api_key,
#     consumer_secret=SETTINGS.twitter_api_key_secret
# )
