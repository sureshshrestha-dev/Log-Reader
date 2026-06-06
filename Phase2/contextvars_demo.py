import asyncio
import contextvars
import random

# 1. Create a Context Variable to hold the unique transaction/request ID
tx_id_var = contextvars.ContextVar("transaction_id", default="UNKNOWN")

# 2. Centralized logging function 
def log(message: str):
    # This automatically grabs the ID from the current async context background
    print(f"[TxID: {tx_id_var.get()}] {message}")

# ---------------------------------------------------------
# Individual Core Operations (Notice: No 'tx_id' parameters!)
# ---------------------------------------------------------
async def add(a, b):
    log(f"Starting addition: {a} + {b}")
    await asyncio.sleep(random.uniform(0.1, 0.3))  # Simulate network/DB latency
    result = a + b
    log(f"Finished addition: Result = {result}")
    return result

async def sub(a, b):
    log(f"Starting subtraction: {a} - {b}")
    await asyncio.sleep(random.uniform(0.1, 0.3))
    result = a - b
    log(f"Finished subtraction: Result = {result}")
    return result

async def mul(a, b):
    log(f"Starting multiplication: {a} * {b}")
    await asyncio.sleep(random.uniform(0.1, 0.3))
    result = a * b
    log(f"Finished multiplication: Result = {result}")
    return result

# ---------------------------------------------------------
# The Pipeline (Simulating an API endpoint request)
# ---------------------------------------------------------
async def run_math_pipeline(tx_id, start_val, add_val, sub_val, mul_val):
    # Set the unique ID for THIS specific async execution line
    token = tx_id_var.set(tx_id)
    try:
        log("Pipeline started.")
        
        # Run the sequential math operations
        val1 = await add(start_val, add_val)
        val2 = await sub(val1, sub_val)
        final_result = await mul(val2, mul_val)
        
        log(f"Pipeline finished! Final value = {final_result}")
    finally:
        # Clean up context when the request is over
        tx_id_var.reset(token)

# ---------------------------------------------------------
# Orchestrator (Simulating two incoming concurrent requests)
# ---------------------------------------------------------
async def main():
    print("--- Starting Concurrent Math Operations ---")
    # We trigger BOTH pipelines at the exact same time
    await asyncio.gather(
        run_math_pipeline("REQ-AAAA", start_val=10, add_val=5, sub_val=3, mul_val=2),
        run_math_pipeline("REQ-BBBB", start_val=100, add_val=50, sub_val=20, mul_val=3)
    )

if __name__ == "__main__":
    asyncio.run(main())