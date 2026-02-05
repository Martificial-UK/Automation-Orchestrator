"""
Lead Ingestion Module
Handles lead capture from web forms and email
"""
import logging
import requests
import imaplib
import email
from email.header import decode_header
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re
import hashlib
from automation_orchestrator.audit import get_audit_logger
from automation_orchestrator.security import (
    InputValidator, EmailValidator, PIIManager, OutputSanitizer
)


class LeadIngest:
    """Handles lead ingestion from multiple sources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.audit = get_audit_logger()
        """
        Initialize lead ingest module
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.processed_ids = set()  # Track processed leads to avoid duplicates
        
    def fetch_web_form(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch leads from web form API endpoint
        
        Args:
            source_config: Web form source configuration
            
        Returns:
            List of lead dictionaries
        """
        endpoint = source_config.get('endpoint')
        method = source_config.get('method', 'GET').upper()
        headers = source_config.get('headers', {})
        auth = source_config.get('auth', {})
        
        if not endpoint:
            self.logger.error("No endpoint specified for web form source")
            return []
        
        try:
            self.logger.info(f"Fetching leads from web form: {endpoint}")
            
            # Prepare authentication
            auth_tuple = None
            if auth.get('type') == 'basic':
                auth_tuple = (auth.get('username'), auth.get('password'))
            
            # Make request
            if method == 'GET':
                response = requests.get(endpoint, headers=headers, auth=auth_tuple, timeout=30)
            elif method == 'POST':
                response = requests.post(endpoint, headers=headers, auth=auth_tuple, 
                                       json=source_config.get('payload', {}), timeout=30)
            else:
                self.logger.error(f"Unsupported HTTP method: {method}")
                return []
            
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            leads = self._parse_web_form_response(data, source_config)
            
            # Filter out already processed leads
            new_leads = [lead for lead in leads if lead.get('id') not in self.processed_ids]
            
            # Mark as processed
            for lead in new_leads:
                self.processed_ids.add(lead.get('id'))
            
            self.logger.info(f"Fetched {len(new_leads)} new leads from web form")
            return new_leads
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching from web form: {e}", exc_info=True)
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in web form fetch: {e}", exc_info=True)
            return []
    
    def _parse_web_form_response(self, data: Any, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse web form API response into lead objects
        
        Args:
            data: Response data
            source_config: Source configuration
            
        Returns:
            List of lead dictionaries
        """
        leads = []
        
        # Handle different response structures
        response_type = source_config.get('response_type', 'list')
        data_path = source_config.get('data_path', '')
        
        # Navigate to data if path specified
        if data_path:
            for key in data_path.split('.'):
                data = data.get(key, data)
        
        # Convert to list if single object
        if response_type == 'object' or isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            self.logger.error(f"Unexpected response format: {type(data)}")
            return []
        
        # Map fields
        field_mapping = source_config.get('field_mapping', {})
        
        for item in data:
            # SECURITY: Validate item is a dictionary
            if not isinstance(item, dict):
                self.logger.warning(f"Skipping non-dict item: {type(item)}")
                continue
            
            lead = {
                'id': self._generate_lead_id(item, source_config),
                'source': 'web_form',
                'source_name': source_config.get('name', 'unknown'),
                'ingested_at': datetime.utcnow().isoformat()
            }
            
            # Apply field mapping with validation
            if field_mapping:
                for dest_field, source_field in field_mapping.items():
                    value = item.get(source_field, '')
                    # Validate specific fields
                    if dest_field == 'email' and value:
                        try:
                            value = EmailValidator.validate_email(value)
                        except ValueError as e:
                            self.logger.warning(f"Invalid email in lead: {e}")
                            value = None
                    lead[dest_field] = value
            else:
                # No mapping - use all fields but validate
                for key, value in item.items():
                    if key == 'email' and value:
                        try:
                            value = EmailValidator.validate_email(value)
                        except ValueError:
                            value = None
                    lead[key] = value
            
            leads.append(lead)
        
        return leads
    
    def fetch_email(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch leads from email
        
        Args:
            source_config: Email source configuration
            
        Returns:
            List of lead dictionaries
        """
        server = source_config.get('server')
        username = source_config.get('username')
        password = source_config.get('password')
        folder = source_config.get('folder', 'INBOX')
        
        if not all([server, username, password]):
            self.logger.error("Missing email configuration")
            return []
        
        try:
            self.logger.info(f"Fetching leads from email: {username}@{server}")
            
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(server)
            mail.login(username, password)
            mail.select(folder)
            
            # Search for unread emails
            search_criteria = source_config.get('search_criteria', 'UNSEEN')
            status, message_ids = mail.search(None, search_criteria)
            
            if status != 'OK':
                self.logger.warning("No new emails found")
                mail.logout()
                return []
            
            leads = []
            
            for msg_id in message_ids[0].split():
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    lead = self._parse_email_to_lead(email_message, source_config)
                    
                    if lead and lead.get('id') not in self.processed_ids:
                        leads.append(lead)
                        self.processed_ids.add(lead.get('id'))
                        
                        # Mark as read if configured
                        if source_config.get('mark_as_read', True):
                            mail.store(msg_id, '+FLAGS', '\\Seen')
                
                except Exception as e:
                    self.logger.error(f"Error parsing email {msg_id}: {e}")
            
            mail.logout()
            
            self.logger.info(f"Fetched {len(leads)} new leads from email")
            return leads
            
        except imaplib.IMAP4.error as e:
            self.logger.error(f"IMAP error: {e}", exc_info=True)
            return []
        except Exception as e:
            self.logger.error(f"Error fetching from email: {e}", exc_info=True)
            return []
    
    def _parse_email_to_lead(self, email_message, source_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse email message to lead object
        
        Args:
            email_message: Email message object
            source_config: Source configuration
            
        Returns:
            Lead dictionary or None
        """
        try:
            # Extract basic info
            subject = self._decode_header(email_message.get('Subject', ''))
            from_email = email.utils.parseaddr(email_message.get('From', ''))[1]
            from_name = email.utils.parseaddr(email_message.get('From', ''))[0]
            date_str = email_message.get('Date', '')
            
            # Extract body
            body = ''
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Parse structured data from email body
            parsed_data = self._extract_fields_from_body(body, source_config)
            
            lead = {
                'id': f"email_{from_email}_{date_str}",
                'source': 'email',
                'source_name': source_config.get('name', 'unknown'),
                'email': from_email,
                'name': from_name or parsed_data.get('name', ''),
                'subject': subject,
                'message': body,
                'ingested_at': datetime.utcnow().isoformat()
            }
            
            # Merge parsed data
            lead.update(parsed_data)
            
            return lead
            
        except Exception as e:
            self.logger.error(f"Error parsing email to lead: {e}", exc_info=True)
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ''
        
        decoded_parts = decode_header(header)
        decoded_str = ''
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_str += str(part)
        
        return decoded_str
    
    def _extract_fields_from_body(self, body: str, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured fields from email body using patterns
        
        Args:
            body: Email body text
            source_config: Source configuration with extraction patterns
            
        Returns:
            Dictionary of extracted fields
        """
        fields = {}
        patterns = source_config.get('extraction_patterns', {})
        
        for field_name, pattern in patterns.items():
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                fields[field_name] = match.group(1).strip()
        
        return fields
    
    def _generate_lead_id(self, data: Dict[str, Any], source_config: Dict[str, Any]) -> str:
        """
        Generate unique lead ID with validation
        
        Args:
            data: Lead data
            source_config: Source configuration
            
        Returns:
            Unique lead ID
        """
        id_field = source_config.get('id_field', 'id')
        
        if id_field in data:
            lead_id = str(data[id_field])
            try:
                # SECURITY: Validate lead ID format
                return InputValidator.validate_lead_id(lead_id)
            except ValueError:
                self.logger.warning(f"Invalid lead ID format, generating new: {lead_id}")
        
        # Generate ID from email or timestamp - secure approach using hash
        email_val = data.get('email', '')
        source_name = source_config.get('name', 'web')
        timestamp = int(datetime.utcnow().timestamp())
        
        # Create safe ID using hashing
        if email_val:
            try:
                EmailValidator.validate_email(email_val)
                # Use first 3 chars of hash for uniqueness
                unique_part = hashlib.sha256(f"{email_val}_{timestamp}".encode()).hexdigest()[:8]
            except ValueError:
                unique_part = hashlib.sha256(str(timestamp).encode()).hexdigest()[:8]
        else:
            unique_part = hashlib.sha256(str(timestamp).encode()).hexdigest()[:8]
        
        return f"{source_name[:10]}_{unique_part}_{timestamp}"
