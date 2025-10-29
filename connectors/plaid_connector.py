from agents import Agent, RunContextWrapper, function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from .utils.context import ChatContext
from .utils.responses import (ConnectPlaidAccountResponse)

@function_tool
def connect_plaid_account(wrapper: RunContextWrapper[ChatContext]) -> ConnectPlaidAccountResponse:
    """
    Call this tool when a user says "Connect my bank account" or "Connect my credit card" or "Connect my investment account" or "Connect my loan" or "Connect my mortgage" or "Connect my other financial institution"
    
    Agent Instruction:
    Use this function when a user wants to:
    1. Connect their bank account, credit card, or investment institution
    2. Check bank account balance or transaction historybut doesn't have an account connected
    3. View credit card balance or transactions but doesn't have a card connected
    4. Access investment account information but lacks connection
    5. Link any financial institution for transaction history, balances, or account details
    
    This function initiates the Plaid connection process to securely link financial accounts including:
    - Checking and savings accounts
    - Credit cards and debit cards
    - Investment and brokerage accounts
    - Loans and mortgages
    
    Response Types to Expect:
    - 'connect_plaid_account': Indicates the user can proceed to connect their financial accounts
    """
    return ConnectPlaidAccountResponse('Plaid Connector').to_dict()
    
PLAID_CONNECTOR_AGENT = Agent(
    name="Plaid Connector",
    instructions=RECOMMENDED_PROMPT_PREFIX + "This agent is responsible for connecting plaid or a user's bank or credit card accounts. ALWAYS CALL THE connect_plaid_account TOOL WHEN HANDED OFF TO. Don't say click here. Say click the button above. Call the connect_plaid_account tool when a user says 'Connect my bank account' or 'Connect my credit card' or 'Connect my investment account' or 'Connect my loan' or 'Connect my mortgage' or 'Connect my other financial institution'",
    tools=[connect_plaid_account],
)