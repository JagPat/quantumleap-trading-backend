#!/usr/bin/env python3
"""
Minimal FastAPI app for Railway deployment testing
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create minimal FastAPI app
app = FastAPI(title="QuantumLeap Trading Backend - Minimal", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "QuantumLeap Trading Backend - Minimal Version", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "minimal"}

@app.get("/ping")
async def ping():
    return {"ping": "pong"}

@app.get("/test")
async def test():
    return {
        "status": "working",
        "port": os.environ.get("PORT", "unknown"),
        "host": "0.0.0.0",
        "message": "Railway deployment test successful"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting minimal app on port {port}")
    uvicorn.run("main_minimal:app", host="0.0.0.0", port=port)