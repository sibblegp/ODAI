"""Configuration module for ODAI API.

This module defines application settings and configuration management,
including API keys, environment settings, and secret management.
Supports both local development (using .env files) and production
(using Google Secret Manager).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
import os

try:
    from connectors.utils import secrets
except ImportError:
    from .connectors.utils import secrets

LOCAL = os.environ.get("LOCAL", "true") == 'true'
PRODUCTION = os.environ.get("PRODUCTION", "false") == "true"
PROJECT_ID = os.environ.get(
    'GOOGLE_CLOUD_PROJECT', 'odai-dev') if not PRODUCTION else 'odai-prod'


def get_secret_or_empty(project_id: str, secret_id: str) -> str:
    """Retrieve a secret from Google Secret Manager or return empty string.
    
    Args:
        project_id: Google Cloud project ID
        secret_id: Secret identifier in Secret Manager
        
    Returns:
        str: Secret value if found, empty string otherwise
    """
    value = secrets.access_secret_version(project_id, secret_id)
    return value if value is not None else ""


class Settings(BaseSettings):
    """Application settings configuration.
    
    Manages all API keys, service credentials, and environment configuration.
    In local development, loads from .env file. In production, loads from
    Google Secret Manager.
    """
    openai_api_key: str = ''
    local: bool = LOCAL
    project_id: str = PROJECT_ID
    key_ring_id: str = 'odai'
    production: bool = False
    alpaca_api_key: str = ''
    alpaca_secret_key: str = ''
    finnhub_api_key: str = ''
    canopy_api_key: str = ''
    coinmarketcap_api_key: str = ''
    aviationstack_api_key: str = ''
    serpapi_api_key: str = ''
    plaid_client_id: str = ''
    plaid_secret: str = ''
    # plaid_sandbox_item_id: str
    # plaid_sandbox_access_token: str
    # slack_token: str
    tripadvisor_api_key: str = ''
    yelp_api_key: str = ''
    # twitter_api_key: str
    # twitter_api_key_secret: str
    # twitter_access_token: str
    # twitter_access_token_secret: str
    # twitter_bearer_token: str
    # twitter_oauth_client_id: str
    # twitter_oauth_client_secret: str
    flightaware_api_key: str = ''
    cloudflare_api_key: str = ''
    cloudflare_account_id: str = ''
    # evernote_consumer_key: str
    # evernote_consumer_secret: str
    ticketmaster_consumer_key: str = ''
    ticketmaster_consumer_secret: str = ''
    weatherapi_api_key: str = ''
    easypost_api_key: str = ''
    movieglu_api_key: str = ''
    movieglu_api_authorization: str = ''
    segment_key: str = ''
    amadeus_client_key: str = ''
    amadeus_client_secret: str = ''
    twilio_account_sid: str = ''
    twilio_auth_token: str = ''
    exchangerate_api_key: str = ''
    accuweather_api_key: str = ''
    caltrain_api_key: str = ''
    sentry_dsn: str = ''

    if os.environ.get("PRODUCTION", "false") == "true":
        production = True
        key_ring_id = 'production'
    else:
        key_ring_id = 'odai'

    if local == True:
        model_config = SettingsConfigDict(env_file=".env")
    else:

        openai_api_key = get_secret_or_empty(PROJECT_ID, "openai_api_key")
        alpaca_api_key = get_secret_or_empty(PROJECT_ID, "alpaca_api_key")
        alpaca_secret_key = get_secret_or_empty(
            PROJECT_ID, "alpaca_secret_key")
        finnhub_api_key = get_secret_or_empty(PROJECT_ID, "finnhub_api_key")
        canopy_api_key = get_secret_or_empty(PROJECT_ID, "canopy_api_key")
        coinmarketcap_api_key = get_secret_or_empty(
            PROJECT_ID, "coinmarketcap_api_key")
        aviationstack_api_key = get_secret_or_empty(
            PROJECT_ID, "aviationstack_api_key")
        serpapi_api_key = get_secret_or_empty(PROJECT_ID, "serpapi_api_key")
        plaid_client_id = get_secret_or_empty(PROJECT_ID, "plaid_client_id")
        plaid_secret = get_secret_or_empty(PROJECT_ID, "plaid_secret")
        # plaid_sandbox_item_id = get_secret_or_empty(PROJECT_ID, "plaid_sandbox_item_id")
        # plaid_sandbox_access_token = get_secret_or_empty(PROJECT_ID, 'plaid_sandbox_access_token')
        # slack_token = get_secret_or_empty(PROJECT_ID, 'slack_token')
        tripadvisor_api_key = get_secret_or_empty(
            PROJECT_ID, 'tripadvisor_api_key')
        yelp_api_key = get_secret_or_empty(PROJECT_ID, 'yelp_api_key')
        # twitter_api_key = get_secret_or_empty(PROJECT_ID, 'twitter_api_key')
        # twitter_api_key_secret = get_secret_or_empty(PROJECT_ID, 'twitter_api_key_secret')
        # twitter_access_token = get_secret_or_empty(PROJECT_ID, 'twitter_access_token')
        # twitter_access_token_secret = get_secret_or_empty(PROJECT_ID, 'twitter_access_token_secret')
        # twitter_bearer_token = get_secret_or_empty(PROJECT_ID, 'twitter_bearer_token')
        flightaware_api_key = get_secret_or_empty(
            PROJECT_ID, 'flightaware_api_key')
        # twitter_oauth_client_id = get_secret_or_empty(PROJECT_ID, 'twitter_oauth_client_id')
        # twitter_oauth_client_secret = get_secret_or_empty(PROJECT_ID, 'twitter_oauth_client_secret')
        cloudflare_api_key = get_secret_or_empty(
            PROJECT_ID, 'cloudflare_api_key')
        cloudflare_account_id = get_secret_or_empty(
            PROJECT_ID, 'cloudflare_account_id')
        # evernote_consumer_key = get_secret_or_empty(PROJECT_ID, 'evernote_consumer_key')
        # evernote_consumer_secret = get_secret_or_empty(PROJECT_ID, 'evernote_consumer_secret')
        ticketmaster_consumer_key = get_secret_or_empty(
            PROJECT_ID, 'ticketmaster_consumer_key')
        ticketmaster_consumer_secret = get_secret_or_empty(
            PROJECT_ID, 'ticketmaster_consumer_secret')
        weatherapi_api_key = get_secret_or_empty(
            PROJECT_ID, 'weatherapi_api_key')
        easypost_api_key = get_secret_or_empty(PROJECT_ID, 'easypost_api_key')
        movieglu_api_key = get_secret_or_empty(PROJECT_ID, 'movieglu_api_key')
        movieglu_api_authorization = get_secret_or_empty(
            PROJECT_ID, 'movieglu_api_authorization')
        segment_key = get_secret_or_empty(PROJECT_ID, 'segment_key')
        amadeus_client_key = get_secret_or_empty(
            PROJECT_ID, 'amadeus_client_key')
        amadeus_client_secret = get_secret_or_empty(
            PROJECT_ID, 'amadeus_client_secret')
        twilio_account_sid = get_secret_or_empty(
            PROJECT_ID, 'twilio_account_sid')
        twilio_auth_token = get_secret_or_empty(
            PROJECT_ID, 'twilio_auth_token')
        exchangerate_api_key = get_secret_or_empty(
            PROJECT_ID, 'exchangerate_api_key')
        accuweather_api_key = get_secret_or_empty(
            PROJECT_ID, 'accuweather_api_key')
        caltrain_api_key = get_secret_or_empty(
            PROJECT_ID, 'caltrain_api_key')
        sentry_dsn = get_secret_or_empty(
            PROJECT_ID, 'sentry_dsn')