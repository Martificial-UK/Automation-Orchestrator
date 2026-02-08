"""
Real-time monitoring dashboard for audit system.
Displays live metrics, health status, and alerts.
"""

import sys
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import get_audit_logger


class AuditMonitor:
    """Real-time audit system monitor."""
    
    def __init__(self, audit_logger):
        self.audit = audit_logger
        self.start_time = time.time()
        self.event_history = deque(maxlen=60)  # Last 60 seconds
        self.last_event_count = 0
        
    def get_uptime(self) -> str:
        """Get system uptime."""
        uptime_seconds = int(time.time() - self.start_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        return f"{hours}h {minutes}m {seconds}s"
    
    def get_event_rate(self) -> float:
        """Calculate current event rate (events/sec)."""
        if len(self.event_history) < 2:
            return 0.0
        
        # Calculate rate over last 10 seconds
        recent = list(self.event_history)[-10:]
        if len(recent) < 2:
            return 0.0
        
        time_span = recent[-1][0] - recent[0][0]
        if time_span == 0:
            return 0.0
        
        event_count = sum(count for _, count in recent)
        return event_count / time_span
    
    def get_buffer_status(self) -> dict:
        """Get write buffer status."""
        buffer_size = self.audit.write_buffer.qsize()
        buffer_pct = (buffer_size / 1000) * 100  # Assume 1000 is "full"
        
        status = "healthy"
        if buffer_size > 500:
            status = "warning"
        elif buffer_size > 800:
            status = "critical"
        
        return {
            "size": buffer_size,
            "percentage": min(buffer_pct, 100),
            "status": status
        }
    
    def get_cache_stats(self) -> dict:
        """Get query cache statistics."""
        cache_size = len(self.audit.query_cache)
        cache_pct = (cache_size / 128) * 100  # Max 128 entries
        
        # Calculate approximate hit rate (based on cache size)
        hit_rate = min((cache_size / 128) * 95, 95) if cache_size > 0 else 0
        
        return {
            "size": cache_size,
            "capacity": 128,
            "percentage": cache_pct,
            "estimated_hit_rate": hit_rate
        }
    
    def get_rate_limit_status(self) -> dict:
        """Get rate limiting status."""
        stats = self.audit.get_rate_limit_stats()
        
        status = "healthy"
        blocked = stats.get('blocked_events', 0)
        if blocked > 100:
            status = "warning"
        elif blocked > 500:
            status = "critical"
        
        return {
            "blocked_events": blocked,
            "active_sources": stats.get('active_sources', 0),
            "status": status
        }
    
    def get_security_status(self) -> dict:
        """Get security event status."""
        # Get recent security events
        recent_events = self.audit.get_security_events(last_n=100)
        
        # Count by type
        event_types = {}
        for event in recent_events:
            event_type = event.get('event_type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        # Determine status
        status = "healthy"
        total_events = len(recent_events)
        if total_events > 50:
            status = "warning"
        elif total_events > 100:
            status = "critical"
        
        return {
            "total_events": total_events,
            "event_types": event_types,
            "status": status
        }
    
    def get_log_file_info(self) -> dict:
        """Get audit log file information."""
        log_file = self.audit.audit_file
        
        if not log_file.exists():
            return {
                "exists": False,
                "size": 0,
                "size_mb": 0,
                "line_count": 0
            }
        
        size = log_file.stat().st_size
        size_mb = size / (1024 * 1024)
        
        # Count lines (approximate for large files)
        line_count = 0
        try:
            with open(log_file, 'r') as f:
                line_count = sum(1 for _ in f)
        except:
            line_count = -1
        
        return {
            "exists": True,
            "size": size,
            "size_mb": size_mb,
            "line_count": line_count
        }
    
    def update_metrics(self):
        """Update metric history."""
        # Count events (would be better to track this in audit logger)
        log_info = self.get_log_file_info()
        current_count = log_info['line_count']
        
        if current_count > self.last_event_count:
            events_delta = current_count - self.last_event_count
            self.event_history.append((time.time(), events_delta))
            self.last_event_count = current_count
    
    def get_dashboard_data(self) -> dict:
        """Get all dashboard data."""
        self.update_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime": self.get_uptime(),
            "event_rate": self.get_event_rate(),
            "buffer": self.get_buffer_status(),
            "cache": self.get_cache_stats(),
            "rate_limit": self.get_rate_limit_status(),
            "security": self.get_security_status(),
            "log_file": self.get_log_file_info()
        }
    
    def print_dashboard(self, data: dict):
        """Print dashboard to console."""
        # Clear screen (platform-specific)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Header
        print("=" * 70)
        print("           AUDIT SYSTEM - REAL-TIME MONITORING DASHBOARD")
        print("=" * 70)
        print(f"Timestamp: {data['timestamp']}")
        print(f"Uptime:    {data['uptime']}")
        print()
        
        # Event Rate
        event_rate = data['event_rate']
        rate_bar = self._make_bar(event_rate, 100, 40)
        print(f"📊 EVENT RATE: {event_rate:.1f} events/sec")
        print(f"   {rate_bar}")
        print()
        
        # Buffer Status
        buffer = data['buffer']
        buffer_bar = self._make_bar(buffer['percentage'], 100, 40, 
                                     status=buffer['status'])
        print(f"💾 WRITE BUFFER: {buffer['size']} events")
        print(f"   {buffer_bar} {buffer['status'].upper()}")
        print()
        
        # Cache Status
        cache = data['cache']
        cache_bar = self._make_bar(cache['percentage'], 100, 40)
        print(f"⚡ QUERY CACHE: {cache['size']}/{cache['capacity']} entries")
        print(f"   {cache_bar}")
        print(f"   Estimated hit rate: {cache['estimated_hit_rate']:.1f}%")
        print()
        
        # Rate Limiting
        rate_limit = data['rate_limit']
        print(f"🚦 RATE LIMITING: {rate_limit['status'].upper()}")
        print(f"   Blocked events: {rate_limit['blocked_events']}")
        print(f"   Active sources: {rate_limit['active_sources']}")
        print()
        
        # Security
        security = data['security']
        print(f"🔒 SECURITY: {security['status'].upper()}")
        print(f"   Total events: {security['total_events']}")
        if security['event_types']:
            print(f"   Event types:")
            for event_type, count in list(security['event_types'].items())[:5]:
                print(f"     • {event_type}: {count}")
        print()
        
        # Log File
        log_file = data['log_file']
        if log_file['exists']:
            print(f"📝 LOG FILE:")
            print(f"   Size: {log_file['size_mb']:.2f} MB")
            print(f"   Events: {log_file['line_count']:,}")
        else:
            print(f"📝 LOG FILE: Not created yet")
        
        print()
        print("=" * 70)
        print("Press Ctrl+C to exit")
        print("=" * 70)
    
    def _make_bar(self, value: float, max_value: float, width: int, 
                  status: str = None) -> str:
        """Create a progress bar."""
        filled = int((value / max_value) * width)
        bar = "█" * filled + "░" * (width - filled)
        
        # Color based on status
        if status == "critical":
            return f"[{bar}] ⚠️  CRITICAL"
        elif status == "warning":
            return f"[{bar}] ⚠️  WARNING"
        else:
            return f"[{bar}] ✓"
    
    def run_live(self, refresh_interval: float = 2.0):
        """Run live monitoring dashboard."""
        print("Starting audit monitoring dashboard...")
        print("Refresh interval: {} seconds".format(refresh_interval))
        time.sleep(1)
        
        try:
            while True:
                data = self.get_dashboard_data()
                self.print_dashboard(data)
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
            print("Final statistics:")
            data = self.get_dashboard_data()
            print(f"  • Uptime: {data['uptime']}")
            print(f"  • Average event rate: {data['event_rate']:.1f} events/sec")
            print(f"  • Total events: {data['log_file']['line_count']:,}")


def main():
    """Run monitoring dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit system monitoring dashboard")
    parser.add_argument("--log-file", default="logs/audit.log", 
                       help="Path to audit log file")
    parser.add_argument("--refresh", type=float, default=2.0,
                       help="Refresh interval in seconds")
    parser.add_argument("--once", action="store_true",
                       help="Print metrics once and exit")
    
    args = parser.parse_args()
    
    # Initialize audit logger
    audit = get_audit_logger(args.log_file)
    
    # Create monitor
    monitor = AuditMonitor(audit)
    
    if args.once:
        # Single snapshot
        data = monitor.get_dashboard_data()
        monitor.print_dashboard(data)
    else:
        # Live monitoring
        monitor.run_live(refresh_interval=args.refresh)


if __name__ == "__main__":
    main()
