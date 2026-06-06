# test/test_api_complete.py
import pytest
import requests
from datetime import datetime, timedelta
import time
import random

BASE_URL = "http://localhost:8000"

class TestLogAPI:
    """Complete test suite for Log API"""
    
    def setup_method(self):
            """Setup before each test: securely ensure API is available and healthy"""
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=2)
                if response.status_code != 200:
                    pytest.skip(f"API server returned status {response.status_code}. DB might be down.")
            except requests.RequestException:
                pytest.skip("API server is completely unreachable. Start with: uvicorn main2:app --reload")
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ Health check passed")
    
    def test_single_log(self):
        """Test posting a single log"""
        log = {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "message": "Test error message"
        }
        
        response = requests.post(f"{BASE_URL}/logs", json=log)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        print("✅ Single log test passed")
    
    def test_batch_logs_small(self):
        """Test posting a small batch of logs"""
        logs = []
        for i in range(100):
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": random.choice(["INFO", "ERROR", "WARNING"]),
                "message": f"Batch test log {i}"
            })
        
        response = requests.post(f"{BASE_URL}/logs/batch", json=logs)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        print(f"✅ Small batch test passed: {len(logs)} logs")
    
    def test_batch_logs_large(self):
        """Test posting a large batch of logs (memory efficient)"""
        batch_size = 1000
        total_logs = 5000
        
        print(f"\n📦 Testing {total_logs} logs in batches of {batch_size}")
        start_time = time.time()
        
        for batch_num in range(0, total_logs, batch_size):
            batch = []
            for i in range(batch_size):
                if batch_num + i >= total_logs:
                    break
                batch.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR" if i % 10 == 0 else "INFO",
                    "message": f"Large batch log {batch_num + i}"
                })
            
            response = requests.post(f"{BASE_URL}/logs/batch", json=batch)
            assert response.status_code == 200
            
            elapsed = time.time() - start_time
            print(f"  Batch {batch_num//batch_size + 1}: {len(batch)} logs in {elapsed:.2f}s")
        
        total_time = time.time() - start_time
        print(f"✅ Large batch test passed: {total_logs} logs in {total_time:.2f}s")
    
    def test_query_all_logs(self):
        """Test querying all logs"""
        response = requests.get(f"{BASE_URL}/logs", params={"limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        print(f"✅ Query test passed: Total {data['total']} logs, returned {len(data['logs'])}")
    
    def test_query_by_level(self):
        """Test filtering by log level"""
        for level in ["INFO", "ERROR", "WARNING", "DEBUG"]:
            response = requests.get(
                f"{BASE_URL}/logs",
                params={"level": level, "limit": 5}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify all returned logs have the correct level
            for log in data["logs"]:
                assert log["level"] == level
            
            print(f"  {level}: {data['total']} total logs")
        
        print("✅ Level filter test passed")
    
    def test_query_with_pagination(self):
        """Test pagination (skip/limit)"""
        # Get first page
        page1 = requests.get(f"{BASE_URL}/logs", params={"limit": 5, "skip": 0})
        assert page1.status_code == 200
        data1 = page1.json()
        
        # Get second page
        page2 = requests.get(f"{BASE_URL}/logs", params={"limit": 5, "skip": 5})
        assert page2.status_code == 200
        data2 = page2.json()
        
        # Pages should be different if there are enough logs
        if len(data1["logs"]) == 5 and len(data2["logs"]) == 5:
            assert data1["logs"][0]["_id"] != data2["logs"][0]["_id"]
        
        print("✅ Pagination test passed")
    
    def test_query_time_range(self):
        """Test time range filtering"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        response = requests.get(
            f"{BASE_URL}/logs",
            params={
                "start_time": yesterday.isoformat(),
                "end_time": now.isoformat()
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify timestamps are within range
        for log in data["logs"]:
            log_time = datetime.fromisoformat(log["timestamp"])
            assert log_time >= yesterday
            assert log_time <= now
        
        print(f"✅ Time range test passed: {len(data['logs'])} logs in last 24 hours")
    
    def test_statistics(self):
        """Test statistics endpoint"""
        response = requests.get(f"{BASE_URL}/logs/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "by_level" in data
        assert "error_rate" in data
        assert "timestamp" in data
        
        # Verify all levels are present
        for level in ["INFO", "ERROR", "WARNING", "DEBUG"]:
            assert level in data["by_level"]
        
        print(f"✅ Stats test passed: Total={data['total']}, Error Rate={data['error_rate']:.2%}")
    
    def test_streaming_response(self):
        """Test streaming endpoint"""
        response = requests.get(
            f"{BASE_URL}/logs",
            params={"stream": "true", "limit": 100}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/x-ndjson"
        
        # Parse streaming response
        lines = response.text.strip().split('\n')
        assert len(lines) > 0
        
        print(f"✅ Streaming test passed: Received {len(lines)} logs")
    
    def test_delete_old_logs(self):
        """Test deleting old logs (use with caution)"""
        # Delete logs older than 365 days (should be safe)
        response = requests.delete(f"{BASE_URL}/logs", params={"days": 365})
        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        print(f"✅ Delete test passed: Deleted {data['deleted_count']} old logs")
    
    def test_invalid_log(self):
        """Test posting invalid log (should fail)"""
        invalid_log = {
            "timestamp": "invalid-date",
            "level": "INVALID_LEVEL",
            "message": ""
        }
        
        response = requests.post(f"{BASE_URL}/logs", json=invalid_log)
        assert response.status_code == 422  # Validation error
        print("✅ Invalid log test passed")

# ============ Performance Benchmark ============
def test_performance_benchmark():
    """Benchmark API performance"""
    import time
    
    print("\n📊 Performance Benchmark:")
    
    # Test single log latency
    latencies = []
    for _ in range(10):
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/logs",
            json={
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": "Benchmark log"
            }
        )
        latencies.append((time.time() - start) * 1000)
    
    avg_latency = sum(latencies) / len(latencies)
    print(f"  Single log avg latency: {avg_latency:.2f}ms")
    
    # Test batch throughput
    batch_sizes = [100, 500, 1000]
    for size in batch_sizes:
        logs = [{
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Benchmark log {i}"
        } for i in range(size)]
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/logs/batch", json=logs)
        elapsed = time.time() - start
        
        throughput = size / elapsed
        print(f"  Batch {size}: {elapsed:.2f}s ({throughput:.0f} logs/sec)")
    
    print("✅ Performance benchmark completed")

# ============ Run Tests ============
if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])