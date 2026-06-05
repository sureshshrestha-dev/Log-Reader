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

def log_generator(file_object):
    for line in file_object:
        yield line.strip()

def filter_error_logs(log_stream):
    for log_entry in log_stream:
        if 'ERROR' in log_entry:
            yield log_entry + ' need fix'

class LogFileHandler:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file = None

    def __enter__(self):
        self.file = open(self.file_path, 'r')
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        return False

@time_execution
def main(file_object):
    logs = log_generator(file_object)
    error_logs = filter_error_logs(logs)
    for error in error_logs:
        print(error)

if __name__ == "__main__":
    with LogFileHandler('text.txt') as file:
        main(file)