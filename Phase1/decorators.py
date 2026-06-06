import time
from functools import wraps

# # After applying @time_execution, `main` is replaced by the decorator's
# `wrapper` function. Without functools.wraps(), metadata such as
# __name__, __doc__, and help() output will belong to `wrapper` instead
# of the original function, which can confuse debuggers, documentation
# tools, and testing frameworks like pytest.


# # @time_execution replaces `main` with `wrapper`.
# Use functools.wraps() to preserve the original function's metadata
# (__name__, __doc__, etc.) for debugging, documentation, and pytest.


def time_execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Execution time: {end_time - start_time} seconds")
        return result
    return wrapper

@time_execution
def add(a, b):
    time.sleep(1)
    return a + b

if  __name__ == "__main__":
    result = add(3, 4)
    print(result)