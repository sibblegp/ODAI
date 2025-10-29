"""Agent listing and analysis utility.

This module provides utilities for listing and analyzing agent definitions
from the integrations.yaml file. It can list all agents or identify agents
that need logos.
"""

import argparse
import yaml
import json


def iter_agents():
    """Iterate through all agents defined in integrations.yaml.
    
    Yields:
        dict: Agent definition from YAML file
    """
    with open('integrations.yaml', 'r') as f:
        data = yaml.safe_load(f)
        yield from data


def agent_summary(agent: dict) -> dict:
    """Extract summary information from an agent definition.
    
    Args:
        agent: Full agent definition dictionary
        
    Returns:
        dict: Dictionary containing only 'id' and 'name' fields
    """
    return {k: v for k, v in agent.items() if k in ['id', 'name']}


def list_agents():
    """List all agents with their IDs and names.
    
    Prints a formatted JSON list of all agents showing only
    their ID and name fields.
    """
    items = list(map(agent_summary, iter_agents()))
    print(f'List of {len(items)} total agents:')
    print(json.dumps(items, indent=2))


def agent_needs_logo(agent: dict) -> bool:
    """Check if an agent needs a logo.
    
    Args:
        agent: Agent definition dictionary
        
    Returns:
        bool: True if agent needs a logo, False otherwise
    """
    return agent.get('needs_logo', False)


def agents_in_need_of_logos():
    """List all agents that need logos.
    
    Prints a formatted JSON list of agent IDs for agents
    that have 'needs_logo' set to True.
    """
    ids = list(map(
        lambda agent: agent['id'],
        filter(agent_needs_logo, iter_agents()))
    )
    print(f'{len(ids)} total agents in need of logos:')
    print(json.dumps(ids, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--list', action='store_true', help='List all agent names and ids')
    parser.add_argument('--logos', action='store_true', help='List agents that need a logo')
    args = parser.parse_args()
    if args.list:
        list_agents()
    elif args.logos:
        agents_in_need_of_logos()
    else:
        parser.print_help()
