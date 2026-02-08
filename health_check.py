"""
Health check endpoint for audit system.
Provides JSON health status for monitoring/alerting systems.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import get_audit_logger


class HealthChecker:
    """Health check system for audit logger."""
    
    def __init__(self, audit_logger):
        self.audit = audit_logger
        self.start_time = time.time()
    
    def check_write_buffer(self) -> dict:
        """Check write buffer health."""
        buffer_size = self.audit.write_buffer.qsize()
        
        # Thresholds
        warning_threshold = 500
        critical_threshold = 800
        
        status = "healthy"
        message = f"Buffer size: {buffer_size} events"
        
        if buffer_size >= critical_threshold:
            status = "critical"
            message = f"Buffer critically full: {buffer_size} events (>{critical_threshold})"
        elif buffer_size >= warning_threshold:
            status = "warning"
            message = f"Buffer filling up: {buffer_size} events (>{warning_threshold})"
        
        return {
            "component": "write_buffer",
            "status": status,
            "message": message,
            "metrics": {
                "size": buffer_size,
                "warning_threshold": warning_threshold,
                "critical_threshold": critical_threshold
            }
        }
    
    def check_worker_thread(self) -> dict:
        """Check if background worker thread is alive."""
        is_alive = self.audit.write_thread.is_alive()
        
        status = "healthy" if is_alive else "critical"
        message = "Worker thread running" if is_alive else "Worker thread stopped"
        
        return {
            "component": "worker_thread",
            "status": status,
            "message": message,
            "metrics": {
                "alive": is_alive,
                "daemon": self.audit.write_thread.daemon
            }
        }
    
    def check_log_file(self) -> dict:
        """Check audit log file status."""
        log_file = self.audit.audit_file
        
        if not log_file.exists():
            return {
                "component": "log_file",
                "status": "warning",
                "message": "Log file not yet created",
                "metrics": {
                    "exists": False,
                    "path": str(log_file)
                }
            }
        
        try:
            # Check file is writable
            size = log_file.stat().st_size
            size_mb = size / (1024 * 1024)
            
            # Check if file is too large (>1GB warning, >5GB critical)
            status = "healthy"
            message = f"Log file: {size_mb:.2f} MB"
            
            if size_mb > 5000:
                status = "critical"
                message = f"Log file very large: {size_mb:.2f} MB (>5GB), rotation needed"
            elif size_mb > 1000:
                status = "warning"
                message = f"Log file large: {size_mb:.2f} MB (>1GB), consider rotation"
            
            return {
                "component": "log_file",
                "status": status,
                "message": message,
                "metrics": {
                    "exists": True,
                    "size_bytes": size,
                    "size_mb": round(size_mb, 2),
                    "path": str(log_file)
                }
            }
        
        except Exception as e:
            return {
                "component": "log_file",
                "status": "critical",
                "message": f"Error accessing log file: {e}",
                "metrics": {
                    "exists": True,
                    "error": str(e)
                }
            }
    
    def check_rate_limiting(self) -> dict:
        """Check rate limiting status."""
        stats = self.audit.get_rate_limit_stats()
        blocked = stats.get('blocked_events', 0)
        active = stats.get('active_sources', 0)
        
        status = "healthy"
        message = f"Rate limiting active: {blocked} blocked, {active} sources"
        
        if blocked > 1000:
            status = "critical"
            message = f"High rate limiting: {blocked} events blocked"
        elif blocked > 500:
            status = "warning"
            message = f"Moderate rate limiting: {blocked} events blocked"
        
        return {
            "component": "rate_limiting",
            "status": status,
            "message": message,
            "metrics": stats
        }
    
    def check_security_events(self) -> dict:
        """Check for recent security events."""
        events = self.audit.get_security_events(last_n=100)
        
        # Count by severity
        validation_errors = sum(1 for e in events if e.get('event_type') == 'validation_error')
        rate_limit_exceeded = sum(1 for e in events if e.get('event_type') == 'rate_limit_exceeded')
        other = len(events) - validation_errors - rate_limit_exceeded
        
        status = "healthy"
        message = f"Security monitoring active: {len(events)} recent events"
        
        if validation_errors > 50 or other > 10:
            status = "critical"
            message = f"High security activity: {validation_errors} validation errors, {other} other"
        elif validation_errors > 20 or other > 5:
            status = "warning"
            message = f"Elevated security activity: {validation_errors} validation errors"
        
        return {
            "component": "security",
            "status": status,
            "message": message,
            "metrics": {
                "total_events": len(events),
                "validation_errors": validation_errors,
                "rate_limit_exceeded": rate_limit_exceeded,
                "other": other
            }
        }
    
    def check_cache(self) -> dict:
        """Check query cache status."""
        cache_size = len(self.audit.query_cache)
        capacity = 128
        
        status = "healthy"
        message = f"Cache: {cache_size}/{capacity} entries"
        
        # Cache being full is actually good (means it's being used)
        if cache_size == 0:
            status = "warning"
            message = "Cache empty (may not be used)"
        
        return {
            "component": "query_cache",
            "status": status,
            "message": message,
            "metrics": {
                "size": cache_size,
                "capacity": capacity,
                "usage_percentage": round((cache_size / capacity) * 100, 1)
            }
        }
    
    def get_health_status(self) -> dict:
        """Get complete health status."""
        checks = [
            self.check_write_buffer(),
            self.check_worker_thread(),
            self.check_log_file(),
            self.check_rate_limiting(),
            self.check_security_events(),
            self.check_cache()
        ]
        
        # Determine overall status
        statuses = [check['status'] for check in checks]
        if 'critical' in statuses:
            overall_status = "critical"
        elif 'warning' in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        # Get last event time
        last_event_time = None
        try:
            if self.audit.audit_file.exists():
                last_modified = self.audit.audit_file.stat().st_mtime
                last_event_time = datetime.fromtimestamp(last_modified).isoformat()
        except:
            pass
        
        uptime = int(time.time() - self.start_time)
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "healthy": statuses.count("healthy"),
                "warning": statuses.count("warning"),
                "critical": statuses.count("critical")
            },
            "metadata": {
                "audit_file": str(self.audit.audit_file),
                "last_event_time": last_event_time
            }
        }


def print_health_status(status: dict, verbose: bool = False):
    """Print health status in human-readable format."""
    # Overall status
    status_emoji = {
        "healthy": "✅",
        "warning": "⚠️",
        "critical": "❌"
    }
    
    emoji = status_emoji.get(status['status'], "❓")
    print(f"\n{emoji} Overall Status: {status['status'].upper()}")
    print(f"Timestamp: {status['timestamp']}")
    print(f"Uptime: {status['uptime_seconds']}s")
    print()
    
    # Component checks
    print("Component Health Checks:")
    print("-" * 60)
    
    for check in status['checks']:
        emoji = status_emoji.get(check['status'], "❓")
        component = check['component'].replace('_', ' ').title()
        print(f"{emoji} {component}: {check['status'].upper()}")
        print(f"   {check['message']}")
        
        if verbose and check.get('metrics'):
            print(f"   Metrics:")
            for key, value in check['metrics'].items():
                print(f"     • {key}: {value}")
        print()
    
    # Summary
    summary = status['summary']
    print("Summary:")
    print(f"  ✅ Healthy: {summary['healthy']}/{summary['total_checks']}")
    print(f"  ⚠️  Warning: {summary['warning']}/{summary['total_checks']}")
    print(f"  ❌ Critical: {summary['critical']}/{summary['total_checks']}")
    print()


def main():
    """Run health check."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit system health check")
    parser.add_argument("--log-file", default="logs/audit.log",
                       help="Path to audit log file")
    parser.add_argument("--json", action="store_true",
                       help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output with metrics")
    parser.add_argument("--watch", type=float, metavar="SECONDS",
                       help="Continuously monitor every N seconds")
    
    args = parser.parse_args()
    
    # Initialize audit logger
    audit = get_audit_logger(args.log_file)
    
    # Create health checker
    checker = HealthChecker(audit)
    
    if args.watch:
        # Continuous monitoring
        try:
            print(f"Starting continuous health monitoring (every {args.watch}s)...")
            print("Press Ctrl+C to stop")
            
            while True:
                status = checker.get_health_status()
                
                if args.json:
                    print(json.dumps(status, indent=2))
                else:
                    import os
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print_health_status(status, verbose=args.verbose)
                
                time.sleep(args.watch)
        
        except KeyboardInterrupt:
            print("\nHealth monitoring stopped.")
    
    else:
        # Single check
        status = checker.get_health_status()
        
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print_health_status(status, verbose=args.verbose)
        
        # Exit with appropriate code
        if status['status'] == 'critical':
            sys.exit(2)
        elif status['status'] == 'warning':
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
