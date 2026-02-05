"""
Workflow Runner for Automation Orchestrator
Executes configured workflows for lead management
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
import time
from automation_orchestrator.audit import get_audit_logger


class WorkflowRunner:
    """Manages and executes automation workflows"""
    
    def __init__(self, config: Dict[str, Any], lead_ingest, crm_connector, email_followup):
        self.audit = get_audit_logger()
        """
        Initialize workflow runner
        
        Args:
            config: Workflow configuration dictionary
            lead_ingest: Lead ingestion module instance
            crm_connector: CRM connector instance
            email_followup: Email follow-up system instance
        """
        self.config = config
        self.lead_ingest = lead_ingest
        self.crm_connector = crm_connector
        self.email_followup = email_followup
        self.running = False
        self.workflows = config.get('workflows', [])
        self.logger = logging.getLogger(__name__)
        
        # Track workflow execution status
        self.execution_status = {}
        
    def start(self):
        """Start workflow execution"""
        if self.running:
            self.logger.warning("Workflow runner already running")
            return
            
        self.running = True
        self.logger.info(f"Starting workflow runner with {len(self.workflows)} workflows")
        
        # Start workflow processing thread
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop workflow execution"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=5)
        self.logger.info("Workflow runner stopped")
    
    def process_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> bool:
        """
        Process a lead (API endpoint handler)
        
        Args:
            lead_id: Lead ID
            lead_data: Lead data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            lead = lead_data.copy()
            lead['id'] = lead_id
            
            # Find and execute qualifying workflow
            for workflow in self.workflows:
                if workflow.get('enabled', True):
                    self._process_lead(lead, workflow)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error processing lead {lead_id}: {e}", exc_info=True)
            return False
    
    def execute_workflow(self, workflow_id: str, execution_id: str, 
                         lead_data: Optional[Dict[str, Any]] = None,
                         context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute a specific workflow (API endpoint handler)
        
        Args:
            workflow_id: Workflow ID
            execution_id: Execution ID (for tracking)
            lead_data: Optional lead data for the workflow
            context: Optional custom context data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find workflow
            workflow = None
            for wf in self.workflows:
                if wf.get('id') == workflow_id or wf.get('name') == workflow_id:
                    workflow = wf
                    break
            
            if not workflow:
                self.logger.error(f"Workflow not found: {workflow_id}")
                return False
            
            # Execute workflow
            if lead_data:
                lead = lead_data.copy()
                lead['id'] = execution_id
                if context:
                    lead['context'] = context
                self._process_lead(lead, workflow)
            
            # Track execution
            self.execution_status[workflow_id] = {
                'execution_id': execution_id,
                'status': 'completed',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.audit.log_event(
                event_type="workflow_completed",
                details={
                    "workflow_id": workflow_id,
                    "execution_id": execution_id
                }
            )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow_id}: {e}", exc_info=True)
            self.execution_status[workflow_id] = {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            return False
    
    def get_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get workflow execution status
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Status information
        """
        if workflow_id in self.execution_status:
            return self.execution_status[workflow_id]
        
        return {
            'workflow_id': workflow_id,
            'status': 'idle',
            'execution_count': 0
        }
        
    def _run_loop(self):
        """Main workflow processing loop"""
        while self.running:
            try:
                for workflow in self.workflows:
                    if not self.running:
                        break
                    self._process_workflow(workflow)
            except Exception as e:
                self.logger.error(f"Error in workflow loop: {e}", exc_info=True)
            
            # Poll interval
            time.sleep(self.config.get('poll_interval', 60))
    
    def _process_workflow(self, workflow: Dict[str, Any]):
        """
        Process a single workflow
        
        Args:
            workflow: Workflow configuration
        """
        workflow_name = workflow.get('name', 'unnamed')
        self.logger.debug(f"Processing workflow: {workflow_name}")
        
        try:
            # Step 1: Ingest leads
            leads = self._ingest_leads(workflow)
            
            if not leads:
                return
                
            self.logger.info(f"Ingested {len(leads)} leads for workflow: {workflow_name}")
            
            # Step 2: Process each lead
            for lead in leads:
                try:
                    self._process_lead(lead, workflow)
                except Exception as e:
                    self.logger.error(f"Error processing lead {lead.get('id')}: {e}", exc_info=True)
                    
        except Exception as e:
            self.logger.error(f"Error in workflow {workflow_name}: {e}", exc_info=True)
    
    def _ingest_leads(self, workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ingest leads from configured sources
        
        Args:
            workflow: Workflow configuration
            
        Returns:
            List of lead dictionaries
        """
        leads = []
        sources = workflow.get('sources', [])
        
        for source in sources:
            source_type = source.get('type')
            
            if source_type == 'web_form':
                # Fetch leads from web form endpoint
                form_leads = self.lead_ingest.fetch_web_form(source)
                leads.extend(form_leads)
                
            elif source_type == 'email':
                # Fetch leads from email
                email_leads = self.lead_ingest.fetch_email(source)
                leads.extend(email_leads)
                
            else:
                self.logger.warning(f"Unknown source type: {source_type}")
        
        return leads
    
    def _process_lead(self, lead: Dict[str, Any], workflow: Dict[str, Any]):
        """
        Process a single lead through the workflow
        
        Args:
            lead: Lead data
            workflow: Workflow configuration
        """
        lead_id = lead.get('id', 'unknown')
        
        # Step 1: Qualify lead
        qualified = self._qualify_lead(lead, workflow.get('qualification_rules', []))
        lead['qualified'] = qualified
        lead['qualification_timestamp'] = datetime.utcnow().isoformat()
        
        # Step 2: Route lead
        destination = self._route_lead(lead, workflow.get('routing_rules', []))
        lead['routed_to'] = destination
        
        # Step 3: Store in CRM
        self.crm_connector.create_or_update_lead(lead)
        self.logger.info(f"Lead {lead_id} stored in CRM, routed to: {destination}")
        
        # Step 4: Trigger follow-up sequence
        if workflow.get('enable_follow_up', True):
            self._trigger_follow_up(lead, workflow)
    
    def _qualify_lead(self, lead: Dict[str, Any], rules: List[Dict[str, Any]]) -> bool:
        """
        Qualify lead based on rules
        
        Args:
            lead: Lead data
            rules: List of qualification rules
            
        Returns:
            True if lead qualifies, False otherwise
        """
        if not rules:
            # No rules means all leads qualify
            return True
        
        for rule in rules:
            rule_type = rule.get('type')
            
            if rule_type == 'field_contains':
                field = rule.get('field')
                value = rule.get('value')
                if value.lower() in str(lead.get(field, '')).lower():
                    return True
                    
            elif rule_type == 'field_equals':
                field = rule.get('field')
                value = rule.get('value')
                if str(lead.get(field)) == str(value):
                    return True
                    
            elif rule_type == 'field_exists':
                field = rule.get('field')
                if field in lead and lead[field]:
                    return True
                    
            elif rule_type == 'field_regex':
                import re
                field = rule.get('field')
                pattern = rule.get('pattern')
                if re.search(pattern, str(lead.get(field, ''))):
                    return True
        
        return False
    
    def _route_lead(self, lead: Dict[str, Any], rules: List[Dict[str, Any]]) -> str:
        """
        Route lead based on routing rules
        
        Args:
            lead: Lead data
            rules: List of routing rules
            
        Returns:
            Destination identifier
        """
        for rule in rules:
            condition = rule.get('condition', {})
            
            # Evaluate condition
            if self._evaluate_condition(lead, condition):
                return rule.get('destination', 'default')
        
        # Default routing
        return rules[0].get('destination', 'default') if rules else 'default'
    
    def _evaluate_condition(self, lead: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """
        Evaluate a routing condition
        
        Args:
            lead: Lead data
            condition: Condition to evaluate
            
        Returns:
            True if condition is met, False otherwise
        """
        if not condition:
            return True
        
        condition_type = condition.get('type')
        field = condition.get('field')
        value = condition.get('value')
        
        if condition_type == 'equals':
            return str(lead.get(field)) == str(value)
        elif condition_type == 'contains':
            return value.lower() in str(lead.get(field, '')).lower()
        elif condition_type == 'greater_than':
            return float(lead.get(field, 0)) > float(value)
        elif condition_type == 'less_than':
            return float(lead.get(field, 0)) < float(value)
        
        return False
    
    def _trigger_follow_up(self, lead: Dict[str, Any], workflow: Dict[str, Any]):
        """
        Trigger email follow-up sequence
        
        Args:
            lead: Lead data
            workflow: Workflow configuration
        """
        follow_up_config = workflow.get('follow_up_sequence', {})
        
        if not follow_up_config:
            return
        
        self.email_followup.schedule_sequence(
            lead_id=lead.get('id'),
            lead_email=lead.get('email'),
            sequence_name=follow_up_config.get('sequence_name'),
            templates=follow_up_config.get('templates', []),
            delays=follow_up_config.get('delays', [])
        )
        
        self.logger.info(f"Scheduled follow-up for lead: {lead.get('id')}")
