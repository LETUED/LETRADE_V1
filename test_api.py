"""Standalone test script for REST API."""

import sys
import os

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI
import uvicorn

# Simple test app
app = FastAPI(
    title="Letrade V1 Trading System API",
    description="REST API for cryptocurrency trading system management and monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "Letrade V1 Trading System API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-06-24T05:41:00Z"
    }

if __name__ == "__main__":
    print("🚀 Starting Letrade V1 REST API...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("📋 ReDoc Documentation: http://localhost:8000/redoc")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )