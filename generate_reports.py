"""
Audit Report Generator - Create HTML/PDF reports from audit data.
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import get_audit_logger


class ReportGenerator:
    """Generate comprehensive audit reports."""
    
    def __init__(self, audit_logger):
        self.audit = audit_logger
    
    def generate_daily_report(self, date: datetime = None) -> str:
        """Generate daily summary report."""
        if date is None:
            date = datetime.now()
        
        start_time = date.replace(hour=0, minute=0, second=0)
        end_time = start_time + timedelta(days=1)
        
        # Get events for the day
        events = self.audit.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Analyze
        stats = self._analyze_events(events)
        
        # Generate HTML
        html = self._generate_html_report(
            title=f"Daily Audit Report - {date.strftime('%Y-%m-%d')}",
            stats=stats,
            events=events
        )
        
        return html
    
    def generate_weekly_report(self) -> str:
        """Generate weekly summary report."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        events = self.audit.query_events(
            start_time=start_date,
            end_time=end_date,
            limit=100000
        )
        
        stats = self._analyze_events(events)
        
        html = self._generate_html_report(
            title=f"Weekly Audit Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            stats=stats,
            events=events
        )
        
        return html
    
    def _analyze_events(self, events: List[Dict]) -> Dict[str, Any]:
        """Analyze events and return statistics."""
        event_types = Counter(e['event_type'] for e in events)
        workflows = Counter(e.get('workflow') for e in events if e.get('workflow'))
        leads = set(e.get('lead_id') for e in events if e.get('lead_id'))
        
        # Time series (hourly)
        hourly = Counter()
        for event in events:
            try:
                dt = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                hour = dt.strftime('%Y-%m-%d %H:00')
                hourly[hour] += 1
            except:
                pass
        
        # Error analysis
        errors = [e for e in events if e['event_type'] == 'error']
        error_types = Counter(e['details'].get('error_type', 'Unknown') for e in errors)
        
        return {
            'total_events': len(events),
            'unique_leads': len(leads),
            'event_types': dict(event_types),
            'workflows': dict(workflows),
            'errors': {
                'total': len(errors),
                'by_type': dict(error_types)
            },
            'hourly': dict(sorted(hourly.items()))
        }
    
    def _generate_html_report(self, title: str, stats: Dict, events: List[Dict]) -> str:
        """Generate HTML report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .metric {{
            display: inline-block;
            background: #f0f0f0;
            padding: 20px;
            margin: 10px;
            border-radius: 5px;
            min-width: 200px;
        }}
        .metric-value {{
            font-size: 36px;
            font-weight: bold;
            color: #4CAF50;
        }}
        .metric-label {{
            font-size: 14px;
            color: #777;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .error {{
            color: #f44336;
        }}
        .success {{
            color: #4CAF50;
        }}
        .chart {{
            margin: 20px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Overview</h2>
        <div class="metric">
            <div class="metric-value">{stats['total_events']}</div>
            <div class="metric-label">Total Events</div>
        </div>
        <div class="metric">
            <div class="metric-value">{stats['unique_leads']}</div>
            <div class="metric-label">Unique Leads</div>
        </div>
        <div class="metric">
            <div class="metric-value" class="{'error' if stats['errors']['total'] > 0 else 'success'}">
                {stats['errors']['total']}
            </div>
            <div class="metric-label">Errors</div>
        </div>
        
        <h2>Event Types</h2>
        <table>
            <tr>
                <th>Event Type</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
"""
        
        total = stats['total_events']
        for event_type, count in sorted(stats['event_types'].items(), key=lambda x: -x[1]):
            percentage = (count / total * 100) if total > 0 else 0
            html += f"""
            <tr>
                <td>{event_type}</td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
            </tr>
"""
        
        html += """
        </table>
        
        <h2>Workflows</h2>
        <table>
            <tr>
                <th>Workflow</th>
                <th>Events</th>
            </tr>
"""
        
        for workflow, count in sorted(stats['workflows'].items(), key=lambda x: -x[1]):
            html += f"""
            <tr>
                <td>{workflow}</td>
                <td>{count}</td>
            </tr>
"""
        
        html += """
        </table>
"""
        
        # Error details
        if stats['errors']['total'] > 0:
            html += """
        <h2>Error Summary</h2>
        <table>
            <tr>
                <th>Error Type</th>
                <th>Count</th>
            </tr>
"""
            for error_type, count in sorted(stats['errors']['by_type'].items(), key=lambda x: -x[1]):
                html += f"""
            <tr>
                <td class="error">{error_type}</td>
                <td>{count}</td>
            </tr>
"""
            html += """
        </table>
"""
        
        # Activity timeline
        html += """
        <h2>Activity Timeline</h2>
        <div class="chart">
"""
        max_count = max(stats['hourly'].values()) if stats['hourly'] else 1
        for hour, count in stats['hourly'].items():
            width = (count / max_count * 100) if max_count > 0 else 0
            html += f"""
            <div style="margin: 5px 0;">
                <span style="display: inline-block; width: 150px;">{hour}</span>
                <div style="display: inline-block; width: {width}%; background: #4CAF50; height: 20px;"></div>
                <span style="margin-left: 10px;">{count}</span>
            </div>
"""
        
        html += """
        </div>
        
        <h2>Recent Events</h2>
        <table>
            <tr>
                <th>Timestamp</th>
                <th>Type</th>
                <th>Lead ID</th>
                <th>Workflow</th>
            </tr>
"""
        
        for event in events[-50:]:  # Last 50 events
            html += f"""
            <tr>
                <td>{event.get('timestamp', 'N/A')}</td>
                <td>{event.get('event_type', 'N/A')}</td>
                <td>{event.get('lead_id', 'N/A')}</td>
                <td>{event.get('workflow', 'N/A')}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
</body>
</html>
"""
        return html
    
    def save_report(self, html: str, filename: str) -> None:
        """Save HTML report to file."""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"Report saved: {output_path.absolute()}")


def main():
    """Generate reports."""
    audit = get_audit_logger()
    generator = ReportGenerator(audit)
    
    print("\nGenerating audit reports...\n")
    
    # Daily report
    daily_html = generator.generate_daily_report()
    generator.save_report(daily_html, "reports/daily_audit_report.html")
    
    # Weekly report
    weekly_html = generator.generate_weekly_report()
    generator.save_report(weekly_html, "reports/weekly_audit_report.html")
    
    print("\nReports generated successfully!")
    print("  - reports/daily_audit_report.html")
    print("  - reports/weekly_audit_report.html\n")


if __name__ == "__main__":
    main()
