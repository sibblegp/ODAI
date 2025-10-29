from agents import function_tool
from agents.agent import Agent, FunctionTool

try:
    from config import Settings
except:
    from ..config import Settings

from typing import Optional

import requests
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from .utils.responses import ToolResponse

SETTINGS = Settings()

EXCHANGE_RATE_API_KEY = SETTINGS.exchangerate_api_key


@function_tool
def get_exchange_rates_for_currency(currency_ISO4217: str) -> dict:
    """
    Retrieve current exchange rates for a specific currency against all available currencies.

    This function fetches the latest exchange rates from the Exchange Rate API for a given
    base currency. The response includes conversion rates to all supported currencies.

    Args:
        currency_ISO4217 (str): The ISO 4217 currency code (e.g., 'USD', 'EUR', 'GBP') 
                                for which to retrieve exchange rates.

    Returns:
        dict: A ToolResponse dictionary with:
            - response_type: "exchange_rate_for_currency"
            - response: API response data containing:
                - result: "success" or "error"
                - documentation: API documentation URL
                - terms_of_use: Terms of use URL
                - time_last_update_unix: Unix timestamp of last update
                - time_last_update_utc: UTC datetime string of last update
                - time_next_update_unix: Unix timestamp of next update
                - time_next_update_utc: UTC datetime string of next update
                - base_code: The base currency ISO code (e.g., "USD")
                - conversion_rates: Dictionary mapping currency codes to exchange rates
                  Example: {"EUR": 0.92, "GBP": 0.79, "JPY": 149.50, ...}
            - agent_name: "Exchange Rate Agent"
            - friendly_name: "Exchange Rate for Currency"
            - display_response: True

    Example:
        >>> get_exchange_rates_for_currency("USD")
        Returns exchange rates for USD against all other currencies
    """
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/latest/{currency_ISO4217}"
    response = requests.get(url)
    data = response.json()
    return ToolResponse(
        response_type="exchange_rate_for_currency",
        response=data,
        agent_name="Exchange Rate Agent",
        friendly_name="Exchange Rate for Currency",
        display_response=True,
    ).to_dict()


@function_tool
def get_exchange_rate_for_currency_pair(from_currency_ISO4217: str, to_currency_ISO4217: str, amount: Optional[float] = None) -> dict:
    """
    Get the exchange rate between two specific currencies with optional amount conversion.

    This function retrieves the current exchange rate between a source currency and a target
    currency. If an amount is provided, it also calculates the converted value.

    Args:
        from_currency_ISO4217 (str): The ISO 4217 code of the source currency (e.g., 'USD', 'EUR').
        to_currency_ISO4217 (str): The ISO 4217 code of the target currency (e.g., 'GBP', 'JPY').
        amount (Optional[float]): Optional amount to convert. If provided, the response will
                                  include the converted amount. Defaults to None.

    Returns:
        dict: A ToolResponse dictionary with:
            - response_type: "exchange_rate_for_currency_pair"
            - response: API response data including:
                - base_code: Source currency code
                - target_code: Target currency code
                - conversion_rate: Exchange rate from source to target
                - conversion_result: Converted amount (if amount was provided)
            - agent_name: "Exchange Rate Agent"
            - friendly_name: "Exchange Rate for Currency Pair"
            - display_response: True

    Examples:
        >>> get_exchange_rate_for_currency_pair("USD", "EUR")
        Returns the exchange rate from USD to EUR

        >>> get_exchange_rate_for_currency_pair("USD", "EUR", 100.0)
        Returns the exchange rate and converts 100 USD to EUR
    """
    if amount is not None:
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/pair/{from_currency_ISO4217}/{to_currency_ISO4217}/{amount}"
    else:
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/pair/{from_currency_ISO4217}/{to_currency_ISO4217}"
    response = requests.get(url)
    data = response.json()
    return ToolResponse(
        response_type="exchange_rate_for_currency_pair",
        response=data,
        agent_name="Exchange Rate Agent",
        friendly_name="Exchange Rate for Currency Pair",
        display_response=True,
    ).to_dict()


EXCHANGE_RATE_AGENT = Agent(
    name="Exchange Rate Agent",
    model="gpt-4o",
    handoff_description="An agent that provides real-time currency exchange rate information and conversion services.",
    instructions=RECOMMENDED_PROMPT_PREFIX + """An agent that provides real-time currency exchange rate information and conversion services.

This agent can help with:
1. Retrieving current exchange rates for any currency against all other supported currencies
2. Getting specific exchange rates between two currencies
3. Converting amounts from one currency to another

Use this agent when users ask about:
- Current exchange rates (e.g., "What's the USD to EUR exchange rate?")
- Currency conversions (e.g., "Convert 100 USD to EUR")
- Multiple exchange rates for a base currency (e.g., "Show me all exchange rates for GBP")
- Comparing currency values

The agent uses ISO 4217 currency codes (e.g., USD, EUR, GBP, JPY) and provides up-to-date exchange rate data including timestamps for when rates were last updated.""",
    tools=[get_exchange_rates_for_currency,
           get_exchange_rate_for_currency_pair],
)
