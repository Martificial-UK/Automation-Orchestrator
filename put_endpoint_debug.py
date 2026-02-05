#!/usr/bin/env python3
"""
PUT Endpoint Isolated Debug Script
Tests PUT endpoint with detailed Pydantic validation error capture
Run with: python put_endpoint_debug.py
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, Any
from datetime import datetime
import uvicorn
import json

# Simple models for testing
class LeadDataDebug(BaseModel):
    """Lead data model - debug version"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"  # Allow extra fields


class LeadResponseDebug(BaseModel):
    """Response for lead operations - debug version"""
    id: str
    status: str
    message: str
    crm_id: Optional[str] = None
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


# In-memory store
leads_cache = {
    "lead-1": {
        "id": "lead-1",
        "first_name": "John",
        "last_name": "Test",
        "email": "john.test@example.com",
        "phone": "+1-555-0001",
        "company": "Test Corp",
        "source": "test",
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
}

# Create debug app
app = FastAPI(title="PUT Endpoint Debug")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug/lead/{lead_id}")
async def get_lead_debug(lead_id: str):
    """Get lead with full details"""
    if lead_id not in leads_cache:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    
    lead = leads_cache[lead_id]
    print(f"[GET] Retrieved lead: {json.dumps(lead, indent=2)}")
    return lead

@app.put("/debug/lead/{lead_id}")
async def update_lead_debug(lead_id: str, lead: LeadDataDebug, background_tasks: BackgroundTasks):
    """
    PUT endpoint with detailed debug output and error capture
    """
    try:
        print(f"\n[PUT] Request received for lead_id: {lead_id}")
        print(f"[PUT] Raw input data type: {type(lead)}")
        print(f"[PUT] Raw input data: {lead}")
        
        # Validate input data
        try:
            lead_dict_from_model = lead.model_dump()
            print(f"[PUT] model_dump() result: {json.dumps(lead_dict_from_model, default=str, indent=2)}")
        except Exception as e:
            print(f"[PUT] ERROR in model_dump(): {e}")
            raise
        
        # Get existing lead
        existing_lead = leads_cache.get(lead_id, {})
        print(f"[PUT] Existing lead in cache: {json.dumps(existing_lead, default=str, indent=2)}")
        
        # Prepare updated lead data
        lead_dict = {
            "id": lead_id,
            "first_name": lead.first_name or existing_lead.get("first_name", ""),
            "last_name": lead.last_name or existing_lead.get("last_name", ""),
            "email": lead.email or existing_lead.get("email", ""),
            "phone": lead.phone or existing_lead.get("phone", ""),
            "company": lead.company or existing_lead.get("company", ""),
            "source": lead.source or existing_lead.get("source", "api"),
            "created_at": existing_lead.get("created_at", datetime.now().isoformat()),
            "status": "active"
        }
        
        print(f"[PUT] Prepared lead_dict: {json.dumps(lead_dict, default=str, indent=2)}")
        
        # Store in cache
        leads_cache[lead_id] = lead_dict
        print(f"[PUT] Stored in cache successfully")
        
        # Try to build response
        try:
            response_data = lead.model_dump()
            print(f"[PUT] Response data: {json.dumps(response_data, default=str, indent=2)}")
            
            response = LeadResponseDebug(
                id=lead_id,
                status="updated",
                message="Lead updated successfully",
                timestamp=datetime.now(),
                data=response_data
            )
            print(f"[PUT] Response object created successfully")
            print(f"[PUT] Response: {response.model_dump_json(default=str)}")
            
            return response
        except ValidationError as e:
            print(f"[PUT] ERROR building response: {e}")
            print(f"[PUT] Validation error details:")
            for error in e.errors():
                print(f"  - {error}")
            raise HTTPException(status_code=500, detail=f"Response validation error: {str(e)}")
        
    except ValidationError as ve:
        print(f"[PUT] PYDANTIC VALIDATION ERROR:")
        for error in ve.errors():
            print(f"  Type: {error.get('type')}")
            print(f"  Loc: {error.get('loc')}")
            print(f"  Msg: {error.get('msg')}")
            print(f"  Input: {error.get('input')}")
        
        return {
            "error": "Validation failed",
            "details": [
                {
                    "type": e.get("type"),
                    "location": e.get("loc"),
                    "message": e.get("msg"),
                    "input": str(e.get("input"))
                }
                for e in ve.errors()
            ]
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"[PUT] UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/debug/lead")
async def create_lead_debug(lead: LeadDataDebug):
    """Test POST with same model"""
    lead_id = "test-new"
    leads_cache[lead_id] = {
        "id": lead_id,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "source": lead.source or "api",
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    
    return LeadResponseDebug(
        id=lead_id,
        status="created",
        message="Lead created",
        timestamp=datetime.now(),
        data=lead.model_dump()
    )


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PUT ENDPOINT DEBUG SERVER")
    print("="*60)
    print("\nEndpoints:")
    print("  GET  /health              - Health check")
    print("  GET  /debug/lead/lead-1   - Get seeded lead")
    print("  POST /debug/lead          - Create new lead")
    print("  PUT  /debug/lead/lead-1   - Update lead (DEBUG)")
    print("\nTest commands:")
    print('  curl -X GET http://localhost:8001/health')
    print('  curl -X GET http://localhost:8001/debug/lead/lead-1')
    print('  curl -X POST http://localhost:8001/debug/lead -H "Content-Type: application/json" \\')
    print('    -d \'{"email":"test@example.com","first_name":"Test","last_name":"User"}\'')
    print('  curl -X PUT http://localhost:8001/debug/lead/lead-1 -H "Content-Type: application/json" \\')
    print('    -d \'{"email":"updated@example.com","first_name":"Updated","last_name":"Lead"}\'')
    print("="*60 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="debug")
