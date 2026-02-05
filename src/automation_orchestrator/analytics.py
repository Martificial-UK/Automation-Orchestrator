"""
Analytics Engine
Tracks metrics and generates reports for lead management and workflows
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class AnalyticsEvent:
    """Single analytics event"""
    
    def __init__(self, event_type: str, timestamp: Optional[datetime] = None,
                 data: Optional[Dict[str, Any]] = None):
        self.event_type = event_type
        self.timestamp = timestamp or datetime.utcnow()
        self.data = data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


class Analytics:
    """Track and report on automation metrics"""
    
    # Event types
    LEAD_CREATED = "lead_created"
    LEAD_QUALIFIED = "lead_qualified"
    LEAD_SYNCED = "lead_synced"
    WORKFLOW_EXECUTED = "workflow_executed"
    WORKFLOW_SUCCEEDED = "workflow_succeeded"
    WORKFLOW_FAILED = "workflow_failed"
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    
    def __init__(self, max_events: int = 100000):
        self.events: List[AnalyticsEvent] = []
        self.max_events = max_events
        self.logger = logging.getLogger(__name__)
    
    def track_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Track an analytics event"""
        event = AnalyticsEvent(event_type, data=data)
        self.events.append(event)
        
        # Keep memory bounded
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
    
    def get_events(self, event_type: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[AnalyticsEvent]:
        """Get events with optional filtering"""
        results = self.events
        
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        
        if start_date:
            results = [e for e in results if e.timestamp >= start_date]
        
        if end_date:
            results = [e for e in results if e.timestamp <= end_date]
        
        return results
    
    def get_lead_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get lead management metrics"""
        start = datetime.utcnow() - timedelta(days=days)
        end = datetime.utcnow()
        
        created = len(self.get_events(self.LEAD_CREATED, start, end))
        qualified = len(self.get_events(self.LEAD_QUALIFIED, start, end))
        synced = len(self.get_events(self.LEAD_SYNCED, start, end))
        
        return {
            "period_days": days,
            "total_leads_created": created,
            "total_leads_qualified": qualified,
            "total_leads_synced": synced,
            "qualification_rate": (qualified / created * 100) if created > 0 else 0,
            "sync_rate": (synced / created * 100) if created > 0 else 0,
            "daily_average": {
                "created": created / days,
                "qualified": qualified / days,
                "synced": synced / days
            }
        }
    
    def get_workflow_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get workflow execution metrics"""
        start = datetime.utcnow() - timedelta(days=days)
        end = datetime.utcnow()
        
        executed = len(self.get_events(self.WORKFLOW_EXECUTED, start, end))
        succeeded = len(self.get_events(self.WORKFLOW_SUCCEEDED, start, end))
        failed = len(self.get_events(self.WORKFLOW_FAILED, start, end))
        
        return {
            "period_days": days,
            "total_executions": executed,
            "total_succeeded": succeeded,
            "total_failed": failed,
            "success_rate": (succeeded / executed * 100) if executed > 0 else 0,
            "failure_rate": (failed / executed * 100) if executed > 0 else 0,
            "daily_average": {
                "executed": executed / days,
                "succeeded": succeeded / days,
                "failed": failed / days
            }
        }
    
    def get_email_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get email campaign metrics"""
        start = datetime.utcnow() - timedelta(days=days)
        end = datetime.utcnow()
        
        sent = len(self.get_events(self.EMAIL_SENT, start, end))
        opened = len(self.get_events(self.EMAIL_OPENED, start, end))
        clicked = len(self.get_events(self.EMAIL_CLICKED, start, end))
        
        return {
            "period_days": days,
            "total_sent": sent,
            "total_opened": opened,
            "total_clicked": clicked,
            "open_rate": (opened / sent * 100) if sent > 0 else 0,
            "click_rate": (clicked / sent * 100) if sent > 0 else 0,
            "daily_average": {
                "sent": sent / days,
                "opened": opened / days,
                "clicked": clicked / days
            }
        }
    
    def get_dashboard_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get complete dashboard summary"""
        return {
            "report_date": datetime.utcnow().isoformat(),
            "period_days": days,
            "leads": self.get_lead_metrics(days),
            "workflows": self.get_workflow_metrics(days),
            "emails": self.get_email_metrics(days),
            "total_events": len(self.events)
        }
    
    def get_daily_breakdown(self, days: int = 30) -> Dict[str, Any]:
        """Get daily breakdown of metrics"""
        breakdown = defaultdict(lambda: {
            "leads_created": 0,
            "leads_qualified": 0,
            "workflows_executed": 0,
            "emails_sent": 0
        })
        
        start = datetime.utcnow() - timedelta(days=days)
        
        for event in self.get_events(start_date=start):
            date_key = event.timestamp.date().isoformat()
            
            if event.event_type == self.LEAD_CREATED:
                breakdown[date_key]["leads_created"] += 1
            elif event.event_type == self.LEAD_QUALIFIED:
                breakdown[date_key]["leads_qualified"] += 1
            elif event.event_type == self.WORKFLOW_EXECUTED:
                breakdown[date_key]["workflows_executed"] += 1
            elif event.event_type == self.EMAIL_SENT:
                breakdown[date_key]["emails_sent"] += 1
        
        return {
            "period_days": days,
            "daily": dict(breakdown)
        }
    
    def get_roi_estimate(self, lead_value: float = 100.0, 
                        conversion_rate: float = 0.10) -> Dict[str, Any]:
        """Estimate ROI based on lead metrics"""
        metrics = self.get_lead_metrics()
        
        qualified_leads = metrics.get("total_leads_qualified", 0)
        conversions = qualified_leads * conversion_rate
        revenue = conversions * lead_value
        
        return {
            "qualified_leads": qualified_leads,
            "estimated_conversions": conversions,
            "assumed_lead_value": lead_value,
            "assumed_conversion_rate": conversion_rate,
            "estimated_revenue": revenue,
            "revenue_per_lead": (revenue / metrics.get("total_leads_created")) 
                                if metrics.get("total_leads_created") > 0 else 0
        }
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        summary = self.get_dashboard_summary()
        
        if format == "json":
            return json.dumps(summary, indent=2, default=str)
        elif format == "csv":
            # Simple CSV export of daily breakdown
            daily = self.get_daily_breakdown()
            lines = ["date,leads_created,leads_qualified,workflows_executed,emails_sent"]
            for date, metrics in sorted(daily.get("daily", {}).items()):
                lines.append(
                    f"{date},{metrics['leads_created']},"
                    f"{metrics['leads_qualified']},{metrics['workflows_executed']},"
                    f"{metrics['emails_sent']}"
                )
            return "\n".join(lines)
        else:
            return json.dumps(summary, indent=2, default=str)
    
    def clear_old_events(self, days: int = 90) -> int:
        """Clear events older than specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        original_count = len(self.events)
        
        self.events = [e for e in self.events if e.timestamp >= cutoff]
        
        removed = original_count - len(self.events)
        self.logger.info(f"Cleared {removed} events older than {days} days")
        
        return removed
