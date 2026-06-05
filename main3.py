import time
from functools import wraps
import threading
import multiprocessing
import gc
import sys
import os

def time_execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Execution time: {end_time - start_time:.4f} seconds")
        return result
    return wrapper

class PathDescriptor:
    def __set__(self, instance, value):
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        
        if not value.endswith('.txt'):
            raise ValueError("File must be a .txt file")
        
        instance.__dict__['_validated_path'] = value  # Different internal name
        print(f"✅ Validated path: {value}")
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get('_validated_path', None)
    
    def __set_name__(self, owner, name):
        self.name = name

class LogProcessor:
    # Descriptor with different name
    path_validator = PathDescriptor()
    
    # __slots__ with different names
    __slots__ = ['_file_path', 'filter_type', 'file', 'line_count', '_temp_data']
    
    def __init__(self, file_path, filter_type=None):
        # Use descriptor for validation
        self.path_validator = file_path  # Triggers validation
        self._file_path = file_path  # Store actual value
        self.filter_type = filter_type
        self.file = None
        self.line_count = 0
        self._temp_data = []
    
    @property
    def file_path(self):
        """Property to access file path"""
        return self._file_path
    
    @classmethod
    def for_errors(cls, file_path):
        instance = cls(file_path, filter_type="error")
        return instance
    
    def __enter__(self):
        print(f"📂 Opening file: {self._file_path}")
        self.file = open(self._file_path, 'r')
        
        # Memory-efficient line counting
        self.line_count = sum(1 for _ in self.file)
        self.file.seek(0)
        
        print(f"📊 File has {self.line_count} lines")
        print(f"💾 Object memory size: {sys.getsizeof(self)} bytes")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
            print("🔒 File closed, memory freed")
        
        self._temp_data = None
        return False
    
    def __len__(self):
        return self.line_count
    
    def __str__(self):
        return f"LogProcessor for file: {self._file_path} with filter: {self.filter_type}"
    
    def __repr__(self):
        return f"LogProcessor({self._file_path}, {self.filter_type})"
    
    def process_logs(self):
        """Memory-efficient generator (one line at a time)"""
        for line in self.file:
            stripped_line = line.strip()
            
            if self.filter_type == "error":
                if 'ERROR' in stripped_line:
                    yield stripped_line + ' need fix'
            else:
                yield stripped_line
    
    def demonstrate_gil_effect(self):
        """Demonstrate GIL with CPU-intensive task"""
        print("\n🧵 Demonstrating GIL effect...")
        
        def cpu_intensive():
            count = 0
            for i in range(5_000_000):
                count += i
            return count
        
        # Single thread
        start = time.time()
        cpu_intensive()
        single_time = time.time() - start
        
        # Multiple threads
        start = time.time()
        threads = []
        for _ in range(2):
            t = threading.Thread(target=cpu_intensive)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        multi_time = time.time() - start
        
        print(f"⏱️  Single thread: {single_time:.2f}s")
        print(f"⏱️  Multi-thread (GIL): {multi_time:.2f}s")
        if single_time > 0:
            print(f"📈 GIL overhead: {((multi_time/single_time)-1)*100:.1f}% slower")
        
        return single_time, multi_time

class ErrorLogProcessor(LogProcessor):
    __slots__ = []  # No extra attributes
    
    def __init__(self, file_path):
        super().__init__(file_path, filter_type='error')
    
    def process_logs(self):
        for log in super().process_logs():
            yield f"[CRITICAL] {log}"

class MemoryOptimizedLogProcessor(LogProcessor):
    """Demonstrates memory optimization techniques"""
    
    def process_in_chunks(self, chunk_size=1000):
        """Process logs in chunks to balance memory and speed"""
        chunk = []
        for line in self.file:
            chunk.append(line.strip())
            if len(chunk) >= chunk_size:
                yield self._process_chunk(chunk)
                chunk = []
                gc.collect()
        if chunk:
            yield self._process_chunk(chunk)
    
    def _process_chunk(self, chunk):
        """Process a chunk of lines"""
        results = []
        for line in chunk:
            if self.filter_type == "error" and 'ERROR' in line:
                results.append(line + ' need fix')
            elif not self.filter_type:
                results.append(line)
        return results

def parallel_log_processing(file_path, keyword='ERROR'):
    """Use multiprocessing to bypass GIL"""
    from multiprocessing import Pool, cpu_count
    
    def process_chunk(chunk):
        errors = []
        for line in chunk:
            if keyword in line:
                errors.append(line.strip())
        return errors
    
    if not os.path.exists(file_path):
        print(f"⚠️  File {file_path} not found")
        return []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    if not lines:
        return []
    
    chunk_size = max(1, len(lines) // cpu_count())
    chunks = [lines[i:i+chunk_size] for i in range(0, len(lines), chunk_size)]
    
    print(f"🚀 Using {cpu_count()} CPU cores (bypasses GIL!)")
    start = time.time()
    
    with Pool(cpu_count()) as pool:
        results = pool.map(process_chunk, chunks)
    
    end = time.time()
    print(f"⏱️  Parallel processing time: {end-start:.2f}s")
    
    return [error for sublist in results for error in sublist]

@time_execution
def main():
    print("=" * 60)
    print("🚀 LOG PROCESSOR WITH GIL & MEMORY MANAGEMENT DEMO")
    print("=" * 60)
    
    # Create sample file if needed
    if not os.path.exists('text.txt'):
        print("\n📝 Creating sample log file...")
        with open('text.txt', 'w') as f:
            f.write("INFO: Application started\n")
            f.write("ERROR: Database connection failed\n")
            f.write("INFO: Retrying connection\n")
            f.write("ERROR: Timeout occurred\n")
            f.write("WARNING: High memory usage\n")
            f.write("ERROR: Invalid user input\n")
            f.write("INFO: Application shutdown\n")
        print("✅ Sample log file created")
    
    # Test descriptor validation
    print("\n✅ SECTION 1: Descriptor Validation")
    print("-" * 40)
    try:
        processor = LogProcessor('text.txt')
        print(f"✓ Valid file path accepted: {processor.file_path}")
    except ValueError as e:
        print(f"❌ {e}")
    
    try:
        processor = LogProcessor('text.log')
    except ValueError as e:
        print(f"❌ Validation caught: {e}")
    
    # Demonstrate memory-efficient processing
    print("\n📁 SECTION 2: Memory-Efficient Processing")
    print("-" * 40)
    with ErrorLogProcessor('text.txt') as processor:
        print("Processing logs with generator...")
        count = 0
        for log_entry in processor.process_logs():
            if count < 5:
                print(f"  {log_entry}")
            count += 1
        if count > 5:
            print(f"  ... and {count-5} more lines")
        print(f"Total log entries: {len(processor)}")
    
    # Demonstrate GIL effect
    print("\n🎯 SECTION 3: GIL Demonstration")
    print("-" * 40)
    with LogProcessor('text.txt') as processor:
        processor.demonstrate_gil_effect()
    
    # Demonstrate chunk processing
    print("\n📦 SECTION 4: Chunk Processing")
    print("-" * 40)
    with MemoryOptimizedLogProcessor('text.txt', filter_type='error') as processor:
        chunks = list(processor.process_in_chunks(2))
        print(f"Processed {len(chunks)} chunks")
        print(f"Total errors: {sum(len(chunk) for chunk in chunks)}")
    
    # Demonstrate multiprocessing
    print("\n⚡ SECTION 5: Multiprocessing (Bypasses GIL)")
    print("-" * 40)
    errors = parallel_log_processing('text.txt', 'ERROR')
    print(f"Found {len(errors)} errors using multiprocessing")
    
    # Garbage collection demo
    print("\n🗑️ SECTION 6: Garbage Collection")
    print("-" * 40)
    
    class TempObject:
        def __del__(self):
            print("  🗑️ Object destroyed")
    
    obj1 = TempObject()
    obj2 = TempObject()
    obj1.ref = obj2
    obj2.ref = obj1
    
    print("Created circular reference")
    obj1 = None
    obj2 = None
    print("Deleted references, forcing GC...")
    gc.collect()
    
    # Memory stats
    print("\n📊 SECTION 7: Memory Statistics")
    print("-" * 40)
    print(f"  __slots__ saves memory: LogProcessor instance is {sys.getsizeof(LogProcessor)} bytes")
    print(f"  GC threshold: {gc.get_threshold()}")
    print(f"  GC enabled: {gc.isenabled()}")
    
    print("\n" + "=" * 60)
    print("🎉 Demo Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()