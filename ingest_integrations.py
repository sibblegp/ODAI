"""Integration data ingestion module.

This module reads integration definitions from YAML files and
ingests them into the Firebase database for use by the application.
"""

import yaml
try:
    from firebase import Integration
except ImportError:
    from .firebase import Integration
    
def ingest_integrations():
    """Ingest integration definitions from YAML file into Firebase.
    
    Reads integration data from integrations.yaml and creates or updates
    Integration records in Firebase with id, logo, name, description,
    and example prompts.
    """
    with open('integrations.yaml', 'r') as file:
        integrations = yaml.safe_load(file)
    for integration in integrations['integrations']:
        print(integration['name'])
        Integration.create_integration(integration['id'], integration['logo'], integration['name'], integration['description'], integration['prompts'])

if __name__ == '__main__':
    ingest_integrations()