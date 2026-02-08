<<<<<<< HEAD
# Python
import os
import logging
import uuid
from locust import HttpUser, task, between
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class ApiUser(HttpUser):
    wait_time = between(1, 3)
    host = "automation-orchestrator-api.herokuapp.com"
    timeout_duration = 90  # seconds

    def on_start(self):
        # Set debug mode from environment variable
        self.ENABLE_LOGGING = os.getenv('ENABLE_LOGGING', 'True') == 'True'
        # Set up logging
        if self.ENABLE_LOGGING:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)
        # No authentication required as per HTTP Request File

    @task
    def run_scenario(self):
        self.get()

    def get(self):
        """
        GET /
        Content-Type: application/json
        """
        url = "/"
        headers = {
            "Accept": "application/json"
        }
        if self.ENABLE_LOGGING:
            print("[Locust] Sending GET / request")

        with self.client.get(
            url=url,
            headers=headers,
            name="GET /",
            catch_response=True,
            timeout=self.timeout_duration
        ) as response:
            if response.status_code in [200]:
                response.success()
                if self.ENABLE_LOGGING:
                    print("[Locust] GET / succeeded")
            else:
                msg = f"GET / failed with status {response.status_code}, response: {response.text}"
                response.failure(msg)
                if self.ENABLE_LOGGING:
                    logging.error(msg)
                    logging.error(f"Request URL: {response.url}")
                    logging.error(f"Request Headers: {headers}")

    def on_stop(self):
        # No resources to clean up for this scenario
        pass

# To run:
# locust -f locustfile.py -u 10 -r 2 --run-time 1m
=======
"""
Locust stress testing configuration for Automation Orchestrator
Run with: locust -f locustfile.py --host http://localhost:8000
"""

from locust import HttpUser, task, between, events
from datetime import datetime
import json
import time


class AutomationOrchestratorUser(HttpUser):
    """Simulates realistic user behavior on the Automation Orchestrator"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    token = None  # Store JWT token after login
    
    def on_start(self):
        """Called when a simulated user starts"""
        self.login()
    
    def login(self):
        """Authenticate and get JWT token"""
        try:
            response = self.client.post("/api/auth/login", json={
                "username": "admin",
                "password": "admin123"
            }, name="/api/auth/login")
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Login successful, token obtained")
            else:
                print(f"[LOGIN FAILED] Status: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            print(f"[LOGIN ERROR] {str(e)}")
    
    def get_headers(self):
        """Return headers with Bearer token for authenticated requests"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    # ==================== HEALTH CHECKS ====================
    
    @task(5)
    def health_check_basic(self):
        """Basic health check - 5% of traffic"""
        self.client.get("/health", name="/health")
    
    @task(2)
    def health_check_detailed(self):
        """Detailed health check - 2% of traffic"""
        self.client.get("/api/status", name="/health/detailed")
    
    @task(1)
    def metrics_endpoint(self):
        """Prometheus metrics - 1% of traffic"""
        self.client.get("/api/crm/status", name="/metrics")
    
    # ==================== AUTHENTICATION ====================
    
    @task(3)
    def get_current_user(self):
        """Get current user info - 3% of traffic"""
        headers = self.get_headers()
        self.client.get("/api/auth/me", headers=headers, name="/api/auth/me")
    
    @task(1)
    def list_api_keys(self):
        """List user's API keys - 1% of traffic"""
        headers = self.get_headers()
        self.client.get("/api/auth/keys", headers=headers, name="/api/auth/keys")
    
    # ==================== WORKFLOW ENDPOINTS ====================
    
    @task(10)
    def trigger_workflows(self):
        """Trigger workflows - 10% of traffic (most common)"""
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"
        self.client.post("/api/workflows/trigger", json={
            "workflow_id": "workflow-1",
            "lead_data": {"email": "test@example.com"}
        }, headers=headers, name="/api/workflows")
    
    @task(5)
    def get_workflow_status(self):
        """Get specific workflow status - 5% of traffic"""
        headers = self.get_headers()
        self.client.get("/api/workflows/workflow-1/status", headers=headers, name="/api/workflows/{id}/status")
    
    @task(3)
    def trigger_workflow(self):
        """Trigger workflow - 3% of traffic"""
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"
        
        workflow_data = {
            "workflow_id": "workflow-1",
            "lead_data": {
                "email": "user@example.com",
                "phone": "+1-555-0100",
                "company": "Test Corp",
                "source": "stress_test"
            },
            "actions": [
                {
                    "type": "email",
                    "config": {
                        "to": "test@example.com",
                        "subject": "Stress Test",
                        "body": "Testing..."
                    }
                }
            ]
        }
        
        self.client.post(
            "/api/workflows",
            json=workflow_data,
            headers=headers,
            name="/api/workflows [POST]"
        )
    
    @task(2)
    def update_workflow(self):
        """Update workflow - 2% of traffic"""
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"
        
        update_data = {
            "name": f"Updated Workflow {int(time.time())}",
            "enabled": True
        }
        
        self.client.put(
            "/api/workflows/1",
            json=update_data,
            headers=headers,
            name="/api/workflows/{id} [PUT]"
        )
    
    @task(4)
    def execute_workflow(self):
        """Execute a workflow - 4% of traffic"""
        headers = self.get_headers()
        
        self.client.post(
            "/api/workflows/1/execute",
            headers=headers,
            name="/api/workflows/{id}/execute"
        )
    
    # ==================== LEAD MANAGEMENT ====================
    
    @task(8)
    def get_leads(self):
        """Get leads - 8% of traffic"""
        headers = self.get_headers()
        self.client.get(
            "/api/leads",
            headers=headers,
            name="/api/leads"
        )
    
    @task(3)
    def create_lead(self):
        """Create new lead - 3% of traffic"""
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"
        
        lead_data = {
            "email": f"lead-{int(time.time())}@example.com",
            "first_name": "Stress",
            "last_name": "Test",
            "company": "Test Corp",
            "phone": "+1234567890"
        }
        
        self.client.post(
            "/api/leads",
            json=lead_data,
            headers=headers,
            name="/api/leads [POST]"
        )
    
    @task(2)
    def get_lead_details(self):
        """Get lead details - 2% of traffic"""
        headers = self.get_headers()
        self.client.get(
            "/api/leads/1",
            headers=headers,
            name="/api/leads/{id}"
        )
    
    # ==================== CAMPAIGN ENDPOINTS ====================
    
    @task(6)
    def get_campaigns(self):
        """Get campaigns - 6% of traffic"""
        headers = self.get_headers()
        self.client.get(
            "/api/campaigns",
            headers=headers,
            name="/api/campaigns"
        )
    
    @task(2)
    def get_campaign_metrics(self):
        """Get campaign metrics - 2% of traffic"""
        headers = self.get_headers()
        self.client.get(
            "/api/campaigns/1/metrics",
            headers=headers,
            name="/api/campaigns/{id}/metrics"
        )
    
    # ==================== ERROR SCENARIOS ====================
    
    @task(1)
    def trigger_error_404(self):
        """Intentional 404 - 1% of traffic (test error handling)"""
        headers = self.get_headers()
        self.client.get(
            "/api/nonexistent",
            headers=headers,
            name="/api/nonexistent [404]"
        )
    
    # ==================== DOCUMENTATION ====================
    
    @task(2)
    def get_api_docs(self):
        """Get API documentation - 2% of traffic"""
        self.client.get("/docs", name="/docs")
    
    @task(1)
    def get_openapi_schema(self):
        """Get OpenAPI schema - 1% of traffic"""
        self.client.get("/openapi.json", name="/openapi.json")


# ==================== EVENT HANDLERS ====================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    print("\n" + "="*60)
    print(f"[START] Stress test started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[TARGET] {environment.host}")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    print("\n" + "="*60)
    print(f"[STOP] Stress test ended at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Print summary statistics
    print_summary(environment)


def print_summary(environment):
    """Print test summary statistics"""
    stats = environment.stats
    
    print("\n📊 TEST SUMMARY STATISTICS\n")
    print(f"{'Endpoint':<40} {'Reqs':>8} {'Avg (ms)':>10} {'Min (ms)':>10} {'Max (ms)':>10} {'Fail':>8}")
    print("-" * 90)
    
    for key in sorted(stats.entries.keys()):
        entry = stats.entries[key]
        print(
            f"{str(entry.name):<40} "
            f"{entry.num_requests:>8} "
            f"{entry.avg_response_time:>10.0f} "
            f"{entry.min_response_time:>10.0f} "
            f"{entry.max_response_time:>10.0f} "
            f"{entry.num_failures:>8}"
        )
    
    print("-" * 90)
    print(f"\n📈 OVERALL STATS:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Total Failures: {stats.total.num_failures}")
    print(f"  Failure Rate: {(stats.total.num_failures / stats.total.num_requests * 100):.2f}%")
    print(f"  Average Response Time: {stats.total.avg_response_time:.0f}ms")
    print(f"  Min Response Time: {stats.total.min_response_time:.0f}ms")
    print(f"  Max Response Time: {stats.total.max_response_time:.0f}ms")
    print(f"  95th Percentile: {stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"  99th Percentile: {stats.total.get_response_time_percentile(0.99):.0f}ms")
    print()


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Called for each request"""
    status = "✓" if exception is None else "✗"
    status_code = exception.__class__.__name__ if exception else getattr(response, 'status_code', 'N/A')
    
    # Print high-latency requests
    if response_time > 1000:
        print(f"[SLOW] {status} {name:<40} {response_time:>6.0f}ms {status_code}")
    
    # Print errors
    if exception:
        print(f"[ERROR] {status} {name:<40} {response_time:>6.0f}ms {exception.__class__.__name__}")
>>>>>>> b827fdb4458c7573c3e10cfdd001559a627ed4e1
