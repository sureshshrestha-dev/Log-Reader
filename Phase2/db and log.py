import datetime
from typing import Optional, List, Generator
from enum import Enum
from pydantic import BaseModel, Field, field_validator , ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import asyncio
import re
import os

class Level(str, Enum):
    INFO = 'INFO'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    DEBUG = 'DEBUG'

class PathDescriptor:
    def __set__(self, instance, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        if not value.endswith('.txt'):
            raise ValueError("File must be a .txt file")
        instance.__dict__[self.name] = value
    
    def __get__(self, instance, owner) -> Optional[str]:
        if instance is None:
            return self
        return instance.__dict__.get(self.name, None)
    
    def __set_name__(self, owner, name: str) -> None:
        self.name = name

class LogProcessor:
    file_path = PathDescriptor()

    def __init__(self, file_path: str, filter_type: Optional[str] = None):
        self.file_path = file_path
        self.filter_type = filter_type
        self.file = None

    def __enter__(self):
        """Context manager entry for sync operations"""
        self.file = open(self.file_path, 'r')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        return False

    def process_logs(self) -> Generator[str, None, None]:
        """Yield raw log lines from file with optional filtering"""
        # Use context manager to ensure file is closed
        with open(self.file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                # Apply filter if specified
                if self.filter_type == "error" and "ERROR" not in line:
                    continue
                    
                yield line


class LogEntry(BaseModel):
    timestamp: datetime.datetime
    level: Level
    message: str = Field(min_length=1)
    
    # Use ConfigDict instead of class Config
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            datetime.datetime: lambda v: v.isoformat()
        }
    )
    
    # Rest of your code remains the same...
    
    def to_mongo(self) -> dict:
        """Convert to MongoDB document"""
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "message": self.message,
            "created_at": datetime.datetime.now(),
            "year": self.timestamp.year,  # For easy partitioning
            "month": self.timestamp.month
        }
    
    @classmethod
    def from_mongo(cls, document: dict) -> 'LogEntry':
        """Create from MongoDB document"""
        return cls(
            timestamp=document["timestamp"],
            level=Level(document["level"]),
            message=document["message"]
        )

# ============ MongoDB Storage Layer ============
class LogDocument:
    COLLECTION_NAME = "logs"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.COLLECTION_NAME]
    
    async def create_indexes(self):
        """Create indexes for efficient queries"""
        await self.collection.create_index("timestamp")
        await self.collection.create_index("level")
        await self.collection.create_index([("timestamp", -1)])  # Descending
        await self.collection.create_index([("level", 1), ("timestamp", -1)])
        await self.collection.create_index("year")  # For time-based partitioning
        print("✅ MongoDB indexes created")

    async def insert_one(self, log_entry: LogEntry) -> str:
        """Insert a single log entry"""
        document = log_entry.to_mongo()
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)
    
    async def insert_many(self, log_entries: List[LogEntry]) -> List[str]:
        """Insert multiple log entries"""
        documents = [log.to_mongo() for log in log_entries]
        result = await self.collection.insert_many(documents)
        return [str(id) for id in result.inserted_ids]
    
    async def count_all(self) -> int:
        """Get total document count"""
        return await self.collection.count_documents({})

# ============ Database Manager ============
class DatabaseManager:
    """Manages MongoDB connection with async context management"""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        self.connection_string = connection_string
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.logs: Optional[LogDocument] = None
    
    async def connect(self, database_name: str = "log_reader"):
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(self.connection_string)
        
        # Test connection
        await self.client.admin.command('ping')
        
        self.db = self.client[database_name]
        self.logs = LogDocument(self.db)
        await self.logs.create_indexes()
        print(f"✅ Connected to MongoDB database: {database_name}")
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            print("✅ Disconnected from MongoDB")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

# ============ Fixed LogProcessorWithDB ============
class LogProcessorWithDB(LogProcessor):
    """LogProcessor that maps text logs to Pydantic, then stores them to MongoDB"""
    
    def __init__(self, file_path: str, db_manager: DatabaseManager, filter_type: Optional[str] = None):
        super().__init__(file_path, filter_type)
        self.db_manager = db_manager
        self.stored_logs = []
    
    def _parse_line_to_pydantic(self, raw_line: str) -> Optional[LogEntry]:
        """
        Parse a raw log line into a structured LogEntry.
        
        Supports formats:
        - "2026-06-05 12:00:00 [ERROR] message"
        - "[ERROR] message"
        - "ERROR: message"
        """
        if not raw_line:
            return None
        
        # Parse timestamp (if present)
        timestamp = None
        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', raw_line)
        
        if timestamp_match:
            try:
                timestamp = datetime.datetime.strptime(
                    timestamp_match.group(1), 
                    "%Y-%m-%d %H:%M:%S"
                )
                # Remove timestamp from line for further parsing
                raw_line = raw_line[timestamp_match.end():].strip()
            except ValueError:
                timestamp = datetime.datetime.now()
        else:
            timestamp = datetime.datetime.now()
        
        # Parse level
        level = Level.INFO  # Default
        
        # Check for [LEVEL] format
        bracket_match = re.search(r'\[(\w+)\]', raw_line)
        if bracket_match:
            level_str = bracket_match.group(1).upper()
            if level_str in Level.__members__:
                level = Level[level_str]
                # Remove level from message
                raw_line = raw_line[:bracket_match.start()] + raw_line[bracket_match.end():]
        
        # Check for LEVEL: format
        elif ':' in raw_line:
            parts = raw_line.split(':', 1)
            level_str = parts[0].strip().upper()
            if level_str in Level.__members__:
                level = Level[level_str]
                raw_line = parts[1].strip()
        
        # Clean up message
        message = raw_line.strip()
        if not message:
            message = "No message content"
        
        # Create and validate LogEntry
        try:
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message
            )
        except Exception as e:
            print(f"⚠️ Failed to parse line: {raw_line[:50]}... Error: {e}")
            return None
    
    async def process_and_store(self, batch_size: int = 100):
        """
        Process log entries and stream them to the database in batches.
        
        Args:
            batch_size: Number of logs to insert in one batch
        """
        batch = []
        total_processed = 0
        
        async with self.db_manager as db:
            for raw_line in self.process_logs():
                # Parse to Pydantic entry
                log_entry = self._parse_line_to_pydantic(raw_line)
                
                if log_entry is None:
                    continue
                
                # Add to batch
                batch.append(log_entry)
                total_processed += 1
                
                # Insert batch when it reaches size limit
                if len(batch) >= batch_size:
                    log_ids = await db.logs.insert_many(batch)
                    
                    # Report progress
                    error_count = sum(1 for log in batch if log.level == Level.ERROR)
                    print(f"📦 Inserted batch: {len(batch)} logs ({error_count} errors)")
                    
                    # Store for reference
                    for log_id, log_entry in zip(log_ids, batch):
                        self.stored_logs.append((log_id, log_entry))
                    
                    # Clear batch
                    batch = []
            
            # Insert remaining logs
            if batch:
                log_ids = await db.logs.insert_many(batch)
                error_count = sum(1 for log in batch if log.level == Level.ERROR)
                print(f"📦 Inserted final batch: {len(batch)} logs ({error_count} errors)")
                
                for log_id, log_entry in zip(log_ids, batch):
                    self.stored_logs.append((log_id, log_entry))
        
        # Final statistics
        total_errors = sum(1 for _, log in self.stored_logs if log.level == Level.ERROR)
        print(f"\n✅ Pipeline complete!")
        print(f"   Total logs processed: {total_processed}")
        print(f"   Total logs stored: {len(self.stored_logs)}")
        print(f"   Total errors found: {total_errors}")
        
        return self.stored_logs

# ============ Sample Log File Creator ============
def create_sample_log_file(filename: str = "production_logs.txt"):
    """Create a sample log file for testing"""
    sample_logs = [
        "2026-06-05 12:00:00 [INFO] Application started successfully",
        "2026-06-05 12:01:00 [ERROR] Database connection failed: timeout after 30s",
        "2026-06-05 12:02:00 [WARNING] Memory usage at 80%",
        "2026-06-05 12:03:00 [INFO] Processing user request #12345",
        "2026-06-05 12:04:00 [ERROR] API call failed: 500 Internal Server Error",
        "2026-06-05 12:05:00 [DEBUG] Cache hit for key: user:123",
        "2026-06-05 12:06:00 [ERROR] Segmentation fault in module X",
        "2026-06-05 12:07:00 [INFO] Request completed in 234ms",
        "2026-06-05 12:08:00 [WARNING] Deprecated API endpoint used",
        "2026-06-05 12:09:00 [ERROR] Disk space low: only 5GB remaining",
    ]
    
    with open(filename, 'w') as f:
        for log in sample_logs:
            f.write(log + '\n')
    
    print(f"✅ Created sample log file: {filename}")

# ============ Main Execution ============
async def main():
    """Main execution function"""
    print("=" * 60)
    print("LOG PROCESSOR WITH MONGODB INTEGRATION")
    print("=" * 60)
    
    # Create sample file if it doesn't exist
    if not os.path.exists("production_logs.txt"):
        create_sample_log_file()
    
    # Initialize database manager
    db_manager = DatabaseManager("mongodb://localhost:27017")
    
    # Create and run processor
    processor = LogProcessorWithDB(
        file_path="production_logs.txt",
        db_manager=db_manager,
        filter_type=None  # Process all logs (not just errors)
    )
    
    # Process and store logs
    stored_logs = await processor.process_and_store(batch_size=5)
    
    # Display some statistics
    print("\n" + "=" * 60)
    print("STORAGE STATISTICS")
    print("=" * 60)
    
    async with db_manager as db:
        total_count = await db.logs.count_all()
        print(f"📊 Total documents in database: {total_count}")
    
    print("\n📝 Sample of stored logs:")
    for i, (log_id, log_entry) in enumerate(stored_logs[:5]):
        print(f"  {i+1}. [{log_entry.timestamp}] {log_entry.level.value}: {log_entry.message[:50]}...")
        print(f"     MongoDB ID: {log_id}")

# ============ Run the Application ============
if __name__ == "__main__":
    print("\n⚠️  Make sure MongoDB is running:")
    print("   docker run -d -p 27017:27017 --name mongodb mongo:latest")
    print()
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Install MongoDB: https://docs.mongodb.com/manual/installation/")
        print("   2. Or use Docker: docker run -d -p 27017:27017 --name mongodb mongo")
        print("   3. Install motor: pip install motor")