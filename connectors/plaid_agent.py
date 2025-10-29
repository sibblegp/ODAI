from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.api import plaid_api
import plaid
from agents import Agent, function_tool, RunContextWrapper
import json
import datetime
from .utils.responses import ToolResponse
from .google_docs import GOOGLE_DOCS_AGENT
from .gmail import GMAIL_AGENT
from .utils.context import ChatContext, is_plaid_enabled
try:
    from firebase import PlaidToken
except ImportError:
    from ..firebase import PlaidToken
try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()

PLAID_CLIENT_ID = SETTINGS.plaid_client_id
PLAID_SECRET = SETTINGS.plaid_secret
# SANDBOX_ITEM_ID = SETTINGS.plaid_sandbox_item_id
# SANDBOX_ACCESS_TOKEN = SETTINGS.plaid_sandbox_access_token


# Available environments are
# 'Production'
# 'Sandbox'
if not SETTINGS.production:
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            'clientId': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
        }
    )
else:
    configuration = plaid.Configuration(
        host=plaid.Environment.Production,
        api_key={
            'clientId': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
        }
    )

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)


@function_tool(is_enabled=is_plaid_enabled)
def get_accounts_at_plaid(wrapper: RunContextWrapper[ChatContext]) -> dict:
    """Get real-time bank account balances and details from user's connected financial institutions via Plaid.

    WHEN TO USE THIS TOOL:
    - User asks about their bank account balance, checking balance, savings balance, or credit card balance
    - User mentions: "how much money", "what's my balance", "account balance", "bank balance"
    - User asks about their available funds, available credit, or current balance
    - User wants to check multiple account balances at once
    - User needs to know their financial status or account overview
    - User asks "how much do I have in my [checking/savings/bank] account"
    - User asks about specific bank accounts by name (e.g., "Chase checking balance")
    - User wants to verify they have enough funds for a purchase or payment
    - User is planning expenses and needs current balance information
    - User asks about credit utilization or credit limit

    WHAT THIS TOOL DOES:
    - Retrieves real-time balance information for ALL connected bank accounts
    - Shows available balance, current balance, and credit limits where applicable
    - Provides account names, types (checking/savings/credit), and last 4 digits
    - Includes official bank names and account nicknames
    - Returns balance in account currency (typically USD)
    - Shows credit card limits and current balance owed

    KEY TRIGGER PHRASES:
    - "what's my balance"
    - "how much money do I have"
    - "check my bank account"
    - "show me my accounts"
    - "account balance"
    - "available funds"
    - "credit limit"
    - "how much is in my checking"
    - "savings account balance"
    - "financial overview"

    Returns:
        dict: Account information including:
            - Account names and types
            - Current balances
            - Available balances
            - Credit limits (for credit cards)
            - Account and routing numbers (masked)
            - Currency codes

    Note: User must have connected their bank accounts via Plaid first.
    If not connected, will return an error message prompting connection.
    """
    plaid_token = PlaidToken.get_tokens_by_user_id(
        wrapper.context.user.reference_id)
    if plaid_token is None:
        return ToolResponse(
            response_type="error",
            agent_name="Plaid",
            friendly_name="Plaid",
            display_response=True,
            response="You are not connected to Plaid. Please connect your Plaid account to get account information."
        ).to_dict()
    decrypted_tokens = plaid_token.decrypted_tokens()
    try:
        accounts_details = []
        for token in decrypted_tokens:
            request = AccountsBalanceGetRequest(
                access_token=token['auth_token']
            )
            accounts_response = client.accounts_balance_get(request)
            accounts_details.append(accounts_response.to_dict())
    except plaid.ApiException as e:
        response = json.loads(e.body or "{}")
        print(e.body)
        return {'error': {'status_code': e.status, 'display_message':
                          response['error_message'], 'error_code': response['error_code'], 'error_type': response['error_type']}}
    return ToolResponse(
        response_type="plaid_accounts_response",
        agent_name="Plaid",
        friendly_name="Getting Account Information",
        display_response=True,
        response=accounts_details
    ).to_dict()


@function_tool(is_enabled=is_plaid_enabled)
def get_transactions_at_plaid(wrapper: RunContextWrapper[ChatContext]) -> dict:
    """Retrieve detailed transaction history and spending data from user's connected bank and credit card accounts.

    When looking at transaction amounts, Debits (withdrawals) appear as positive amounts and credits (deposits) appear as negative amounts.

    There is no ambiguity here about whether something is a debit or credit. Debits are positive amounts and credits are negative amounts. Do not consider amount size or payee name.

    Correctly interpret amounts based upon the above to determine spending and income.
    
    WHEN TO USE THIS TOOL:
    - User asks about recent transactions, purchases, or spending
    - User mentions: "what did I spend", "recent transactions", "purchase history", "spending"
    - User wants to review charges, payments, or deposits
    - User asks about specific merchants or transaction categories
    - User needs to track expenses or analyze spending patterns
    - User asks "where did my money go" or "what did I buy"
    - User wants to find a specific transaction or payment
    - User asks about recurring charges or subscriptions
    - User needs transaction details for budgeting or expense reports
    - User asks about transactions in a specific time period
    - User wants to categorize spending (food, travel, shopping, etc.)
    - User asks about refunds, returns, or pending transactions
    - User needs to verify if a payment went through
    - User wants to identify unknown charges

    WHAT THIS TOOL DOES:
    - Retrieves last 30 days of transactions (production) or longer history (sandbox)
    - Shows transaction amounts, dates, and merchant names
    - Provides transaction categories (Food, Travel, Shopping, etc.)
    - Includes pending and posted transactions
    - Shows payment methods used for each transaction
    - Identifies recurring subscriptions and regular payments
    - Groups transactions by account for easy review
    - Includes both debits and credits (spending and income)
    - Shows transaction descriptions and merchant details

    KEY TRIGGER PHRASES:
    - "recent transactions"
    - "what did I spend"
    - "show my purchases"
    - "transaction history"
    - "recent charges"
    - "spending history"
    - "where did my money go"
    - "check my transactions"
    - "review my spending"
    - "what did I buy"
    - "list my expenses"
    - "payment history"
    - "recent activity"
    - "bank statement"
    - "credit card charges"
    - "subscription payments"
    - "recurring charges"
    - "spending breakdown"
    - "expense report"
    - "categorize my spending"

    COMMON USE CASES:
    - Expense tracking and budgeting
    - Finding specific transactions
    - Identifying unknown charges
    - Reviewing subscription payments
    - Analyzing spending by category
    - Preparing expense reports
    - Checking if payments cleared
    - Reviewing refunds and returns

    Args:
        wrapper: The execution context wrapper containing user information

    Returns:
        dict: Transactions organized by account containing:
            - Transaction dates and amounts
            - Merchant names and categories
            - Transaction types (debit/credit)
            - Account information for each transaction
            - Pending vs posted status
            - Category classifications (Food, Travel, etc.)

    Note: Requires active Plaid connection. Returns last 30 days in production.
    Transactions are organized by account for easier review and analysis.
    """
    plaid_token = PlaidToken.get_tokens_by_user_id(
        wrapper.context.user.reference_id)
    if plaid_token is None:
        return ToolResponse(
            response_type="error",
            agent_name="Plaid",
            friendly_name="Plaid",
            display_response=True,
            response="You are not connected to Plaid. Please connect your Plaid account to get transaction information."
        ).to_dict()
    decrypted_tokens = plaid_token.decrypted_tokens()

    account_transactions = {}
    transactions_details = []
    for token in decrypted_tokens:
        if not SETTINGS.production:
            start_date = datetime.date(year=2024, month=1, day=1)
            end_date = datetime.date(year=2025, month=12, day=1)
        else:
            start_date = datetime.date.today() - datetime.timedelta(days=30)
            end_date = datetime.date.today()
        request = TransactionsGetRequest(
            access_token=token['auth_token'],
            start_date=start_date,
            end_date=end_date
        )
        transactions_response = client.transactions_get(request)
        transactions = transactions_response.to_dict()
        print(transactions.keys())
        for account in transactions['accounts']:
            account_transactions[account['account_id']] = {
                'account_name': account['name'],
                'account_official_name': account['official_name'],
                'transactions': []
            }
        for transaction in transactions['transactions']:
            print(transaction.keys())
            # print(transaction['date'])
            # print(transaction['authorized_date'])
            transaction['date'] = datetime.datetime.combine(
                transaction['date'], datetime.time(0, 0, 0))
            transaction['authorized_date'] = datetime.datetime.combine(
                transaction['authorized_date'], datetime.time(0, 0, 0))
            account_transactions[transaction['account_id']
                                 ]['transactions'].append(transaction)
    print(account_transactions)
    return ToolResponse(
        response_type="plaid_transactions_response",
        agent_name="Plaid",
        friendly_name="Getting Transactions",
        display_response=True,
        response=account_transactions
    ).to_dict()


PLAID_AGENT = Agent(
    name="Plaid",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX + """You are a Plaid financial assistant that provides comprehensive banking and financial account information.

Your primary functions:
1. Check real-time bank account balances (checking, savings, credit cards)
2. Retrieve transaction history and spending patterns
3. Analyze expenses by category and merchant
4. Track payments, deposits, and transfers
5. Monitor credit card usage and limits
6. Identify recurring subscriptions and charges

You should proactively use your tools when users ask about:
- Account balances or available funds
- Recent transactions or purchases
- Spending patterns or expense tracking
- Specific merchant charges
- Payment verification
- Financial overview or status
- Budget planning information
- Unknown charges or fraud detection

Always provide clear, organized financial information and help users understand their financial picture.""",
    tools=[get_accounts_at_plaid, get_transactions_at_plaid],
    handoff_description=RECOMMENDED_PROMPT_PREFIX + """Plaid - Banking & Financial Account Assistant

I can help with:
• Checking account balances (checking, savings, credit cards)
• Viewing recent transactions and purchase history
• Analyzing spending by category
• Finding specific transactions or payments
• Reviewing recurring charges and subscriptions
• Providing financial account overviews

Use me when the user asks about their bank accounts, balances, transactions, spending, or any financial account information.""",
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT]
)

ALL_TOOLS = [get_accounts_at_plaid, get_transactions_at_plaid]
