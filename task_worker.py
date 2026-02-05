"""
Background task worker for Automation Orchestrator
Processes tasks from Redis queue
Run with: python task_worker.py
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Callable
from datetime import datetime
import time

from src.automation_orchestrator.redis_queue import get_queue, TaskStatus
from src.automation_orchestrator.config import load_config
from src.automation_orchestrator.crm import GenericAPIConnector
from src.automation_orchestrator.email_followup import EmailFollowup
from src.automation_orchestrator.lead_ingest import LeadIngest
from src.automation_orchestrator.workflows import WorkflowRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskWorker:
    """Background task worker that processes Redis queue tasks"""
    
    def __init__(self, queue_name: str = "default", worker_id: str = "worker-1"):
        """
        Initialize task worker
        
        Args:
            queue_name: Name of queue to process
            worker_id: Identifier for this worker
        """
        self.queue_name = queue_name
        self.worker_id = worker_id
        self.running = False
        self.tasks_processed = 0
        self.tasks_failed = 0
        
        # Initialize components from config
        self.cfg = load_config()
        self.queue = get_queue(self.cfg.get("redis", {}))
        
        # Initialize handlers
        self.crm_connector = GenericAPIConnector(self.cfg.get("crm", {}))
        self.email_followup = EmailFollowup(self.cfg.get("email", {}))
        self.lead_ingest = LeadIngest(self.cfg.get("lead_ingest", {}))
        self.workflow_runner = WorkflowRunner(self.cfg.get("workflows", {}))
        
        # Task handlers registry
        self.handlers: Dict[str, Callable] = {
            "crm_update": self.handle_crm_update,
            "email_send": self.handle_email_send,
            "workflow_execute": self.handle_workflow_execute,
            "lead_process": self.handle_lead_process,
        }
        
        logger.info(f"Worker {self.worker_id} initialized")
    
    async def handle_crm_update(self, task_data: Dict[str, Any]) -> bool:
        """
        Handle CRM update task
        
        Args:
            task_data: Task data containing lead_id and lead_data
        
        Returns:
            True if successful
        """
        try:
            lead_id = task_data.get("lead_id")
            lead_data = task_data.get("lead_data")
            
            logger.info(f"Processing CRM update for lead {lead_id}")
            
            # Update in CRM via API connector
            result = self.crm_connector.update_lead(lead_id, lead_data)
            
            logger.info(f"CRM update completed for lead {lead_id}: {result}")
            return True
        except Exception as e:
            logger.error(f"Error in CRM update: {e}")
            return False
    
    async def handle_email_send(self, task_data: Dict[str, Any]) -> bool:
        """
        Handle email send task
        
        Args:
            task_data: Task data containing email_to, subject, body
        
        Returns:
            True if successful
        """
        try:
            email_to = task_data.get("email_to")
            subject = task_data.get("subject")
            body = task_data.get("body")
            
            logger.info(f"Processing email send to {email_to}")
            
            # Send email
            result = self.email_followup.send_email(email_to, subject, body)
            
            logger.info(f"Email sent to {email_to}: {result}")
            return True
        except Exception as e:
            logger.error(f"Error in email send: {e}")
            return False
    
    async def handle_workflow_execute(self, task_data: Dict[str, Any]) -> bool:
        """
        Handle workflow execution task
        
        Args:
            task_data: Task data containing workflow_id and params
        
        Returns:
            True if successful
        """
        try:
            workflow_id = task_data.get("workflow_id")
            params = task_data.get("params", {})
            
            logger.info(f"Processing workflow execution: {workflow_id}")
            
            # Execute workflow
            result = self.workflow_runner.execute(workflow_id, params)
            
            logger.info(f"Workflow execution completed: {workflow_id}")
            return True
        except Exception as e:
            logger.error(f"Error in workflow execution: {e}")
            return False
    
    async def handle_lead_process(self, task_data: Dict[str, Any]) -> bool:
        """
        Handle lead processing task
        
        Args:
            task_data: Task data containing lead data
        
        Returns:
            True if successful
        """
        try:
            lead_data = task_data.get("lead_data")
            
            logger.info(f"Processing lead: {lead_data.get('email')}")
            
            # Process lead through ingestion pipeline
            result = self.lead_ingest.process(lead_data)
            
            logger.info(f"Lead processing completed: {lead_data.get('email')}")
            return True
        except Exception as e:
            logger.error(f"Error in lead processing: {e}")
            return False
    
    async def process_task(self, task: Dict[str, Any]) -> bool:
        """
        Process a single task
        
        Args:
            task: Task object from queue
        
        Returns:
            True if successful
        """
        task_id = task.get("id")
        task_type = task.get("type")
        task_data = task.get("data")
        
        try:
            logger.info(f"[{self.worker_id}] Processing task {task_id}: {task_type}")
            
            # Get handler for task type
            handler = self.handlers.get(task_type)
            if not handler:
                logger.error(f"No handler registered for task type: {task_type}")
                self.queue.mark_failed(task_id, f"No handler for {task_type}", retry=False)
                return False
            
            # Execute handler
            start_time = time.time()
            success = await handler(task_data)
            elapsed = time.time() - start_time
            
            if success:
                self.queue.mark_complete(task_id)
                self.tasks_processed += 1
                logger.info(f"Task {task_id} completed successfully ({elapsed:.2f}s)")
                return True
            else:
                self.queue.mark_failed(task_id, "Handler returned False", retry=True)
                self.tasks_failed += 1
                logger.error(f"Task {task_id} failed")
                return False
        
        except Exception as e:
            logger.error(f"Exception processing task {task_id}: {e}")
            self.queue.mark_failed(task_id, str(e), retry=True)
            self.tasks_failed += 1
            return False
    
    async def run(self, poll_interval: int = 5):
        """
        Run worker indefinitely
        
        Args:
            poll_interval: Seconds between queue checks when empty
        """
        self.running = True
        logger.info(f"[{self.worker_id}] Worker started, polling queue '{self.queue_name}'")
        
        try:
            while self.running:
                # Attempt to get task from queue (non-blocking)
                task = self.queue.dequeue(queue_name=self.queue_name, timeout=0)
                
                if task:
                    # Process task
                    await self.process_task(task)
                else:
                    # Queue empty, wait before checking again
                    await asyncio.sleep(poll_interval)
        
        except KeyboardInterrupt:
            logger.info(f"[{self.worker_id}] Interrupted by user")
        except Exception as e:
            logger.error(f"[{self.worker_id}] Fatal error: {e}")
        finally:
            self.running = False
            logger.info(f"[{self.worker_id}] Worker stopped")
            logger.info(f"[{self.worker_id}] Stats: {self.tasks_processed} processed, {self.tasks_failed} failed")
    
    def stop(self):
        """Stop the worker"""
        logger.info(f"[{self.worker_id}] Stop signal received")
        self.running = False


async def main():
    """Main entry point for worker"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Background task worker")
    parser.add_argument("--queue", default="default", help="Queue name to process")
    parser.add_argument("--worker-id", default="worker-1", help="Worker ID")
    parser.add_argument("--poll-interval", type=int, default=5, help="Poll interval in seconds")
    
    args = parser.parse_args()
    
    # Create worker
    worker = TaskWorker(queue_name=args.queue, worker_id=args.worker_id)
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Signal received, shutting down...")
        worker.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run worker
    await worker.run(poll_interval=args.poll_interval)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
