"""
Production Monitoring and Logging Module
Comprehensive monitoring, metrics collection, and event tracking for production systems
"""

import logging
import logging.handlers
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
from pathlib import Path
import os

# Configure JSON logging
class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easier parsing and aggregation"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1])
            }
        
        # Add custom fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_json_logging(log_dir: str = 'logs', level: int = logging.INFO) -> None:
    """Configure JSON logging for production"""
    
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler (INFO level for production)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Application log file (JSON format, all levels)
    app_log_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / 'application.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    app_log_handler.setLevel(logging.DEBUG)
    app_log_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(app_log_handler)
    
    # Error log file (JSON format, ERROR and CRITICAL only)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / 'error.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
    
    # Workflow events log file
    workflow_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / 'workflows.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    workflow_handler.setLevel(logging.INFO)
    workflow_handler.setFormatter(JSONFormatter())
    workflow_logger = logging.getLogger('workflows')
    workflow_logger.addHandler(workflow_handler)


# Production-grade metrics collection
class MetricsCollector:
    """Collect and aggregate system metrics"""
    
    def __init__(self, max_history: int = 1440):  # 24 hours of 1-min data
        self.max_history = max_history
        self.request_history = deque(maxlen=max_history)
        self.error_history = deque(maxlen=max_history)
        self.latency_history = deque(maxlen=max_history)
        
        self.start_time = time.time()
        self.total_requests = 0
        self.total_errors = 0
        self.total_latency_ms = 0.0
        
        # Error tracking
        self.error_types = {}
        self.endpoint_stats = {}
        
        logger = logging.getLogger(__name__)
        logger.info("MetricsCollector initialized")
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                      latency_ms: float, error: Optional[str] = None):
        """Record API request metrics"""
        self.total_requests += 1
        self.total_latency_ms += latency_ms
        
        if status_code >= 400:
            self.total_errors += 1
            if error:
                self.error_types[error] = self.error_types.get(error, 0) + 1
        
        # Track endpoint statistics
        key = f"{method} {endpoint}"
        if key not in self.endpoint_stats:
            self.endpoint_stats[key] = {
                'count': 0,
                'errors': 0,
                'total_latency': 0,
                'max_latency': 0,
                'min_latency': float('inf')
            }
        
        stats = self.endpoint_stats[key]
        stats['count'] += 1
        stats['total_latency'] += latency_ms
        stats['max_latency'] = max(stats['max_latency'], latency_ms)
        stats['min_latency'] = min(stats['min_latency'], latency_ms)
        
        if status_code >= 400:
            stats['errors'] += 1
        
        # Store in history
        self.request_history.append({
            'timestamp': datetime.utcnow(),
            'endpoint': endpoint,
            'method': method,
            'status': status_code,
            'latency': latency_ms
        })
    
    def record_workflow_execution(self, workflow_id: str, duration_ms: float, 
                                 success: bool, error: Optional[str] = None):
        """Record workflow execution metrics"""
        logger = logging.getLogger('workflows')
        logger.info(
            f"Workflow execution: {workflow_id}",
            extra={
                'extra_fields': {
                    'workflow_id': workflow_id,
                    'duration_ms': duration_ms,
                    'success': success,
                    'error': error
                }
            }
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        uptime_seconds = time.time() - self.start_time
        
        avg_latency = (self.total_latency_ms / self.total_requests) if self.total_requests > 0 else 0
        error_rate = (self.total_errors / self.total_requests * 100) if self.total_requests > 0 else 0
        success_rate = 100 - error_rate
        
        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'uptime_seconds': int(uptime_seconds),
            'metrics': {
                'total_requests': self.total_requests,
                'total_errors': self.total_errors,
                'error_rate_percent': round(error_rate, 2),
                'success_rate_percent': round(success_rate, 2),
                'avg_latency_ms': round(avg_latency, 2),
                'total_latency_ms': round(self.total_latency_ms, 2)
            },
            'error_breakdown': self._get_top_errors(5),
            'endpoint_performance': self._get_endpoint_stats()
        }
    
    def _get_top_errors(self, limit: int = 5) -> Dict[str, int]:
        """Get top error types"""
        sorted_errors = sorted(self.error_types.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_errors[:limit])
    
    def _get_endpoint_stats(self) -> Dict[str, Any]:
        """Get endpoint performance statistics"""
        stats = {}
        for endpoint, data in list(self.endpoint_stats.items()):
            if data['count'] > 0:
                stats[endpoint] = {
                    'requests': data['count'],
                    'errors': data['errors'],
                    'error_rate_percent': round(data['errors'] / data['count'] * 100, 2),
                    'avg_latency_ms': round(data['total_latency'] / data['count'], 2),
                    'max_latency_ms': round(data['max_latency'], 2),
                    'min_latency_ms': round(data['min_latency'], 2)
                }
        return stats
    
    def export_daily_summary(self, output_dir: str = 'metrics') -> str:
        """Export daily metrics summary to file"""
        Path(output_dir).mkdir(exist_ok=True)
        
        today = datetime.utcnow().strftime('%Y-%m-%d')
        filepath = Path(output_dir) / f'metrics_{today}.json'
        
        summary = self.get_summary()
        summary['export_date'] = today
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Metrics exported to {filepath}")
        
        return str(filepath)


class AlertManager:
    """Manage and track production alerts"""
    
    def __init__(self):
        self.active_alerts = []
        self.alert_history = deque(maxlen=1000)
        self.thresholds = {
            'error_rate_high': 5.0,  # %
            'latency_high': 500.0,  # ms
            'queue_depth_high': 1000,
            'database_timeout': 5000,  # ms
        }
        logger = logging.getLogger(__name__)
        logger.info("AlertManager initialized")
    
    def check_thresholds(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        
        error_rate = metrics['metrics']['error_rate_percent']
        if error_rate > self.thresholds['error_rate_high']:
            alert = {
                'timestamp': datetime.utcnow().isoformat(),
                'severity': 'HIGH',
                'type': 'error_rate_high',
                'message': f'Error rate {error_rate}% exceeds threshold {self.thresholds["error_rate_high"]}%',
                'current_value': error_rate,
                'threshold': self.thresholds['error_rate_high']
            }
            alerts.append(alert)
            self._log_alert(alert)
        
        avg_latency = metrics['metrics']['avg_latency_ms']
        if avg_latency > self.thresholds['latency_high']:
            alert = {
                'timestamp': datetime.utcnow().isoformat(),
                'severity': 'MEDIUM',
                'type': 'latency_high',
                'message': f'Average latency {avg_latency}ms exceeds threshold {self.thresholds["latency_high"]}ms',
                'current_value': avg_latency,
                'threshold': self.thresholds['latency_high']
            }
            alerts.append(alert)
            self._log_alert(alert)
        
        return alerts
    
    def _log_alert(self, alert: Dict[str, Any]):
        """Log alert event"""
        logger = logging.getLogger(__name__)
        logger.warning(
            f"ALERT: {alert['type']}",
            extra={
                'extra_fields': alert
            }
        )
    
    def set_threshold(self, alert_type: str, threshold: float):
        """Update alert threshold"""
        self.thresholds[alert_type] = threshold


# Performance tracking for specific operations
class PerformanceTracker:
    """Track performance of specific operations"""
    
    def __init__(self):
        self.operations = {}
        logger = logging.getLogger(__name__)
        logger.info("PerformanceTracker initialized")
    
    def record_operation(self, operation_name: str, duration_ms: float, 
                        success: bool, metadata: Optional[Dict] = None):
        """Record operation performance"""
        if operation_name not in self.operations:
            self.operations[operation_name] = {
                'count': 0,
                'successes': 0,
                'failures': 0,
                'total_time_ms': 0,
                'max_time_ms': 0,
                'min_time_ms': float('inf')
            }
        
        op = self.operations[operation_name]
        op['count'] += 1
        op['total_time_ms'] += duration_ms
        op['max_time_ms'] = max(op['max_time_ms'], duration_ms)
        op['min_time_ms'] = min(op['min_time_ms'], duration_ms)
        
        if success:
            op['successes'] += 1
        else:
            op['failures'] += 1
        
        logger = logging.getLogger(__name__)
        logger.info(
            f"Operation: {operation_name}",
            extra={
                'extra_fields': {
                    'operation': operation_name,
                    'duration_ms': duration_ms,
                    'success': success,
                    'metadata': metadata or {}
                }
            }
        )
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for specific operation"""
        if operation_name not in self.operations:
            return {}
        
        op = self.operations[operation_name]
        if op['count'] == 0:
            return {}
        
        return {
            'operation': operation_name,
            'total_executions': op['count'],
            'successes': op['successes'],
            'failures': op['failures'],
            'success_rate_percent': round(op['successes'] / op['count'] * 100, 2),
            'avg_duration_ms': round(op['total_time_ms'] / op['count'], 2),
            'max_duration_ms': round(op['max_time_ms'], 2),
            'min_duration_ms': round(op['min_time_ms'], 2)
        }


# Export for use in FastAPI application
__all__ = [
    'setup_json_logging',
    'JSONFormatter',
    'MetricsCollector',
    'AlertManager',
    'PerformanceTracker'
]
