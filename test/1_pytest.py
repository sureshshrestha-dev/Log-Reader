import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from main2 import LogProcessor

# pytest test/1_pytest.py -v

# The fixture you provided
@pytest.fixture
def mock_file():
    """Mock the open function to avoid real file I/O"""
    with patch('builtins.open') as mocked_open:
        # Create a mock file handle that returns our test data
        mock_file_handle = MagicMock()
        mock_file_handle.__iter__.return_value = ["ERROR: Test", "INFO: Test"]
        mock_file_handle.__enter__.return_value = mock_file_handle
        
        # Setup the mocked open to return our mock file handle
        mocked_open.return_value = mock_file_handle
        
        yield mocked_open

# ============ THE CHALLENGE SOLUTION ============
def test_log_processor_error_count(mock_file):
    """
    Test that LogProcessor correctly counts errors in the mock file
    """
    # Create a LogProcessor instance with a dummy file path
    processor = LogProcessor('dummy.txt', filter_type='error')
    
    # Manually set up the context manager behavior since we're mocking
    # Option 1: Directly use the mocked open
    with patch('builtins.open') as mock_open:
        # Setup mock to return our test data
        mock_file_handle = MagicMock()
        mock_file_handle.__iter__.return_value = ["ERROR: Test", "INFO: Test"]
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_open.return_value = mock_file_handle
        
        # Use the context manager
        with processor as p:
            # Count errors by consuming the generator
            error_count = 0
            for log in p.process_logs():
                # process_logs with filter_type='error' only yields ERROR logs
                error_count += 1
            
            # Assert that we found exactly 1 error
            assert error_count == 1, f"Expected 1 error, but found {error_count}"

# ============ BETTER SOLUTION (Using the fixture directly) ============
def test_log_processor_with_fixture(mock_file):
    """
    Test using the provided mock_file fixture
    """
    # Create processor
    processor = LogProcessor('dummy.txt', filter_type='error')
    
    # Setup the mock to return our test data
    mock_open = mock_file
    mock_file_handle = MagicMock()
    mock_file_handle.__iter__.return_value = ["ERROR: Test", "INFO: Test"]
    mock_file_handle.__enter__.return_value = mock_file_handle
    mock_open.return_value = mock_file_handle
    
    # Test the processor
    with processor as p:
        logs = list(p.process_logs())
        
        # Should only have 1 log (the ERROR one)
        assert len(logs) == 1
        assert "ERROR" in logs[0]
        assert "need fix" in logs[0]
        assert "INFO" not in logs[0]

# ============ COMPREHENSIVE TEST WITH MULTIPLE SCENARIOS ============
class TestLogProcessor:
    """Complete test suite for LogProcessor"""
    
    @pytest.fixture
    def mock_file_with_content(self):
        """Fixture that returns different mock file contents"""
        def _create_mock(content_list):
            with patch('builtins.open') as mock_open:
                mock_file_handle = MagicMock()
                mock_file_handle.__iter__.return_value = content_list
                mock_file_handle.__enter__.return_value = mock_file_handle
                mock_open.return_value = mock_file_handle
                yield mock_open
        return _create_mock
    
    def test_count_errors_only(self):
        """Test that only ERROR logs are counted with filter_type='error'"""
        test_data = [
            "ERROR: Database connection failed",
            "INFO: Application started",
            "ERROR: Timeout occurred",
            "WARNING: Low memory",
            "ERROR: Segmentation fault"
        ]
        
        with patch('builtins.open') as mock_open:
            mock_file_handle = MagicMock()
            mock_file_handle.__iter__.return_value = test_data
            mock_file_handle.__enter__.return_value = mock_file_handle
            mock_open.return_value = mock_file_handle
            
            processor = LogProcessor('dummy.txt', filter_type='error')
            
            with processor as p:
                errors = list(p.process_logs())
                
                # Should have 3 errors (only the ERROR lines)
                assert len(errors) == 3
                
                # All returned logs should contain 'ERROR' and 'need fix'
                for error in errors:
                    assert "ERROR" in error
                    assert "need fix" in error
    
    def test_no_errors_found(self):
        """Test when there are no ERROR logs"""
        test_data = [
            "INFO: All good",
            "DEBUG: Checking status",
            "WARNING: Low disk space",
            "INFO: Operation complete"
        ]
        
        with patch('builtins.open') as mock_open:
            mock_file_handle = MagicMock()
            mock_file_handle.__iter__.return_value = test_data
            mock_file_handle.__enter__.return_value = mock_file_handle
            mock_open.return_value = mock_file_handle
            
            processor = LogProcessor('dummy.txt', filter_type='error')
            
            with processor as p:
                errors = list(p.process_logs())
                
                # Should have 0 errors
                assert len(errors) == 0
    
    def test_all_errors(self):
        """Test when all logs are errors"""
        test_data = [
            "ERROR: Critical failure",
            "ERROR: System crash",
            "ERROR: Data corruption"
        ]
        
        with patch('builtins.open') as mock_open:
            mock_file_handle = MagicMock()
            mock_file_handle.__iter__.return_value = test_data
            mock_file_handle.__enter__.return_value = mock_file_handle
            mock_open.return_value = mock_file_handle
            
            processor = LogProcessor('dummy.txt', filter_type='error')
            
            with processor as p:
                errors = list(p.process_logs())
                
                # Should have 3 errors
                assert len(errors) == 3
                
                # Each error should be properly formatted
                for error in errors:
                    assert error.endswith('need fix')
    
    def test_no_filter(self):
        """Test without any filter (should yield all logs)"""
        test_data = [
            "ERROR: Database failed",
            "INFO: Server started",
            "WARNING: Memory low",
            "ERROR: Connection lost"
        ]
        
        with patch('builtins.open') as mock_open:
            mock_file_handle = MagicMock()
            mock_file_handle.__iter__.return_value = test_data
            mock_file_handle.__enter__.return_value = mock_file_handle
            mock_open.return_value = mock_file_handle
            
            # No filter_type (default None)
            processor = LogProcessor('dummy.txt', filter_type=None)
            
            with processor as p:
                logs = list(p.process_logs())
                
                # Should have ALL 4 logs (no filtering)
                assert len(logs) == 4
                
                # None should have 'need fix' suffix
                for log in logs:
                    assert 'need fix' not in log

# ============ ADVANCED: Testing with Parameterization ============
@pytest.mark.parametrize("test_data,expected_count", [
    (["ERROR: Test"], 1),                    # 1 error
    (["INFO: Test"], 0),                     # 0 errors
    (["ERROR: 1", "ERROR: 2"], 2),           # 2 errors
    (["ERROR: 1", "INFO: 2", "ERROR: 3"], 2), # Mixed
    ([], 0),                                 # Empty file
])
def test_error_count_parametrized(test_data, expected_count):
    """Test multiple scenarios with parameterization"""
    with patch('builtins.open') as mock_open:
        mock_file_handle = MagicMock()
        mock_file_handle.__iter__.return_value = test_data
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_open.return_value = mock_file_handle
        
        processor = LogProcessor('dummy.txt', filter_type='error')
        
        with processor as p:
            errors = list(p.process_logs())
            assert len(errors) == expected_count

# ============ TESTING THE TEST (to verify it works) ============
def test_the_test():
    """Simple test to verify our test logic"""
    # This test doesn't need the processor, just validates our approach
    test_data = ["ERROR: Test", "INFO: Test"]
    error_lines = [line for line in test_data if 'ERROR' in line]
    
    assert len(error_lines) == 1
    assert error_lines[0] == "ERROR: Test"

# ============ HOW TO RUN THE TESTS ============
# In terminal, run:
# pytest test_log_processor.py -v
# 
# Or with specific test:
# pytest test_log_processor.py::test_log_processor_error_count -v

# ============ SIMPLEST VERSION (YOUR CHALLENGE SOLUTION) ============
def test_challenge_solution(mock_file):
    """
    YOUR CHALLENGE SOLUTION:
    Test that LogProcessor correctly finds 1 error in mock file
    """
    # Setup the mock
    mock_open = mock_file
    mock_file_handle = MagicMock()
    mock_file_handle.__iter__.return_value = ["ERROR: Test", "INFO: Test"]
    mock_file_handle.__enter__.return_value = mock_file_handle
    mock_open.return_value = mock_file_handle
    
    # Create processor
    processor = LogProcessor('dummy.txt', filter_type='error')
    
    # Process the logs
    with processor as p:
        error_count = sum(1 for _ in p.process_logs())
    
    # Assert we found exactly 1 error
    assert error_count == 1