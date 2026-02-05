"""
HubSpot CRM Connector
Integration with HubSpot using REST API
"""

import logging
from typing import Dict, List, Any, Optional
import requests
import os
from automation_orchestrator.crm_connector import CRMConnector
from automation_orchestrator.audit import get_audit_logger
from automation_orchestrator.security import SecretManager

logger = logging.getLogger(__name__)
audit = get_audit_logger()


class HubSpotConnector(CRMConnector):
    """HubSpot CRM connector implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize HubSpot connector
        
        Args:
            config: HubSpot configuration containing:
                - api_key: HubSpot API key or
                - access_token: HubSpot OAuth access token
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://api.hubapi.com"
        
        # SECURITY: Load API key from environment or config (prefer environment)
        self.api_key = os.environ.get('HUBSPOT_API_KEY') or os.environ.get('HUBSPOT_ACCESS_TOKEN') or \
                       config.get('api_key') or config.get('access_token')
        
        if not self.api_key:
            raise ValueError("HubSpot api_key or access_token must be provided in config or environment")
        
        self.audit = audit
        
        self.logger.info("HubSpot connector initialized")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def _map_lead_to_hubspot(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Map lead data to HubSpot contact properties"""
        mapping = self.config.get('field_mapping', {})
        
        # Default HubSpot property mapping
        hs_properties = {
            'firstname': lead.get('first_name', ''),
            'lastname': lead.get('last_name', ''),
            'email': lead.get('email', ''),
            'phone': lead.get('phone', ''),
            'company': lead.get('company', ''),
            'hs_lead_status': lead.get('source', 'New'),
        }
        
        # Apply custom mapping
        for custom_field, hs_field in mapping.items():
            if custom_field in lead:
                hs_properties[hs_field] = lead[custom_field]
        
        # Remove empty values
        hs_properties = {k: v for k, v in hs_properties.items() if v}
        
        return hs_properties
    
    def create_or_update_lead(self, lead: Dict[str, Any]) -> bool:
        """
        Create or update a contact in HubSpot
        
        Args:
            lead: Lead data dictionary
        
        Returns:
            True if successful, False otherwise
        """
        try:
            email = lead.get('email')
            if not email:
                self.logger.error("Email is required to create/update HubSpot contact")
                return False
            
            hs_properties = self._map_lead_to_hubspot(lead)
            
            # Check if contact exists by email
            existing_contact = self._find_contact_by_email(email)
            
            if existing_contact:
                # Update existing contact
                contact_id = existing_contact['id']
                url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
                payload = {'properties': hs_properties}
                
                response = requests.patch(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=10
                )
                response.raise_for_status()
                lead['crm_id'] = contact_id
                self.logger.info(f"Updated HubSpot contact {contact_id}")
            else:
                # Create new contact
                url = f"{self.base_url}/crm/v3/objects/contacts"
                payload = {'properties': hs_properties}
                
                response = requests.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=10
                )
                response.raise_for_status()
                contact_id = response.json()['id']
                lead['crm_id'] = contact_id
                self.logger.info(f"Created HubSpot contact {contact_id}")
            
            self.audit.log_event(
                event_type="crm_create",
                lead_id=lead.get('id'),
                details={"hubspot_id": contact_id}
            )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error creating/updating HubSpot contact: {e}")
            self.audit.log_event(
                event_type="error",
                details={"error": str(e), "operation": "hubspot_create_update"}
            )
            return False
    
    def _find_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find contact by email address"""
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts"
            params = {
                'limit': 1,
                'after': 0,
                'filterGroups': [
                    {
                        'filters': [
                            {
                                'propertyName': 'email',
                                'operator': 'EQ',
                                'value': email
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                url + '/search',
                json=params,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json().get('results', [])
            return results[0] if results else None
        
        except Exception as e:
            self.logger.error(f"Error finding HubSpot contact by email: {e}")
            return None
    
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """
        Get contact details from HubSpot
        
        Args:
            lead_id: HubSpot contact ID
        
        Returns:
            Contact data or None if not found
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts/{lead_id}"
            params = {
                'properties': [
                    'firstname', 'lastname', 'email', 'phone', 'company',
                    'hs_lead_status', 'hs_lead_status', 'lifecyclestage'
                ]
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            self.logger.error(f"Error fetching HubSpot contact: {e}")
            return None
    
    def list_leads(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        List contacts from HubSpot
        
        Args:
            filters: Optional filters (source, email, etc.)
        
        Returns:
            List of contacts
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts"
            
            params = {
                'limit': 100,
                'properties': [
                    'firstname', 'lastname', 'email', 'phone', 'company',
                    'hs_lead_status', 'lifecyclestage'
                ]
            }
            
            # Add filters if provided
            if filters and 'email' in filters:
                params['filterGroups'] = [
                    {
                        'filters': [
                            {
                                'propertyName': 'email',
                                'operator': 'EQ',
                                'value': filters['email']
                            }
                        ]
                    }
                ]
                response = requests.post(
                    url + '/search',
                    json=params,
                    headers=self._get_headers(),
                    timeout=10
                )
            else:
                response = requests.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=10
                )
            
            response.raise_for_status()
            
            if 'search' in response.request.url:
                return response.json().get('results', [])
            else:
                return response.json().get('results', [])
        
        except Exception as e:
            self.logger.error(f"Error listing HubSpot contacts: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test HubSpot connection"""
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts"
            response = requests.get(
                url,
                params={'limit': 1},
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            self.logger.info("HubSpot connection test successful")
            return True
        
        except Exception as e:
            self.logger.error(f"HubSpot connection test failed: {e}")
            return False
