import asyncio
import random

# Mocking the DatabaseManager and LogEntry for a runnable example
class LogEntry:
    def __init__(self, data: str):
        self.data = data

class DatabaseManager:
    async def insert_one(self, log_entry: LogEntry):
        # Simulate database network latency
        # If MongoDB gets slow, this sleep time increases
        await asyncio.sleep(random.uniform(0.1, 0.5)) 
        print(cls_color(f" Saved to DB: {log_entry.data}", "32"))

def cls_color(text, color_code):
    return f"\033[{color_code}m{text}\033[0m"

# -------------------------------------------------------------------
# 1. THE PRODUCER
# -------------------------------------------------------------------
async def producer(queue: asyncio.Queue, file_path: str):
    print(f"[Producer] Starting to read {file_path}...")
    
    # Simulating reading lines from a huge log file
    for i in range(1, 21):  
        log_entry = LogEntry(f"Log line {i} from {file_path}")
        
        print(f"[Producer] Attempting to add item {i} to queue...")
        # If the queue is full, this 'await' will pause right here!
        await queue.put(log_entry)
        print(cls_color(f"[Producer] Added item {i} to queue. (Queue size: {queue.qsize()})", "34"))
        
        # Simulate fast file reading
        await asyncio.sleep(0.05) 
        
    print("[Producer] Done reading file. Sending shutdown signal...")
    # None is a "Poison Pill" telling the consumer there is no more work left
    await queue.put(None) 

# -------------------------------------------------------------------
# 2. THE CONSUMER
# -------------------------------------------------------------------
async def consumer(queue: asyncio.Queue, db: DatabaseManager):
    print("[Consumer] Ready and waiting for logs...")
    while True:
        # Get a log entry from the queue (yields control if queue is empty)
        log_entry = await queue.get()
        
        # Check for the poison pill shutdown signal
        if log_entry is None:
            queue.task_done()
            print("[Consumer] Received shutdown signal. Exiting.")
            break
        
        # Write to MongoDB
        try:
            await db.insert_one(log_entry)
        except Exception as e:
            print(f"[Consumer] Error writing to DB: {e}")
        finally:
            # Tell the queue that this item is fully processed
            queue.task_done()

# -------------------------------------------------------------------
# 3. THE ARCHITECT'S ORCHESTRATION
# -------------------------------------------------------------------
async def main():
    # CRITICAL: We set a small maxsize (e.g., 5) to witness backpressure in action.
    # In production, this might be 1000.
    shared_queue = asyncio.Queue(maxsize=5)
    db_manager = DatabaseManager()
    
    # Start both tasks concurrently
    producer_task = asyncio.create_task(producer(shared_queue, "production_logs.txt"))
    consumer_task = asyncio.create_task(consumer(shared_queue, db_manager))
    
    # Wait until both tasks finish completely
    await asyncio.gather(producer_task, consumer_task)
    print("System processed all logs successfully without crashing.")

if __name__ == "__main__":
    asyncio.run(main())