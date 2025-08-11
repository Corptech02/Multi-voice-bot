#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import random
import string
import json
import asyncio
from datetime import datetime, timedelta
import base64
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import os
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Insurance COI Automation API", version="3.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
coi_requests = []
email_count = 0
last_scan_time = datetime.now()
scan_results = {"new_emails": 0, "processed": 0}
monitoring_active = False

# Initialize with some example data
coi_requests = [
    {
        "id": "REQ001",
        "date": "2025-01-08",
        "vendor": "ABC Construction Inc.",
        "status": "pending",
        "coverages": {
            "general_liability": {
                "required": 1000000,
                "received": 0,
                "status": "missing"
            }
        }
    }
]

class COIRequest(BaseModel):
    vendor: str
    coverages: Dict[str, Dict[str, Any]]

@app.get("/")
async def root():
    return {"message": "COI Backend API is running", "version": "3.0"}

@app.get("/api/v1/requests")
async def get_requests():
    return coi_requests

@app.post("/api/v1/requests")
async def create_request(request: COIRequest):
    request_id = f"REQ{random.randint(100, 999)}"
    new_request = {
        "id": request_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "vendor": request.vendor,
        "status": "pending",
        "coverages": request.coverages
    }
    coi_requests.append(new_request)
    return new_request

@app.get("/api/v1/requests/monitoring/status")
async def get_monitoring_status():
    return {
        "active": monitoring_active,
        "email_count": email_count,
        "last_scan": last_scan_time.isoformat(),
        "scan_results": scan_results
    }

@app.post("/api/v1/requests/monitoring/start")
async def start_monitoring():
    global monitoring_active
    monitoring_active = True
    logger.info("Email monitoring started (simulated)")
    return {
        "status": "started",
        "message": "Email monitoring started",
        "active": monitoring_active
    }

@app.post("/api/v1/requests/monitoring/stop")
async def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    logger.info("Email monitoring stopped")
    return {
        "status": "stopped",
        "message": "Email monitoring stopped",
        "active": monitoring_active
    }

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    uvicorn.run(app, host="0.0.0.0", port=port)