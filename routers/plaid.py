"""Plaid integration router module.

This module provides API endpoints for Plaid financial services integration,
including Link token creation and access token exchange for bank account access.
"""

import os
import plaid
from plaid.configuration import logging
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.link_token_create_request_statements import LinkTokenCreateRequestStatements
# from plaid.model.link_token_create_request_cra_options import LinkTokenCreateRequestCraOptions
# from plaid.model.consumer_report_permissible_purpose import ConsumerReportPermissiblePurpose
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.api import plaid_api
import datetime as dt
from datetime import date, timedelta
import datetime
import time
import json
from typing import Annotated
from fastapi import APIRouter, Form, Header, HTTPException
try:
    from firebase import User, PlaidToken
except ImportError:
    from ..firebase import User, PlaidToken
try:
    from authorization import validate_google_token
except ImportError:
    from ..authorization import validate_google_token

PLAID_ROUTER = APIRouter(prefix='/auth/plaid')


def empty_to_none(field) -> str | None:
    """Convert empty environment variable to None.
    
    Args:
        field: Environment variable name
        
    Returns:
        str | None: Environment variable value or None if empty/not set
    """
    value = os.getenv(field)
    if value is None or len(value) == 0:
        return None
    return value

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code.
    
    Args:
        obj: Object to serialize
        
    Returns:
        str: ISO format string for datetime objects
        
    Raises:
        TypeError: If object type is not serializable
    """
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')
PLAID_PRODUCTS = os.getenv('PLAID_PRODUCTS', 'transactions,auth').split(',')
PLAID_COUNTRY_CODES = os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')
PLAID_REDIRECT_URI = empty_to_none('PLAID_REDIRECT_URI')

try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()

PLAID_CLIENT_ID = SETTINGS.plaid_client_id
PLAID_SECRET = SETTINGS.plaid_secret

if not SETTINGS.production:
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            'clientId': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
            'plaidVersion': '2020-09-14'
        }
    )
else:
    configuration = plaid.Configuration(
        host=plaid.Environment.Production,
        api_key={
            'clientId': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
            'plaidVersion': '2020-09-14'
        }
    )

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

products = []
for product in PLAID_PRODUCTS:
    products.append(Products(product))
    
@PLAID_ROUTER.post('/info')
def info():
    """Get Plaid configuration information.
    
    Returns:
        dict: Plaid configuration with item_id, access_token, and products
    """
    return {
        'item_id': None,
        'access_token': None,
        'products': PLAID_PRODUCTS
    }

@PLAID_ROUTER.post('/create_link_token')
def create_link_token(authorization: Annotated[str, Header()]) -> dict:
    """Create a Plaid Link token for the authenticated user.
    
    Args:
        authorization: Bearer token from request header
        
    Returns:
        dict: Plaid Link token response or error message
    """
    valid, user, user_anonymous = validate_google_token(authorization)
    if not valid:
        return {'error': 'Invalid token'}
    if user_anonymous:
        return {'error': 'Anonymous user'}
    if user is None:
        return {'error': 'User not found'}
    try:
        request = LinkTokenCreateRequest(
            products=products,
            client_name="ODAI",
            country_codes=list(
                map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(time.time())
            )
        )
        if request is not None and isinstance(request, LinkTokenCreateRequest):
            if PLAID_REDIRECT_URI != None:
                request['redirect_uri'] = PLAID_REDIRECT_URI
            if Products('statements') in products:
                statements = LinkTokenCreateRequestStatements(
                    end_date=date.today(),
                    start_date=date.today()-timedelta(days=30)
                )
                request['statements'] = statements

        response = client.link_token_create(request)
        
        PlaidToken.create_token_request(user, PLAID_REDIRECT_URI)
        return response.to_dict()
    except plaid.ApiException as e:
        print(e)
        return json.loads(e.body or '{}')


@PLAID_ROUTER.post('/set_access_token')
def set_access_token(authorization: Annotated[str, Header()], public_token: Annotated[str, Form()]):
    """Exchange a Plaid public token for an access token and save it.
    
    Args:
        authorization: Bearer token from request header
        public_token: Plaid public token from Link flow
        
    Returns:
        dict: Exchange response with access token (dev) or success status (prod)
    """
    valid, user, user_anonymous = validate_google_token(authorization)
    if not valid:
        return {'error': 'Invalid token'}
    if user_anonymous:
        return {'error': 'Anonymous user'}
    if user is None:
        return {'error': 'User not found'}
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']
        request = AccountsBalanceGetRequest(
            access_token=access_token
        )
        accounts_response = client.accounts_balance_get(request)
        account_names_and_numbers = []
        logging.info(accounts_response) 
        for account in accounts_response['accounts']:
            logging.info(account.get('name', account.get('official_name', 'Unknown')))
        for account in accounts_response['accounts']:
            account_names_and_numbers.append({'name': account['name'], 'mask': account['mask']})
        bank_name = accounts_response['item']['institution_name']
        PlaidToken.save_or_add_token(account_names_and_numbers, access_token, item_id, user, bank_name)
        return {'success': True}
    except plaid.ApiException as e:
        return json.loads(e.body or '{}')
    
@PLAID_ROUTER.get('/accounts')
def get_accounts(authorization: Annotated[str, Header()]):
    """Get the accounts for the authenticated user.
    
    Args:
        authorization: Bearer token from request header
        
    Returns:
        dict: Accounts response with account details
    """
    valid, user, user_anonymous = validate_google_token(authorization)
    if not valid:
        raise HTTPException(status_code=401, detail='Invalid token')
    if user_anonymous:
        raise HTTPException(status_code=401, detail='Anonymous user')
    if user is None:
        raise HTTPException(status_code=401, detail='User not found')
    accounts = PlaidToken.get_accounts_by_user_id(user.reference_id)
    return {'accounts': accounts}

@PLAID_ROUTER.delete('/accounts/{account_id}')
def delete_token(authorization: Annotated[str, Header()], account_id: str):
    """Delete a Plaid token for the authenticated user.
    
    Args:
        authorization: Bearer token from request header
        account_id: Plaid account ID to delete
        
    Returns:
        dict: Success message
    """
    valid, user, user_anonymous = validate_google_token(authorization)
    if not valid:
        raise HTTPException(status_code=401, detail='Invalid token')
    if user_anonymous:
        raise HTTPException(status_code=401, detail='Anonymous user')
    if user is None:
        raise HTTPException(status_code=401, detail='User not found')
    user_tokens = PlaidToken.get_tokens_by_user_id(user.reference_id)
    if user_tokens is None:
        raise HTTPException(status_code=401, detail='User not found')
    if user_tokens.delete_account(user, account_id):
        return {'success': True}
    else:
        raise HTTPException(status_code=404, detail='Token not found')