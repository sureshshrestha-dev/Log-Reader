import time
from functools import wraps
import threading  # Add this import

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
        
        # Only store after all validations pass
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
        """Create a LogProcessor pre-configured to filter error logs"""
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
        """Process logs based on the configured filter type"""
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
    """Process a single log file and print status"""
    print(f"Starting to process: {file_path}")
    try:
        with LogProcessor(file_path) as processor:
            # Count and process logs
            error_count = 0
            for log_entry in processor.process_logs():
                # Just iterate to 'consume' the generator
                error_count += 1
            print(f"Finished {file_path} - Found {error_count} error logs")
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")


@time_execution
def main():
    print("=" * 50)
    print("SINGLE THREADED PROCESSING (for comparison)")
    print("=" * 50)
    
    # Single-threaded processing (baseline)
    process_single_file('text.txt')
    process_single_file('large.txt')
    
    print("\n" + "=" * 50)
    print("MULTI-THREADED PROCESSING")
    print("=" * 50)
    
    # Create threads for both files
    thread1 = threading.Thread(target=process_single_file, args=('text.txt',))
    thread2 = threading.Thread(target=process_single_file, args=('large.txt',))
    
    # Start both threads (they run concurrently!)
    thread1.start()
    thread2.start()
    
    # Wait for both threads to complete
    thread1.join()
    thread2.join()
    
    print("\n✅ Both files processed concurrently!")
    
    # Optional: Demonstrate with ErrorLogProcessor
    print("\n" + "=" * 50)
    print("PROCESSING WITH ERRORLogProcessor (Threaded)")
    print("=" * 50)
    
    def process_with_error_processor(file_path):
        with ErrorLogProcessor(file_path) as processor:
            print(f"Processing {file_path} with ErrorLogProcessor")
            for log_entry in processor.process_logs():
                print(f"  {log_entry[:50]}...")  # Print first 50 chars
            print(f"Finished {file_path} - Total lines: {len(processor)}")
    
    thread3 = threading.Thread(target=process_with_error_processor, args=('text.txt',))
    thread4 = threading.Thread(target=process_with_error_processor, args=('large.txt',))
    
    thread3.start()
    thread4.start()
    
    thread3.join()
    thread4.join()

if __name__ == "__main__":
    # Create a sample large.txt file if it doesn't exist
    try:
        with open('large.txt', 'r') as f:
            pass
    except FileNotFoundError:
        print("Creating sample large.txt file...")
        with open('large.txt', 'w') as f:
            for i in range(100):
                if i % 10 == 0:
                    f.write(f"ERROR: Sample error log {i}\n")
                else:
                    f.write(f"INFO: Sample info log {i}\n")
        print("Created large.txt with sample data\n")
    
    main()


# By running two threads, you made your program I/O concurrent.
#  Even though the GIL prevents two Python threads from running Python calculations at the exact same microsecond,
#  while thread1 is waiting for the disk to give it a line of text, the GIL is released, 
# and thread2 can start reading its file. You effectively overlapped the "waiting" time!