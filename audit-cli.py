#!/usr/bin/env python
"""
Audit CLI Tool - Query and analyze audit logs from command line.

Usage:
    audit-cli stats                           # Show overall statistics
    audit-cli query --lead LEAD-001           # Query by lead ID
    audit-cli query --type error              # Query by event type
    audit-cli query --workflow sales          # Query by workflow
    audit-cli query --last 24h                # Query last 24 hours
    audit-cli errors                          # Show recent errors
    audit-cli performance                     # Show performance stats
    audit-cli integrity                       # Verify log integrity
    audit-cli export --format csv --output audit.csv  # Export data
"""

import sys
import argparse
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import get_audit_logger, AuditLogger


def parse_time_range(time_str: str) -> datetime:
    """Parse time range string like '24h', '7d', '1w'."""
    multipliers = {'h': 1/24, 'd': 1, 'w': 7, 'm': 30}
    
    if time_str[-1] in multipliers:
        value = int(time_str[:-1])
        days = value * multipliers[time_str[-1]]
        return datetime.utcnow() - timedelta(days=days)
    
    raise ValueError(f"Invalid time range: {time_str}")


def cmd_stats(audit: AuditLogger, args: argparse.Namespace) -> None:
    """Show overall statistics."""
    stats = audit.get_statistics(workflow=args.workflow)
    
    print("\n" + "="*70)
    print("AUDIT STATISTICS")
    print("="*70)
    print(f"\nTotal Events: {stats['total_events']}")
    print(f"Leads Processed: {stats['leads_processed']}")
    print(f"Errors: {stats['errors']}")
    print(f"\nEvent Types:")
    for event_type, count in sorted(stats['event_types'].items(), key=lambda x: -x[1]):
        print(f"  {event_type:20} {count:6}")
    print("="*70 + "\n")


def cmd_query(audit: AuditLogger, args: argparse.Namespace) -> None:
    """Query audit logs with filters."""
    # Parse time range if provided
    start_time = None
    if args.last:
        start_time = parse_time_range(args.last)
    
    # Query events
    events = audit.query_events(
        event_type=args.type,
        lead_id=args.lead,
        workflow=args.workflow,
        start_time=start_time,
        limit=args.limit
    )
    
    print(f"\nFound {len(events)} event(s)\n")
    
    for i, event in enumerate(events, 1):
        print(f"[{i}] {event['timestamp']} - {event['event_type']}")
        print(f"    Lead: {event.get('lead_id', 'N/A')}")
        print(f"    Workflow: {event.get('workflow', 'N/A')}")
        
        if args.verbose:
            print(f"    Details: {json.dumps(event['details'], indent=4)}")
        
        print()


def cmd_errors(audit: AuditLogger, args: argparse.Namespace) -> None:
    """Show recent errors."""
    events = audit.query_events(event_type="error", limit=args.limit)
    
    print("\n" + "="*70)
    print(f"RECENT ERRORS ({len(events)})")
    print("="*70 + "\n")
    
    for i, event in enumerate(events, 1):
        details = event['details']
        print(f"[{i}] {event['timestamp']}")
        print(f"    Type: {details.get('error_type', 'Unknown')}")
        print(f"    Message: {details.get('error_message', 'N/A')}")
        print(f"    Lead: {event.get('lead_id', 'N/A')}")
        print(f"    Workflow: {event.get('workflow', 'N/A')}")
        
        if args.verbose and 'traceback' in details:
            print(f"    Traceback:\n{details['traceback']}")
        
        print()


def cmd_performance(audit: AuditLogger, args: argparse.Namespace) -> None:
    """Show performance statistics."""
    stats = audit.get_performance_stats()
    
    if not stats:
        print("\nNo performance data available.\n")
        return
    
    print("\n" + "="*70)
    print("PERFORMANCE STATISTICS")
    print("="*70 + "\n")
    
    print(f"{'Operation':<25} {'Count':>8} {'Min':>8} {'Avg':>8} {'P95':>8} {'Max':>8}")
    print("-" * 70)
    
    for operation, data in sorted(stats.items()):
        print(f"{operation:<25} {data['count']:>8} "
              f"{data['min']:>8.3f} {data['avg']:>8.3f} "
              f"{data['p95']:>8.3f} {data['max']:>8.3f}")
    
    print("="*70 + "\n")


def cmd_integrity(audit: AuditLogger, args: argparse.Namespace) -> None:
    """Verify log integrity."""
    print("\n" + "="*70)
    print("LOG INTEGRITY VERIFICATION")
    print("="*70 + "\n")
    
    if not audit.audit_file.exists():
        print("Audit log file not found.\n")
        return
    
    total = 0
    valid = 0
    invalid = []
    
    with open(audit.audit_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            total += 1
            try:
                event = json.loads(line.strip())
                
                if 'signature' in event:
                    # Verify signature
                    signature = event.pop('signature')
                    event_str = json.dumps(event, sort_keys=True)
                    expected_sig = audit._calculate_signature(event_str)
                    
                    if signature == expected_sig:
                        valid += 1
                    else:
                        invalid.append((line_num, "Invalid signature"))
                else:
                    # No signature (might be old event)
                    valid += 1
            
            except json.JSONDecodeError:
                invalid.append((line_num, "JSON parse error"))
    
    print(f"Total events: {total}")
    print(f"Valid: {valid}")
    print(f"Invalid: {len(invalid)}")
    
    if invalid:
        print(f"\nInvalid entries:")
        for line_num, reason in invalid[:10]:
            print(f"  Line {line_num}: {reason}")
        
        if len(invalid) > 10:
            print(f"  ... and {len(invalid) - 10} more")
    
    print("\n" + "="*70 + "\n")


def cmd_export(audit: AuditLogger, args: argparse.Namespace) -> None:
    """Export audit data to CSV or JSON."""
    events = audit.query_events(limit=args.limit)
    
    if args.format == 'csv':
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            if not events:
                return
            
            # Get all possible fields
            fields = ['timestamp', 'event_type', 'actor', 'lead_id', 'workflow']
            detail_fields = set()
            for event in events:
                detail_fields.update(event.get('details', {}).keys())
            
            fields.extend(sorted(detail_fields))
            
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            
            for event in events:
                row = {
                    'timestamp': event.get('timestamp'),
                    'event_type': event.get('event_type'),
                    'actor': event.get('actor'),
                    'lead_id': event.get('lead_id'),
                    'workflow': event.get('workflow'),
                }
                row.update(event.get('details', {}))
                writer.writerow(row)
        
        print(f"\nExported {len(events)} events to {args.output}\n")
    
    elif args.format == 'json':
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2)
        
        print(f"\nExported {len(events)} events to {args.output}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Audit CLI Tool")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.add_argument('--workflow', help='Filter by workflow')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query audit logs')
    query_parser.add_argument('--type', help='Filter by event type')
    query_parser.add_argument('--lead', help='Filter by lead ID')
    query_parser.add_argument('--workflow', help='Filter by workflow')
    query_parser.add_argument('--last', help='Time range (e.g., 24h, 7d, 1w)')
    query_parser.add_argument('--limit', type=int, default=100, help='Max results')
    query_parser.add_argument('--verbose', '-v', action='store_true', help='Show details')
    
    # Errors command
    errors_parser = subparsers.add_parser('errors', help='Show recent errors')
    errors_parser.add_argument('--limit', type=int, default=20, help='Max errors to show')
    errors_parser.add_argument('--verbose', '-v', action='store_true', help='Show tracebacks')
    
    # Performance command
    perf_parser = subparsers.add_parser('performance', help='Show performance stats')
    
    # Integrity command
    integrity_parser = subparsers.add_parser('integrity', help='Verify log integrity')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export audit data')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Export format')
    export_parser.add_argument('--output', default='audit_export.csv', help='Output file')
    export_parser.add_argument('--limit', type=int, default=10000, help='Max events')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Get audit logger
    audit = get_audit_logger()
    
    # Execute command
    commands = {
        'stats': cmd_stats,
        'query': cmd_query,
        'errors': cmd_errors,
        'performance': cmd_performance,
        'integrity': cmd_integrity,
        'export': cmd_export
    }
    
    commands[args.command](audit, args)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
