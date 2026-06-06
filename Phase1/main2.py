import time
from functools import wraps
import threading
import asyncio
import datetime
from dataclasses import dataclass
from typing import List, Optional, Generator, Iterator
from enum import Enum
import re

from pydantic import BaseModel, Field, field_validator
class Level(Enum):
    INFO = 'INFO'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    DEBUG = 'DEBUG'

# @dataclass
# class LogEntry:
#     timestamp: datetime.datetime
#     level: Level
#     message: str

class LogEntry(BaseModel):
    timestamp: datetime.datetime
    level: Level
    message: str = Field(min_length=1)

    # This ensures that even if someone creates the object manually, 
    # it must have a non-empty message.
    
    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.level.value}: {self.message}"
    
    def is_error(self) -> bool:
        """Check if this is an error log"""
        return self.level == Level.ERROR

def time_execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Execution time: {end_time - start_time} seconds")
        return result
    return wrapper


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
    file_path: str = PathDescriptor()
    
    def __init__(self, file_path: str, filter_type: Optional[str] = None) -> None:
        self.file_path = file_path
        self.filter_type = filter_type
        self.file = None
        self.line_count: int = 0

    @classmethod
    def for_errors(cls, file_path: str) -> 'LogProcessor':
        """Create a LogProcessor pre-configured to filter error logs"""
        instance = cls(file_path, filter_type="error")
        return instance
    
    def __enter__(self) -> 'LogProcessor':
        self.file = open(self.file_path, 'r')
        self.line_count = sum(1 for _ in self.file)
        self.file.seek(0)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.file:
            self.file.close()
        return False  # Re-raise any exceptions

    def __len__(self) -> int:
        return self.line_count

    def __str__(self) -> str:
        return f"LogProcessor for file: {self.file_path} with filter: {self.filter_type}"

    def __repr__(self) -> str:
        return f"LogProcessor({self.file_path}, {self.filter_type})"
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """
        Parse a raw log line into a LogEntry object.
        Expected format: "INFO: Message" or "ERROR: Message"
        For real logs: "2024-01-01 10:00:00 - ERROR - Database connection failed"
        """
        line = line.strip()
        if not line:
            return None
        
        # Try to parse different log formats
        # Format 1: "LEVEL: message"
        if ':' in line:
            parts = line.split(':', 1)
            level_str = parts[0].strip().upper()
            message = parts[1].strip()
            
            # Convert string to Level enum
            try:
                level = Level[level_str]
            except KeyError:
                # Default to INFO if level not recognized
                level = Level.INFO
            
            # Use current timestamp if none provided
            timestamp = datetime.datetime.now()
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message
            )
        
        # Format 2: Assume INFO if no level specified
        return LogEntry(
            timestamp=datetime.datetime.now(),
            level=Level.INFO,
            message=line
        )
    
    def process_logs(self) -> Generator[LogEntry, None, None]:
        """
        Process logs and yield LogEntry objects.
        Yields LogEntry objects based on the configured filter type.
        """
        for line in self.file:
            parsed_log = self._parse_log_line(line)
            
            if parsed_log is None:
                continue
            
            # Apply filter if specified
            if self.filter_type == "error":
                if parsed_log.level == Level.ERROR:
                    yield parsed_log
            else:
                # Default: yield all logs
                yield parsed_log
    
    def get_errors(self) -> List[LogEntry]:
        """Get all error logs as a list"""
        return [log for log in self.process_logs() if log.level == Level.ERROR]
    
    def get_logs_by_level(self, level: Level) -> List[LogEntry]:
        """Get logs filtered by specific level"""
        return [log for log in self.process_logs() if log.level == level]
    
    def get_error_messages(self) -> List[str]:
        """Get just the error messages (legacy support)"""
        return [log.message for log in self.process_logs() if log.level == Level.ERROR]


class ErrorLogProcessor(LogProcessor):
    def __init__(self, file_path: str) -> None:
        super().__init__(file_path, filter_type='error')
    
    def process_logs(self) -> Generator[LogEntry, None, None]:
        """Process logs and add CRITICAL prefix to error messages"""
        for log in super().process_logs():
            # Modify the message but keep the LogEntry structure
            log.message = f"[CRITICAL] {log.message}"
            yield log


def process_single_file(file_path: str) -> None:
    """Synchronous version that uses the new LogEntry structure"""
    print(f"Starting to process: {file_path}")
    try:
        with LogProcessor(file_path) as processor:
            errors: List[LogEntry] = []
            for log_entry in processor.process_logs():
                if log_entry.is_error():
                    errors.append(log_entry)
                    print(f"  Found error: {log_entry}")
            
            print(f"Finished {file_path} - Found {len(errors)} error logs")
            
            # Demonstrate accessing LogEntry attributes
            if errors:
                first_error = errors[0]
                print(f"  First error timestamp: {first_error.timestamp}")
                print(f"  First error level: {first_error.level.value}")
                print(f"  First error message: {first_error.message}")
                
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")


def process_with_type_hints_example():
    """Demonstrate type hints in action"""
    # Type hints help with IDE autocomplete and error checking
    
    processor: LogProcessor = LogProcessor('text.txt')
    
    # Now we know process_logs returns Generator[LogEntry, None, None]
    logs: Generator[LogEntry, None, None] = processor.process_logs()
    
    # We can collect into a list with proper typing
    log_list: List[LogEntry] = list(processor.process_logs())
    
    # Optional type for values that might be None
    first_log: Optional[LogEntry] = log_list[0] if log_list else None
    
    # Error logs as typed list
    error_logs: List[LogEntry] = [log for log in log_list if log.level == Level.ERROR]
    
    print(f"Total logs: {len(log_list)}")
    print(f"Error logs: {len(error_logs)}")
    
    if first_log:
        print(f"First log: {first_log}")


@time_execution
def main_sync():
    """Synchronous main function to test the refactored LogProcessor"""
    print("=" * 60)
    print("TESTING REFACTORED LOGPROCESSOR WITH LOGENTRY")
    print("=" * 60)
    
    # Create sample files
    import os
    if not os.path.exists('text.txt'):
        create_sample_files()
    
    # Process with the new LogEntry structure
    process_single_file('text.txt')
    
    print("\n" + "=" * 60)
    print("DEMONSTRATING TYPE HINTS")
    print("=" * 60)
    
    # Demonstrate the typed approach
    with LogProcessor('text.txt') as processor:
        # Get all errors as LogEntry objects
        error_entries: List[LogEntry] = processor.get_errors()
        
        print(f"\nFound {len(error_entries)} error(s):")
        for error in error_entries:
            print(f"  • [{error.timestamp.strftime('%H:%M:%S')}] {error.message}")
        
        # Get just the messages (legacy support)
        error_messages: List[str] = processor.get_error_messages()
        print(f"\nError messages only: {error_messages}")
        
        # Filter by level
        info_logs: List[LogEntry] = processor.get_logs_by_level(Level.INFO)
        print(f"\nInfo logs: {len(info_logs)}")


# ============ SIMPLE EXAMPLE OF THE REFACTOR ============
def simple_demo():
    """Simple demo showing the before/after of refactoring"""
    
    # BEFORE (raw strings)
    print("=== BEFORE REFACTOR (Raw Strings) ===")
    raw_logs = ["ERROR: Database failed", "INFO: Server started"]
    for log in raw_logs:
        if 'ERROR' in log:
            print(f"Error found: {log}")
    
    # AFTER (LogEntry objects)
    print("\n=== AFTER REFACTOR (LogEntry Objects) ===")
    log_entries = [
        LogEntry(timestamp=datetime.datetime.now(), level=Level.ERROR, message="Database failed"),
        LogEntry(timestamp=datetime.datetime.now(), level=Level.INFO, message="Server started")
    ]
    
    for log in log_entries:
        if log.is_error():
            print(f"Error found: {log.message}")
            print(f"  Level: {log.level.value}")
            print(f"  Time: {log.timestamp}")
    
    # Benefits of structured data
    print("\n=== BENEFITS ===")
    print("✓ Type safety with enums")
    print("✓ Easy filtering by level")
    print("✓ Structured timestamp for sorting")
    print("✓ IDE autocomplete works!")
    print("✓ Can add methods like .is_error()")


# ============ CREATE SAMPLE FILES ============
def create_sample_files():
    """Create sample log files for testing"""
    
    # Create text.txt with proper format
    with open('text.txt', 'w') as f:
        f.write("INFO: Application started\n")
        f.write("ERROR: Database connection failed\n")
        f.write("INFO: Retrying connection\n")
        f.write("ERROR: Timeout occurred after 30 seconds\n")
        f.write("WARNING: Memory usage high\n")
        f.write("INFO: Application shutdown\n")
    
    # Create large.txt
    with open('large.txt', 'w') as f:
        for i in range(100):
            if i % 10 == 0:
                f.write(f"ERROR: Sample error log {i}\n")
            elif i % 7 == 0:
                f.write(f"WARNING: Sample warning {i}\n")
            else:
                f.write(f"INFO: Sample info log {i}\n")
    
    print("✅ Sample files created: text.txt and large.txt\n")


# ============ RUN THE DEMO ============
if __name__ == "__main__":
    # Create sample files if they don't exist
    import os
    if not os.path.exists('text.txt') or not os.path.exists('large.txt'):
        create_sample_files()
    
    # Run the simple demo first
    simple_demo()
    
    print("\n" + "=" * 60)
    print("RUNNING MAIN SYNC DEMO")
    print("=" * 60)
    
    # Run the main demo
    main_sync()
    
    # Uncomment to run async version
    # asyncio.run(main())