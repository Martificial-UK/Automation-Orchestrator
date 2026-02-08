"""
Salesforce CRM Connector
Integration with Salesforce using REST API
"""

import logging
from typing import Dict, List, Any, Optional
import requests
from automation_orchestrator.crm_connector import CRMConnector
from automation_orchestrator.audit import get_audit_logger
from automation_orchestrator.security import SecretManager

logger = logging.getLogger(__name__)
audit = get_audit_logger()


class SalesforceConnector(CRMConnector):
    """Salesforce CRM connector implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Salesforce connector
        
        Args:
            config: Salesforce configuration containing:
                - instance_url: Salesforce instance URL (e.g., https://na1.salesforce.com)
                - client_id: OAuth client ID
                - client_secret: OAuth client secret
                - username: Salesforce username
                - password: Salesforce password
                - security_token: Salesforce security token
                OR
                - access_token: Pre-authenticated access token
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.base_url = config.get('instance_url', '').rstrip('/')
        self.access_token = None
        self.audit = audit
        
        # Authenticate if not using pre-authenticated token
        if 'access_token' in config:
            self.access_token = config['access_token']
        else:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Salesforce using OAuth with secure secret handling"""
        try:
            auth_url = f"{self.base_url}/services/oauth2/token"
            
            # SECURITY: Use SecretManager to load credentials from environment
            # Fall back to config if secrets not in environment
            client_id = self._get_config_secret('client_id', 'SF_CLIENT_ID')
            client_secret = self._get_config_secret('client_secret', 'SF_CLIENT_SECRET')
            username = self._get_config_secret('username', 'SF_USERNAME')
            password = self._get_config_secret('password', 'SF_PASSWORD')
            security_token = self.config.get('security_token', '')
            
            if not all([client_id, client_secret, username, password]):
                raise ValueError("Missing required Salesforce credentials")
            
            payload = {
                'grant_type': 'password',
                'client_id': client_id,
                'client_secret': client_secret,
                'username': username,
                'password': password + security_token
            }
            
            response = requests.post(auth_url, data=payload, timeout=10, verify=True)
            response.raise_for_status()
            
            self.access_token = response.json()['access_token']
            self.logger.info("Successfully authenticated with Salesforce")
            audit.log_event(
                event_type="crm_authenticated",
                details={"crm": "salesforce"}
            )
        
        except Exception as e:
            self.logger.error(f"Salesforce authentication failed: {e}")
            audit.log_event(
                event_type="error",
                details={"error": str(e), "operation": "salesforce_auth"}
            )
            raise
    
    def _get_config_secret(self, config_key: str, env_var: str) -> Optional[str]:
        """Get secret from environment or config - preferring environment"""
        import os
        
        # Try environment first
        value = os.environ.get(env_var)
        if value:
            return value
        
        # Fall back to config
        return self.config.get(config_key)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def _map_lead_to_salesforce(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Map lead data to Salesforce Lead object fields"""
        mapping = self.config.get('field_mapping', {})
        
        # Default Salesforce field mapping
        sf_lead = {
            'FirstName': lead.get('first_name', ''),
            'LastName': lead.get('last_name', ''),
            'Email': lead.get('email', ''),
            'Phone': lead.get('phone', ''),
            'Company': lead.get('company', ''),
            'LeadSource': lead.get('source', 'Web'),
        }
        
        # Apply custom mapping
        for custom_field, sf_field in mapping.items():
            if custom_field in lead:
                sf_lead[sf_field] = lead[custom_field]
        
        return sf_lead
    
    def create_or_update_lead(self, lead: Dict[str, Any]) -> bool:
        """
        Create or update a lead in Salesforce
        
        Args:
            lead: Lead data dictionary
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.access_token:
                self.logger.error("Not authenticated with Salesforce")
                return False
            
            sf_lead = self._map_lead_to_salesforce(lead)
            
            # Check if lead exists by email
            existing_lead = self._find_lead_by_email(lead.get('email'))
            
            if existing_lead:
                # Update existing lead
                lead_id = existing_lead['Id']
                url = f"{self.base_url}/services/data/v57.0/sobjects/Lead/{lead_id}"
                response = requests.patch(
                    url,
                    json=sf_lead,
                    headers=self._get_headers(),
                    timeout=10
                )
                response.raise_for_status()
                lead['crm_id'] = lead_id
                self.logger.info(f"Updated Salesforce lead {lead_id}")
            else:
                # Create new lead
                url = f"{self.base_url}/services/data/v57.0/sobjects/Lead"
                response = requests.post(
                    url,
                    json=sf_lead,
                    headers=self._get_headers(),
                    timeout=10
                )
                response.raise_for_status()
                lead_id = response.json()['id']
                lead['crm_id'] = lead_id
                self.logger.info(f"Created Salesforce lead {lead_id}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error creating/updating Salesforce lead: {e}")
            return False
    
    def _find_lead_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find lead by email address"""
        try:
            url = f"{self.base_url}/services/data/v57.0/sobjects/Lead"
            soql = f"SELECT Id, Email FROM Lead WHERE Email = '{email}' LIMIT 1"
            
            response = requests.get(
                url,
                params={'q': soql},
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            records = response.json().get('records', [])
            return records[0] if records else None
        
        except Exception as e:
            self.logger.error(f"Error finding Salesforce lead by email: {e}")
            return None
    
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """
        Get lead details from Salesforce
        
        Args:
            lead_id: Salesforce lead ID
        
        Returns:
            Lead data or None if not found
        """
        try:
            url = f"{self.base_url}/services/data/v57.0/sobjects/Lead/{lead_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            self.logger.error(f"Error fetching Salesforce lead: {e}")
            return None
    
    def list_leads(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        List leads from Salesforce
        
        Args:
            filters: Optional filters (source, email, etc.)
        
        Returns:
            List of leads
        """
        try:
            soql = "SELECT Id, FirstName, LastName, Email, Phone, Company, LeadSource FROM Lead"
            
            # Add filters
            where_clauses = []
            if filters:
                if 'email' in filters:
                    where_clauses.append(f"Email = '{filters['email']}'")
                if 'source' in filters:
                    where_clauses.append(f"LeadSource = '{filters['source']}'")
            
            if where_clauses:
                soql += " WHERE " + " AND ".join(where_clauses)
            
            soql += " LIMIT 100"
            
            url = f"{self.base_url}/services/data/v57.0/sobjects/Lead"
            response = requests.get(
                url,
                params={'q': soql},
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            return response.json().get('records', [])
        
        except Exception as e:
            self.logger.error(f"Error listing Salesforce leads: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test Salesforce connection"""
        try:
            url = f"{self.base_url}/services/data/v57.0/sobjects/Lead"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            self.logger.info("Salesforce connection test successful")
            return True
        
        except Exception as e:
            self.logger.error(f"Salesforce connection test failed: {e}")
            return False
