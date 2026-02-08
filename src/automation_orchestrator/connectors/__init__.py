"""
CRM Connectors Package
Specific implementations for popular CRM systems
"""

from .salesforce_connector import SalesforceConnector
from .hubspot_connector import HubSpotConnector

__all__ = ['SalesforceConnector', 'HubSpotConnector']
