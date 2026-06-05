import time
from functools import wraps

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

        # file.seek(0) Reset file pointer to beginning
        # logic perfectly—that is a classic move when you need to consume a file stream twice (once to count, once to process).
        #  Many developers forget to reset the pointer and end up with an empty file on the second read!
        self.file.seek(0)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        return False  # Re-raise any exceptions

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

# NEW CLASS: Inherits from LogProcessor
class ErrorLogProcessor(LogProcessor):
    def __init__(self, file_path):
        # Force the filter_type to 'error' by calling parent's __init__
        super().__init__(file_path, filter_type='error')
        
    def process_logs(self):
        # Add [CRITICAL] prefix to every log
        # Call parent's process_logs() first, then add extra logic
        for log in super().process_logs():
            yield f"[CRITICAL] {log}"

@time_execution
def main():
    # Using the inherited ErrorLogProcessor class instead of the factory method
    with ErrorLogProcessor('text.txt') as processor:
        for log_entry in processor.process_logs():
            print(log_entry)
        print(f"Total log entries: {len(processor)}")
        print(str(processor))
        print(repr(processor))

  # This will fail validation (for demonstration)
    print("\n--- Testing validation ---")
    try:
        invalid_processor = LogProcessor('text.log')
    except ValueError as e:
        print(f"❌ Validation caught: {e}")
    
    try:
        invalid_processor2 = LogProcessor(123)
    except ValueError as e:
        print(f"❌ Validation caught: {e}")

if __name__ == "__main__":
    main()