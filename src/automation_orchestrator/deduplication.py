"""
Lead Deduplication Engine
Detects and merges duplicate leads based on configurable rules
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
from automation_orchestrator.audit import get_audit_logger
import re

logger = logging.getLogger(__name__)
audit = get_audit_logger()


class DeduplicationEngine:
    """Intelligent lead deduplication with configurable strategies"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize deduplication engine
        
        Args:
            config: Configuration for deduplication rules
                {
                    "enabled": bool,
                    "strategies": ["email", "phone", "fuzzy"],
                    "fuzzy_threshold": 0.85,  # 0-1
                    "ignore_fields": ["created_at", "updated_at"],
                    "merge_strategy": "keep_newest"  # keep_newest, keep_oldest, manual
                }
        """
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        self.audit = audit
    
    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """Default deduplication configuration"""
        return {
            "enabled": True,
            "strategies": ["email", "phone", "fuzzy"],
            "fuzzy_threshold": 0.85,
            "ignore_fields": ["id", "created_at", "updated_at", "crm_id"],
            "merge_strategy": "keep_newest",
            "track_merge_history": True
        }
    
    def find_duplicates(self, leads: List[Dict[str, Any]]) -> List[List[int]]:
        """
        Find duplicate groups in a list of leads
        
        Args:
            leads: List of lead dictionaries
        
        Returns:
            List of duplicate groups (index groups)
        """
        if not self.config.get("enabled"):
            return []
        
        duplicates = []
        checked = set()
        
        for i, lead1 in enumerate(leads):
            if i in checked:
                continue
            
            group = [i]
            
            for j, lead2 in enumerate(leads[i+1:], start=i+1):
                if j in checked:
                    continue
                
                if self._are_duplicates(lead1, lead2):
                    group.append(j)
                    checked.add(j)
            
            if len(group) > 1:
                duplicates.append(group)
                checked.add(i)
        
        return duplicates
    
    def _are_duplicates(self, lead1: Dict[str, Any], lead2: Dict[str, Any]) -> bool:
        """
        Check if two leads are duplicates using configured strategies
        
        Args:
            lead1: First lead
            lead2: Second lead
        
        Returns:
            True if duplicates, False otherwise
        """
        strategies = self.config.get("strategies", ["email"])
        
        for strategy in strategies:
            if strategy == "email" and self._match_email(lead1, lead2):
                return True
            elif strategy == "phone" and self._match_phone(lead1, lead2):
                return True
            elif strategy == "fuzzy" and self._match_fuzzy(lead1, lead2):
                return True
        
        return False
    
    def _match_email(self, lead1: Dict[str, Any], lead2: Dict[str, Any]) -> bool:
        """Check if emails match exactly"""
        email1 = lead1.get("email", "").lower().strip()
        email2 = lead2.get("email", "").lower().strip()
        
        if not email1 or not email2:
            return False
        
        return email1 == email2
    
    def _match_phone(self, lead1: Dict[str, Any], lead2: Dict[str, Any]) -> bool:
        """Check if phone numbers match (normalize first)"""
        phone1 = self._normalize_phone(lead1.get("phone", ""))
        phone2 = self._normalize_phone(lead2.get("phone", ""))
        
        if not phone1 or not phone2 or len(phone1) < 7:
            return False
        
        return phone1 == phone2
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone number (digits only)"""
        if not phone:
            return ""
        return re.sub(r"\D", "", str(phone))
    
    def _match_fuzzy(self, lead1: Dict[str, Any], lead2: Dict[str, Any]) -> bool:
        """
        Fuzzy match: compare name + email/company
        
        Args:
            lead1: First lead
            lead2: Second lead
        
        Returns:
            True if fuzzy match score above threshold
        """
        threshold = self.config.get("fuzzy_threshold", 0.85)
        
        # Get comparison fields
        name1 = f"{lead1.get('first_name', '')} {lead1.get('last_name', '')}".lower().strip()
        name2 = f"{lead2.get('first_name', '')} {lead2.get('last_name', '')}".lower().strip()
        
        if not name1 or not name2 or len(name1) < 3:
            return False
        
        # Calculate name similarity
        similarity = self._string_similarity(name1, name2)
        
        # If names are similar, check email or company too
        if similarity >= threshold:
            # Check if email or company also matches or is similar
            email1 = lead1.get("email", "").lower().strip()
            email2 = lead2.get("email", "").lower().strip()
            
            if email1 and email2 and email1 == email2:
                return True
            
            company1 = lead1.get("company", "").lower().strip()
            company2 = lead2.get("company", "").lower().strip()
            
            if company1 and company2 and self._string_similarity(company1, company2) > 0.8:
                return True
        
        return similarity >= threshold
    
    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Calculate string similarity (0-1)"""
        return SequenceMatcher(None, s1, s2).ratio()
    
    def merge_leads(self, leads: List[Dict[str, Any]], lead_indices: List[int],
                    merge_strategy: Optional[str] = None) -> Tuple[Dict[str, Any], List[str]]:
        """
        Merge duplicate leads into a single record
        
        Args:
            leads: List of all leads
            lead_indices: Indices of leads to merge
            merge_strategy: "keep_newest", "keep_oldest", or "manual"
        
        Returns:
            Tuple of (merged_lead, list_of_merged_lead_ids)
        """
        if not lead_indices or len(lead_indices) < 2:
            return {}, []
        
        strategy = merge_strategy or self.config.get("merge_strategy", "keep_newest")
        
        # Get leads to merge
        leads_to_merge = [leads[i] for i in lead_indices]
        merged_ids = [lead.get("id") for lead in leads_to_merge]
        
        if strategy == "keep_newest":
            # Keep lead with latest timestamp
            base_lead = max(leads_to_merge, 
                           key=lambda x: x.get("created_at", 0))
        elif strategy == "keep_oldest":
            # Keep lead with oldest timestamp
            base_lead = min(leads_to_merge,
                           key=lambda x: x.get("created_at", float('inf')))
        else:
            # Default to first
            base_lead = leads_to_merge[0]
        
        # Merge data: fill empty fields from other leads
        merged = base_lead.copy()
        ignore_fields = self.config.get("ignore_fields", [])
        
        for lead in leads_to_merge:
            for key, value in lead.items():
                if key not in ignore_fields and not merged.get(key):
                    merged[key] = value
        
        # Add merge metadata
        if self.config.get("track_merge_history"):
            merged["_merged_from"] = merged_ids
            merged["_merge_count"] = len(lead_indices)
            merged["_merged_at"] = merged.get("updated_at")
        
        self.logger.info(f"Merged {len(lead_indices)} leads: {merged_ids}")
        self.audit.log_event(
            event_type="leads_merged",
            details={
                "merged_count": len(lead_indices),
                "merged_ids": merged_ids,
                "kept_id": merged.get("id")
            }
        )
        
        return merged, merged_ids
    
    def deduplicate_batch(self, leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deduplicate a batch of leads
        
        Args:
            leads: List of leads to deduplicate
        
        Returns:
            {
                "unique_leads": [...],
                "duplicates_found": N,
                "duplicates": [[group1], [group2]],
                "merge_summary": {...}
            }
        """
        duplicate_groups = self.find_duplicates(leads)
        
        if not duplicate_groups:
            return {
                "unique_leads": leads,
                "duplicates_found": 0,
                "duplicates": [],
                "merge_summary": {"total_merged": 0}
            }
        
        # Track merged leads
        unique_leads = []
        merged_indices = set()
        merge_count = 0
        
        for group in duplicate_groups:
            merged_lead, _ = self.merge_leads(leads, group)
            unique_leads.append(merged_lead)
            merged_indices.update(group)
            merge_count += len(group) - 1
        
        # Add non-duplicate leads
        for i, lead in enumerate(leads):
            if i not in merged_indices:
                unique_leads.append(lead)
        
        return {
            "unique_leads": unique_leads,
            "duplicates_found": len(duplicate_groups),
            "duplicates": duplicate_groups,
            "merge_summary": {
                "total_merged": merge_count,
                "original_count": len(leads),
                "final_count": len(unique_leads),
                "duplicates_groups": len(duplicate_groups)
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        return {
            "enabled": self.config.get("enabled"),
            "strategies": self.config.get("strategies"),
            "fuzzy_threshold": self.config.get("fuzzy_threshold"),
            "merge_strategy": self.config.get("merge_strategy")
        }
