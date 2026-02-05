"""
Simplified Background task worker for Automation Orchestrator
Processes tasks from Redis/Fakeredis queue
Run with: python task_worker_simple.py
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any
from datetime import datetime
import time
import json

from src.automation_orchestrator.redis_queue import RedisQueue, TaskStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleTaskWorker:
    """Simplified background task worker that processes Redis queue tasks"""
    
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
        
        # Initialize queue
        self.queue = RedisQueue()
        
        logger.info(f"Worker {self.worker_id} initialized")
    
    async def handle_crm_update(self, task_data: Dict[str, Any]) -> bool:
        """Handle CRM update task"""
        try:
            lead_id = task_data.get("lead_id")
            lead_data = task_data.get("lead_data", {})
            
            logger.info(f"[WORKER] Processing CRM update for lead {lead_id}")
            
            # Simulate CRM update
            await asyncio.sleep(0.1)
            
            logger.info(f"[WORKER] CRM update completed for lead {lead_id}")
            return True
        except Exception as e:
            logger.error(f"[WORKER] Error in CRM update: {e}")
            return False
    
    async def handle_email_send(self, task_data: Dict[str, Any]) -> bool:
        """Handle email send task"""
        try:
            email_to = task_data.get("email_to", "unknown@example.com")
            subject = task_data.get("subject", "No subject")
            
            logger.info(f"[WORKER] Sending email to {email_to}: '{subject}'")
            
            # Simulate email send
            await asyncio.sleep(0.05)
            
            logger.info(f"[WORKER] Email sent to {email_to}")
            return True
        except Exception as e:
            logger.error(f"[WORKER] Error in email send: {e}")
            return False
    
    async def handle_workflow_execute(self, task_data: Dict[str, Any]) -> bool:
        """Handle workflow execution task"""
        try:
            workflow_name = task_data.get("workflow_name", "unknown")
            workflow_data = task_data.get("workflow_data", {})
            
            logger.info(f"[WORKER] Executing workflow: {workflow_name}")
            
            # Simulate workflow execution
            await asyncio.sleep(0.2)
            
            logger.info(f"[WORKER] Workflow {workflow_name} completed")
            return True
        except Exception as e:
            logger.error(f"[WORKER] Error in workflow execution: {e}")
            return False
    
    async def handle_lead_process(self, task_data: Dict[str, Any]) -> bool:
        """Handle lead processing task"""
        try:
            lead_id = task_data.get("lead_id", "unknown")
            operation = task_data.get("operation", "process")
            
            logger.info(f"[WORKER] Processing lead {lead_id} ({operation})")
            
            # Simulate lead processing
            await asyncio.sleep(0.15)
            
            logger.info(f"[WORKER] Lead {lead_id} processed")
            return True
        except Exception as e:
            logger.error(f"[WORKER] Error in lead processing: {e}")
            return False
    
    async def process_task(self, task_id: str, task_type: str, task_data: Dict[str, Any]) -> bool:
        """Process a single task"""
        task_key = f"{self.queue.queue_prefix}:task:{task_id}"
        
        try:
            # Update task status to PROCESSING
            if self.queue.client:
                self.queue.client.hset(task_key, mapping={
                    "status": TaskStatus.PROCESSING.value,
                    "worker_id": self.worker_id,
                    "started_at": datetime.utcnow().isoformat()
                })
            
            logger.info(f"[{self.worker_id}] Processing task {task_id[:8]} (type: {task_type})")
            
            # Route to appropriate handler
            handler_name = f"handle_{task_type}"
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                result = await handler(task_data)
            else:
                logger.warning(f"No handler for task type: {task_type}")
                result = False
            
            # Update task status
            if result:
                if self.queue.client:
                    self.queue.client.hset(task_key, mapping={
                        "status": TaskStatus.COMPLETED.value,
                        "completed_at": datetime.utcnow().isoformat()
                    })
                logger.info(f"[{self.worker_id}] Task {task_id[:8]} completed successfully")
                self.tasks_processed += 1
                return True
            else:
                if self.queue.client:
                    self.queue.client.hset(task_key, mapping={
                        "status": TaskStatus.FAILED.value,
                        "failed_at": datetime.utcnow().isoformat()
                    })
                logger.warning(f"[{self.worker_id}] Task {task_id[:8]} failed")
                self.tasks_failed += 1
                return False
        
        except Exception as e:
            logger.error(f"[{self.worker_id}] Error processing task {task_id}: {e}")
            if self.queue.client:
                try:
                    self.queue.client.hset(task_key, mapping={
                        "status": TaskStatus.FAILED.value,
                        "error": str(e)
                    })
                except:
                    pass
            self.tasks_failed += 1
            return False
    
    async def poll_queue(self):
        """Poll queue for tasks and process them"""
        queue_key = self.queue._get_queue_key(self.queue_name)
        
        logger.info(f"[{self.worker_id}] Starting to poll queue '{self.queue_name}'")
        
        while self.running:
            try:
                # Try to get a task from queue
                if self.queue.client:
                    task_data_str = self.queue.client.lpop(queue_key)
                    
                    if task_data_str:
                        try:
                            task_data = json.loads(task_data_str)
                            task_id = task_data.get("id")
                            task_type = task_data.get("type")
                            payload = task_data.get("data", {})
                            
                            # Process the task
                            await self.process_task(task_id, task_type, payload)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse task JSON: {task_data_str}")
                    else:
                        # No task available, sleep briefly
                        await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Error polling queue: {e}")
                await asyncio.sleep(1)
    
    async def run(self):
        """Start the worker"""
        self.running = True
        logger.info(f"Worker {self.worker_id} started successfully")
        logger.info(f"Waiting for tasks on queue: {self.queue_name}")
        
        try:
            await self.poll_queue()
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} shutting down")
            self.running = False
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {e}")
            self.running = False
        finally:
            logger.info(f"Worker {self.worker_id} stopped")
            logger.info(f"Tasks processed: {self.tasks_processed}, Failed: {self.tasks_failed}")
    
    def shutdown(self, signum, frame):
        """Handle shutdown signal"""
        logger.info(f"Shutdown signal received on {self.worker_id}")
        self.running = False


async def main():
    """Main entry point"""
    # Parse command line arguments
    worker_id = "worker-1"
    queue_name = "default"
    
    import argparse
    parser = argparse.ArgumentParser(description="Task worker for Automation Orchestrator")
    parser.add_argument("--worker-id", default=worker_id, help="Worker ID")
    parser.add_argument("--queue", default=queue_name, help="Queue name")
    parser.add_argument("--poll-interval", type=float, default=0.5, help="Poll interval in seconds")
    args = parser.parse_args()
    
    # Create and run worker
    worker = SimpleTaskWorker(queue_name=args.queue, worker_id=args.worker_id)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, worker.shutdown)
    signal.signal(signal.SIGTERM, worker.shutdown)
    
    # Run worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
