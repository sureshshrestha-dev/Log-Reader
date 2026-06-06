# Imagine a library where only one person is allowed to talk at a time, even if there are 100 people in the room.
#  That is the GIL. It ensures that only one thread executes Python bytecode at a time. 
# It makes memory management (garbage collection) safe and easy, but it means that if you have a CPU-heavy task, adding more threads won't make it faster.

# The Analogy: Memory Management
# Python uses Reference Counting. Every object has a counter of how many things point to it.
#  When the count hits zero, Python immediately deletes it. 
# However, Python also has a "Garbage Collector" that cleans up "circular references" (where Object A points to B, and B points back to A).

import sys
import gc

class Worker:
    def __init__(self, name, tasks_count):
        self.name = name
        self.tasks_count = tasks_count
        self.next_worker = None  # Used to demonstrate circular references

    def __str__(self):
        return f"Worker: {self.name} handling {self.tasks_count} tasks"

    def __repr__(self):
        return f"Worker('{self.name}', {self.tasks_count})"

    def __add__(self, other):
        """Combines tasks from two workers into a new worker instance."""
        if isinstance(other, Worker):
            combined_name = f"{self.name}+{other.name}"
            combined_tasks = self.tasks_count + other.tasks_count
            return Worker(combined_name, combined_tasks)
        return NotImplemented

    def __del__(self):
        """Triggers automatically when reference count hits 0."""
        print(f"🗑️  Memory Freed: {self.name} object destroyed!")


if __name__ == "__main__":
    print("--- 1. Object Creation & Reference Counting ---")
    w1 = Worker("Alice", 10)
    w2 = Worker("Bob", 20)
    print(w1)  # Output: Worker: Alice handling 10 tasks
    
    # sys.getrefcount adds 1 temporary reference inside the function
    print(f"Alice true reference count: {sys.getrefcount(w1) - 1}")  # Output: 1

    print("\n--- 2. Custom Magic Arithmetic Operator ---")
    # Adding two workers creates a brand new third Worker object
    w3 = w1 + w2
    print(repr(w3))  # Output: Worker('Alice+Bob', 30)

    print("\n--- 3. Immediate Memory Cleanup (Ref Count = 0) ---")
    print("Setting w3 to None...")
    w3 = None  # Triggers __del__ immediately because nothing else points to it

    print("\n--- 4. Circular Reference (Requires GC) ---")
    # Creating a loop where Alice points to Bob, and Bob points to Alice
    w1.next_worker = w2
    w2.next_worker = w1

    print("Clearing global variables w1 and w2...")
    w1 = None
    w2 = None
    print("Variables cleared, but workers are still trapped in a circular memory loop!")

    print("\n--- 5. Forcing Garbage Collection ---")
    # Python's GC sweeps cyclic isolated groups out of memory
    gc.collect()
    
    print("\n--- Script Finished ---")