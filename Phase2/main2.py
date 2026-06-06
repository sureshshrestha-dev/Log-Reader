import time
from functools import wraps
import threading
import asyncio
import datetime
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class Level(Enum):
    INFO = 'INFO'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    DEBUG = 'DEBUG'

@dataclass
class LogEntry:
    timestamp: datetime.datetime
    level: Level
    message: str

def time_execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Execution time: {end_time - start_time} seconds")
        return result
    return wrapper

def filter_error_logs(log_stream):
    for log_entry in log_stream:
        if 'ERROR' in log_entry:
            yield log_entry + ' need fix'


class PathDescriptor:
    def __set__(self, instance, value):
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        
        if not value.endswith('.txt'):
            raise ValueError("File must be a .txt file")
        
        instance.__dict__[self.name] = value
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name, None)
    
    def __set_name__(self, owner, name):
        self.name = name

        
class LogProcessor:
    file_path = PathDescriptor()

    def __init__(self, file_path, filter_type=None):
        self.file_path = file_path
        self.filter_type = filter_type
        self.file = None
        self.line_count = 0

    @classmethod
    def for_errors(cls, file_path):
        instance = cls(file_path, filter_type="error")
        return instance
    
    def __enter__(self):
        self.file = open(self.file_path, 'r')
        self.line_count = sum(1 for _ in self.file)
        self.file.seek(0)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        return False

    def __len__(self):
        return self.line_count

    def __str__(self):
        return f"LogProcessor for file: {self.file_path} with filter: {self.filter_type}"

    def __repr__(self):
        return f"LogProcessor({self.file_path}, {self.filter_type})"
    
    def process_logs(self):
        for line in self.file:
            stripped_line = line.strip()
            
            if self.filter_type == "error":
                if 'ERROR' in stripped_line:
                    yield stripped_line + ' need fix'
            else:
                yield stripped_line


class ErrorLogProcessor(LogProcessor):
    def __init__(self, file_path):
        super().__init__(file_path, filter_type='error')
        
    def process_logs(self):
        for log in super().process_logs():
            yield f"[CRITICAL] {log}"


def process_single_file(file_path):
    """Synchronous version for comparison"""
    print(f"Starting to process: {file_path}")
    try:
        with LogProcessor(file_path) as processor:
            error_count = 0
            for log_entry in processor.process_logs():
                error_count += 1
            print(f"Finished {file_path} - Found {error_count} error logs")
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")


# ============ ASYNC VERSION ============
@time_execution
async def process_log_async(file_path):
    """
    Async version of log processing.
    This would use aiofiles in real implementation.
    """
    print(f"🚀 Async: Starting to process {file_path}")
    
    # Simulate async file reading (since we don't have aiofiles installed)
    # In real code, you would do:
    # async with aiofiles.open(file_path, mode='r') as f:
    #     async for line in f:
    #         if 'ERROR' in line:
    #             print(f"Found error in {file_path}")
    
    # Simulated async processing (for demonstration)
    try:
        # Simulate reading a file asynchronously
        with open(file_path, 'r') as f:  # In real code, use aiofiles
            lines = f.readlines()
            error_count = 0
            for line in lines:
                # Simulate async I/O operation (like sending to database)
                await asyncio.sleep(0)  # Yield control to event loop
                if 'ERROR' in line:
                    error_count += 1
                    # Simulate async network call
                    await asyncio.sleep(0.001)
            
            print(f"✅ Async: Finished {file_path} - Found {error_count} errors")
    except FileNotFoundError:
        print(f"❌ Async: File not found - {file_path}")
    except Exception as e:
        print(f"❌ Async: Error processing {file_path} - {e}")

# ============ THREADING VERSION (for comparison) ============
@time_execution
def run_with_threading():
    """Run using threading (traditional concurrency)"""
    print("\n" + "=" * 60)
    print("RUNNING WITH THREADING")
    print("=" * 60)
    
    thread1 = threading.Thread(target=process_single_file, args=('text.txt',))
    thread2 = threading.Thread(target=process_single_file, args=('large.txt',))
    
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()
    
    print("\n✅ Threading completed!\n")


# ============ ASYNC VERSION (THE CHALLENGE SOLUTION) ============
@time_execution
async def run_with_async():
    """Run using asyncio (modern async concurrency)"""
    print("\n" + "=" * 60)
    print("RUNNING WITH ASYNCIO")
    print("=" * 60)
    
    # Create async tasks for both files
    task1 = process_log_async('text.txt')
    task2 = process_log_async('large.txt')
    
    # Run them concurrently using asyncio.gather
    await asyncio.gather(task1, task2)
    
    print("\n✅ Async completed!\n")


# ============ ALTERNATIVE: Process many files concurrently ============
async def process_multiple_files(file_paths):
    """Process multiple files concurrently using asyncio.gather"""
    tasks = [process_log_async(file_path) for file_path in file_paths]
    await asyncio.gather(*tasks)


# ============ ADVANCED: With timeout and error handling ============
async def process_with_timeout(file_path, timeout_seconds=5):
    """Process file with timeout protection"""
    try:
        await asyncio.wait_for(process_log_async(file_path), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        print(f"⏰ Timeout processing {file_path} after {timeout_seconds} seconds")


@time_execution
async def main():
    """Main async function that coordinates everything"""
    
    # Demonstration of different approaches
    
    # 1. Sequential async (not concurrent)
    print("=" * 60)
    print("SEQUENTIAL ASYNC (one after another)")
    print("=" * 60)
    await process_log_async('text.txt')
    await process_log_async('large.txt')
    
    # 2. Concurrent async (THE CHALLENGE SOLUTION)
    print("\n" + "=" * 60)
    print("CONCURRENT ASYNC (using asyncio.gather)")
    print("=" * 60)
    
    # This is the answer to the challenge!
    # Run both tasks at the SAME time using asyncio.gather
    await asyncio.gather(
        process_log_async('text.txt'),
        process_log_async('large.txt')
    )
    
    # 3. Process multiple files dynamically
    print("\n" + "=" * 60)
    print("PROCESSING MULTIPLE FILES")
    print("=" * 60)
    files = ['text.txt', 'large.txt']
    await process_multiple_files(files)
    
    # 4. Compare threading vs async
    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)
    
    # Run threading version (but can't call time_execution directly on async)
    run_with_threading()
    
    # Run async version
    await run_with_async()


# ============ SIMPLE CHALLENGE SOLUTION (what you asked for) ============
async def challenge_solution():
    """
    THIS IS THE DIRECT ANSWER TO YOUR CHALLENGE:
    Run two async functions at the same time using asyncio.gather
    """
    # Create the two tasks
    task1 = process_log_async('text.txt')
    task2 = process_log_async('large.txt')
    
    # Run them concurrently
    await asyncio.gather(task1, task2)
    
    # That's it! Both files are processed simultaneously


# ============ CREATE SAMPLE FILES ============
def create_sample_files():
    """Create sample log files for testing"""
    
    # Create text.txt
    with open('text.txt', 'w') as f:
        f.write("INFO: Application started\n")
        f.write("ERROR: Database connection failed\n")
        f.write("INFO: Retrying connection\n")
        f.write("ERROR: Timeout occurred\n")
        f.write("INFO: Application shutdown\n")
    
    # Create large.txt
    with open('large.txt', 'w') as f:
        for i in range(100):
            if i % 10 == 0:
                f.write(f"ERROR: Sample error log {i}\n")
            else:
                f.write(f"INFO: Sample info log {i}\n")
    
    print("✅ Sample files created: text.txt and large.txt\n")


# ============ RUN THE APPLICATION ============
if __name__ == "__main__":
    # Create sample files if they don't exist
    import os
    if not os.path.exists('text.txt') or not os.path.exists('large.txt'):
        create_sample_files()
    
    # Run the async main function
    asyncio.run(main())
    
    # Or just run the simple challenge solution:
    # asyncio.run(challenge_solution())