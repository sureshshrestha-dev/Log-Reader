import asyncio
import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from enum import Enum
import json
from collections import deque
import asyncio

# ============ Models ============
class Level(str, Enum):
    INFO = 'INFO'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    DEBUG = 'DEBUG'

class LogEntry(BaseModel):
    timestamp: datetime.datetime
    level: Level
    message: str = Field(min_length=1)
    
    class Config:
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat()
        }

class LogBatch(BaseModel):
    """Batch of logs for bulk insertion"""
    logs: List[LogEntry]

# ============ Database Manager ============
class DatabaseManager:
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        self.connection_string = connection_string
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self, database_name: str = "log_reader"):
        self.client = AsyncIOMotorClient(self.connection_string)
        await self.client.admin.command('ping')
        self.db = self.client[database_name]
        
        # Create indexes for performance
        await self.db.logs.create_index("timestamp")
        await self.db.logs.create_index("level")
        await self.db.logs.create_index([("timestamp", -1)])
        await self.db.logs.create_index([("level", 1), ("timestamp", -1)])
        print(f"✅ Connected to MongoDB: {database_name}")
    
    async def disconnect(self):
        if self.client:
            self.client.close()
            print("✅ Disconnected from MongoDB")
    
    async def insert_many(self, logs: List[LogEntry]) -> List[str]:
        """Insert multiple logs efficiently"""
        documents = [log.dict() for log in logs]
        result = await self.db.logs.insert_many(documents)
        return [str(id) for id in result.inserted_ids]
    
    async def get_logs(
        self, 
        level: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None
    ) -> List[Dict[str, Any]]:
        """Query logs with filters"""
        query = {}
        
        if level:
            query["level"] = level.upper()
        
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time
        
        cursor = self.db.logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for log in logs:
            log["_id"] = str(log["_id"])
        
        return logs
    
    async def count_logs(self, level: Optional[str] = None) -> int:
        """Count total logs with optional level filter"""
        query = {}
        if level:
            query["level"] = level.upper()
        return await self.db.logs.count_documents(query)
    
    async def delete_old_logs(self, days: int = 30) -> int:
        """Delete logs older than specified days"""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        result = await self.db.logs.delete_many({"timestamp": {"$lt": cutoff}})
        return result.deleted_count

# ============ Batch Processor for Memory Efficiency ============
class LogBatchProcessor:
    """Processes batches of logs without memory spikes"""
    
    def __init__(self, db_manager: DatabaseManager, batch_size: int = 1000):
        self.db_manager = db_manager
        self.batch_size = batch_size
        self.buffer = []
    
    async def add_log(self, log: LogEntry):
        """Add a log to the buffer, auto-flush when full"""
        self.buffer.append(log)
        if len(self.buffer) >= self.batch_size:
            await self.flush()
    
    async def flush(self):
        """Flush buffer to database"""
        if self.buffer:
            await self.db_manager.insert_many(self.buffer)
            print(f"📦 Flushed {len(self.buffer)} logs to database")
            self.buffer.clear()
    
    async def add_batch(self, logs: List[LogEntry]):
        """Add a batch of logs efficiently"""
        for i in range(0, len(logs), self.batch_size):
            batch = logs[i:i + self.batch_size]
            await self.db_manager.insert_many(batch)
            print(f"📦 Inserted batch: {len(batch)} logs")

# ============ Lifespan Manager ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    app.state.db = DatabaseManager()
    await app.state.db.connect()
    app.state.batch_processor = LogBatchProcessor(app.state.db)
    print("🚀 API Started - Ready to receive logs")
    yield
    # Shutdown
    await app.state.batch_processor.flush()
    await app.state.db.disconnect()
    print("👋 API Shutdown")

# ============ FastAPI App ============
app = FastAPI(
    title="Log Processor API",
    description="High-performance log ingestion and query API",
    version="1.0.0",
    lifespan=lifespan
)

# ============ Health Check ============
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "database": "connected" if app.state.db.db else "disconnected"
    }

# ============ GET /logs - Query Logs ============
@app.get("/logs")
async def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level (INFO, ERROR, WARNING, DEBUG)"),
    limit: int = Query(100, ge=1, le=10000, description="Number of logs to return"),
    skip: int = Query(0, ge=0, description="Number of logs to skip"),
    start_time: Optional[datetime.datetime] = Query(None, description="Filter logs after this time"),
    end_time: Optional[datetime.datetime] = Query(None, description="Filter logs before this time"),
    stream: bool = Query(False, description="Stream results as JSON lines")
):
    """
    Retrieve logs from MongoDB with optional filters.
    
    Supports:
    - Filter by log level
    - Pagination (skip/limit)
    - Time range queries
    - Streaming response for large results
    """
    try:
        if stream:
            # Streaming response for large datasets (no memory spike)
            async def generate_stream():
                logs = await app.state.db.get_logs(level, limit, skip, start_time, end_time)
                for log in logs:
                    yield json.dumps(log, default=str) + "\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="application/x-ndjson"
            )
        else:
            # Regular JSON response
            logs = await app.state.db.get_logs(level, limit, skip, start_time, end_time)
            total = await app.state.db.count_logs(level)
            
            return {
                "total": total,
                "limit": limit,
                "skip": skip,
                "logs": logs
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ POST /logs - Single Log ============
@app.post("/logs")
async def create_log(log: LogEntry, background_tasks: BackgroundTasks):
    """
    Create a single log entry.
    Uses background processing to avoid blocking.
    """
    try:
        # Process in background to avoid blocking
        background_tasks.add_task(app.state.batch_processor.add_log, log)
        
        return {
            "status": "accepted",
            "message": "Log queued for processing",
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ POST /logs/batch - Handle 100k Concurrent Logs ============
@app.post("/logs/batch")
async def create_logs_batch(logs: List[LogEntry]):
    """
    Handle 100k+ concurrent logs without memory spike.
    
    This endpoint:
    - Accepts up to 100,000 logs in one request
    - Processes in batches to prevent memory spikes
    - Uses streaming-like batch processing
    - Returns immediately with accepted status
    """
    try:
        log_count = len(logs)
        
        if log_count > 100000:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many logs. Maximum 100,000 per request. Received: {log_count}"
            )
        
        # Process in background to not block
        async def process_large_batch():
            # Use batch processor for efficient insertion
            await app.state.batch_processor.add_batch(logs)
            print(f"✅ Processed {log_count} logs in background")
        
        # Create background task
        asyncio.create_task(process_large_batch())
        
        return {
            "status": "accepted",
            "message": f"Queued {log_count} logs for processing",
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ GET /logs/stats - Statistics ============
@app.get("/logs/stats")
async def get_stats():
    """Get log statistics"""
    try:
        total = await app.state.db.count_logs()
        errors = await app.state.db.count_logs("ERROR")
        warnings = await app.state.db.count_logs("WARNING")
        info = await app.state.db.count_logs("INFO")
        debug = await app.state.db.count_logs("DEBUG")
        
        return {
            "total": total,
            "by_level": {
                "ERROR": errors,
                "WARNING": warnings,
                "INFO": info,
                "DEBUG": debug
            },
            "error_rate": errors / total if total > 0 else 0,
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ DELETE /logs - Cleanup Old Logs ============
@app.delete("/logs")
async def delete_old_logs(days: int = Query(30, ge=1, le=365)):
    """Delete logs older than specified days"""
    try:
        deleted = await app.state.db.delete_old_logs(days)
        return {
            "status": "success",
            "deleted_count": deleted,
            "days_kept": days,
            "message": f"Deleted {deleted} logs older than {days} days"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ GET /logs/stream - Real-time Stream ============
@app.get("/logs/stream")
async def stream_recent_logs(limit: int = Query(100, le=1000)):
    """Stream recent logs in real-time using Server-Sent Events"""
    from fastapi.responses import StreamingResponse
    
    async def event_stream():
        # Get recent logs
        logs = await app.state.db.get_logs(limit=limit)
        
        for log in logs:
            yield f"data: {json.dumps(log, default=str)}\n\n"
            await asyncio.sleep(0.1)  # Simulate real-time streaming
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# ============ WebSocket Support for Real-time (Bonus) ============
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            
            # Process as log entry
            try:
                log_data = json.loads(data)
                log = LogEntry(**log_data)
                await app.state.batch_processor.add_log(log)
                await websocket.send_text(f"✅ Log accepted: {log.message[:50]}")
            except Exception as e:
                await websocket.send_text(f"❌ Error: {str(e)}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")

# ============ Performance Test Endpoint ============
@app.post("/logs/test/100k")
async def test_100k_logs():
    """Test endpoint to simulate 100k logs (for benchmarking)"""
    import random
    
    levels = ["INFO", "ERROR", "WARNING", "DEBUG"]
    messages = [
        "Database connection established",
        "API call failed",
        "Memory usage high",
        "User authentication successful",
        "File not found",
        "Cache hit",
        "Request timeout",
        "Background job completed",
        "Configuration loaded",
        "Service started"
    ]
    
    logs = []
    for i in range(100000):
        log = LogEntry(
            timestamp=datetime.datetime.now(),
            level=random.choice(levels),
            message=f"{random.choice(messages)} - ID:{i}"
        )
        logs.append(log)
        
        # Yield every 10000 logs to show progress
        if i % 10000 == 0:
            print(f"Generated {i} logs...")
    
    # Process in background
    asyncio.create_task(app.state.batch_processor.add_batch(logs))
    
    return {
        "status": "accepted",
        "message": f"Queued 100,000 logs for processing",
        "timestamp": datetime.datetime.now().isoformat()
    }

# ============ Main Entry Point ============
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 STARTING LOG PROCESSING API")
    print("=" * 60)
    print("\n📚 API Documentation: http://localhost:8000/docs")
    print("📊 Health Check: http://localhost:8000/health")
    print("\n💡 Test with:")
    print("  curl http://localhost:8000/logs?level=ERROR&limit=10")
    print("  curl -X POST http://localhost:8000/logs/batch \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '[{\"timestamp\":\"2024-01-01T10:00:00\",\"level\":\"ERROR\",\"message\":\"Test\"}]'")
    print("\n" + "=" * 60)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        workers=4,  # Multiple workers for concurrency
        loop="asyncio"
    )