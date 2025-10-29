"""TokenUsage model for tracking OpenAI token consumption."""

import datetime

from ..base import FireStoreObject

try:
    from firebase.models.user import User
except ImportError:
    from ..models.user import User

class TokenUsage(FireStoreObject):
    """TokenUsage model for tracking OpenAI token consumption."""

    usage: dict
    total_usage: dict

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

    @classmethod
    async def add_usage(cls, user: 'User', input_tokens: int, cached_input_tokens: int, output_tokens: int):
        gpt_cost_per_million_input_tokens = 2.00
        gpt_cost_per_million_output_tokens = 8.00
        gpt_cost_per_million_cached_input_tokens = 0.50
        uncached_input_tokens = input_tokens - cached_input_tokens
        uncached_input_cost = (uncached_input_tokens /
                               1000000) * gpt_cost_per_million_input_tokens
        cached_input_cost = (cached_input_tokens / 1000000) * \
            gpt_cost_per_million_cached_input_tokens
        output_cost = (output_tokens / 1000000) * \
            gpt_cost_per_million_output_tokens
        total_cost = uncached_input_cost + cached_input_cost + output_cost
        existing_usage_request = cls.token_usage.document(
            user.reference_id).get()
        current_date_year = datetime.datetime.now().strftime("%Y")
        current_date_month = datetime.datetime.now().strftime("%m")
        current_date_day = datetime.datetime.now().strftime("%d")
        if existing_usage_request.exists:
            existing_usage = cls(existing_usage_request)
            if hasattr(existing_usage, 'usage'):
                if current_date_year in existing_usage.usage:
                    if current_date_month in existing_usage.usage[current_date_year]:
                        if current_date_day in existing_usage.usage[current_date_year][current_date_month]:
                            existing_usage.usage[current_date_year][current_date_month][
                                current_date_day]['input_tokens'] += input_tokens
                            existing_usage.usage[current_date_year][current_date_month][
                                current_date_day]['output_tokens'] += output_tokens
                            existing_usage.usage[current_date_year][current_date_month][
                                current_date_day]['cached_input_tokens'] += cached_input_tokens
                            existing_usage.usage[current_date_year][current_date_month][
                                current_date_day]['total_cost'] += total_cost
                            existing_usage.usage[current_date_year][current_date_month]['usage'] = {
                                'input_tokens': existing_usage.usage[current_date_year][current_date_month]['usage']['input_tokens'] + input_tokens,
                                'output_tokens': existing_usage.usage[current_date_year][current_date_month]['usage']['output_tokens'] + output_tokens,
                                'cached_input_tokens': existing_usage.usage[current_date_year][current_date_month]['usage']['cached_input_tokens'] + cached_input_tokens,
                                'total_cost': existing_usage.usage[current_date_year][current_date_month]['usage']['total_cost'] + total_cost
                            }
                            existing_usage.usage[current_date_year]['usage'] = {
                                'input_tokens': existing_usage.usage[current_date_year]['usage']['input_tokens'] + input_tokens,
                                'output_tokens': existing_usage.usage[current_date_year]['usage']['output_tokens'] + output_tokens,
                                'cached_input_tokens': existing_usage.usage[current_date_year]['usage']['cached_input_tokens'] + cached_input_tokens,
                                'total_cost': existing_usage.usage[current_date_year]['usage']['total_cost'] + total_cost
                            }
                        else:
                            existing_usage.usage[current_date_year][current_date_month][current_date_day] = {
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'cached_input_tokens': cached_input_tokens,
                                'total_cost': total_cost
                            }
                            existing_usage.usage[current_date_year][current_date_month]['usage'] = {
                                'input_tokens': existing_usage.usage[current_date_year][current_date_month]['usage']['input_tokens'] + input_tokens,
                                'output_tokens': existing_usage.usage[current_date_year][current_date_month]['usage']['output_tokens'] + output_tokens,
                                'cached_input_tokens': existing_usage.usage[current_date_year][current_date_month]['usage']['cached_input_tokens'] + cached_input_tokens,
                                'total_cost': existing_usage.usage[current_date_year][current_date_month]['usage']['total_cost'] + total_cost
                            }
                            existing_usage.usage[current_date_year]['usage'] = {
                                'input_tokens': existing_usage.usage[current_date_year]['usage']['input_tokens'] + input_tokens,
                                'output_tokens': existing_usage.usage[current_date_year]['usage']['output_tokens'] + output_tokens,
                                'cached_input_tokens': existing_usage.usage[current_date_year]['usage']['cached_input_tokens'] + cached_input_tokens,
                                'total_cost': existing_usage.usage[current_date_year]['usage']['total_cost'] + total_cost
                            }
                    else:
                        existing_usage.usage[current_date_year] = {
                            current_date_month: {
                                'usage': {
                                    'input_tokens': input_tokens,
                                    'output_tokens': output_tokens,
                                    'cached_input_tokens': cached_input_tokens,
                                    'total_cost': total_cost
                                },
                                current_date_day: {
                                    'input_tokens': input_tokens,
                                    'output_tokens': output_tokens,
                                    'cached_input_tokens': cached_input_tokens,
                                    'total_cost': total_cost
                                }
                            },
                            'usage': {
                                'input_tokens': existing_usage.usage[current_date_year]['usage']['input_tokens'] + input_tokens,
                                'output_tokens': existing_usage.usage[current_date_year]['usage']['output_tokens'] + output_tokens,
                                'cached_input_tokens': existing_usage.usage[current_date_year]['usage']['cached_input_tokens'] + cached_input_tokens,
                                'total_cost': existing_usage.usage[current_date_year]['usage']['total_cost'] + total_cost
                            }
                        }
                else:
                    existing_usage.usage[current_date_year] = {
                        'usage': {
                            'input_tokens': existing_usage.usage[current_date_year]['usage']['input_tokens'] + input_tokens,
                            'output_tokens': existing_usage.usage[current_date_year]['usage']['output_tokens'] + output_tokens,
                            'cached_input_tokens': existing_usage.usage[current_date_year]['usage']['cached_input_tokens'] + cached_input_tokens,
                            'total_cost': existing_usage.usage[current_date_year]['usage']['total_cost'] + total_cost
                        },
                        current_date_month: {
                            'usage': {
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'cached_input_tokens': cached_input_tokens,
                                'total_cost': total_cost
                            },
                            current_date_day: {
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'cached_input_tokens': cached_input_tokens,
                                'total_cost': total_cost
                            }
                        }
                    }
            else:
                existing_usage.usage = {
                    current_date_year: {
                        'usage': {
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'cached_input_tokens': cached_input_tokens,
                            'total_cost': total_cost
                        },
                        current_date_month: {
                            'usage': {
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'cached_input_tokens': cached_input_tokens,
                                'total_cost': total_cost
                            },
                            current_date_day: {
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'cached_input_tokens': cached_input_tokens,
                                'total_cost': total_cost
                            }
                        }
                    }
                }
            cls.token_usage.document(existing_usage.reference_id).update(
                {'usage': existing_usage.usage})
        else:
            cls.token_usage.document(user.reference_id).set({
                'usage': {
                    current_date_year: {
                        'usage': {
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'cached_input_tokens': cached_input_tokens,
                            'total_cost': total_cost
                        },
                        current_date_month: {
                            'usage': {
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'cached_input_tokens': cached_input_tokens,
                                'total_cost': total_cost
                            },
                            current_date_day: {
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'cached_input_tokens': cached_input_tokens,
                                'total_cost': total_cost
                            }
                        }
                    }
                }})
        existing_usage = cls(cls.token_usage.document(user.reference_id).get())

        if existing_usage and hasattr(existing_usage, 'total_usage'):
            existing_usage.total_usage['input_tokens'] += input_tokens
            existing_usage.total_usage['output_tokens'] += output_tokens
            existing_usage.total_usage['cached_input_tokens'] += cached_input_tokens
            existing_usage.total_usage['total_cost'] += total_cost
            cls.token_usage.document(existing_usage.reference_id).update({
                'total_usage': existing_usage.total_usage
            })
        else:
            cls.token_usage.document(user.reference_id).update({
                'total_usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'cached_input_tokens': cached_input_tokens,
                    'total_cost': total_cost
                }
            })
