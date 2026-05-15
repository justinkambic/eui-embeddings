"""
Root-level pytest configuration
Disables OpenTelemetry during tests to avoid connection errors
"""
import os
import sys
from unittest.mock import patch, MagicMock

# Disable OpenTelemetry before any imports that might use it
# Set environment variables to disable OTEL exporters
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("OTEL_TRACES_EXPORTER", "none")
os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
os.environ.setdefault("OTEL_LOGS_EXPORTER", "none")

# Also set a dummy endpoint to prevent connection attempts if SDK is still enabled
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:0")

# Mock OpenTelemetry instrumentation before any modules import it
# This prevents actual instrumentation from happening during tests
# BUT: We skip mocking for otel_config tests themselves, as they need to test the actual code
_patches = []
_otel_mocks_applied = False

def pytest_collection_modifyitems(config, items):
    """Check if we're running otel_config tests and conditionally apply mocks"""
    global _otel_mocks_applied
    
    # Check if any otel_config tests are being run
    has_otel_tests = any('test_otel_config' in str(item.fspath) for item in items)
    
    # Only apply mocks if we're NOT running otel_config tests
    # But we need to apply them before embed.py is imported, so we do it here
    if not has_otel_tests and not _otel_mocks_applied:
        _setup_otel_mocks()
        _otel_mocks_applied = True

def pytest_configure(config):
    """Configure pytest - apply mocks early if not running otel_config tests"""
    global _otel_mocks_applied
    
    # Check command line to see if otel_config tests are being run
    # This runs before collection, so we can apply mocks early
    import sys
    test_paths = ' '.join(sys.argv)
    
    # If running ONLY otel_config tests, don't mock
    # But if running all tests (including otel_config), we still need mocks
    # for other tests that import embed.py
    # The otel_config tests will handle their own mocking internally
    if 'test_otel_config' in test_paths and len([a for a in sys.argv if a.endswith('.py')]) == 1:
        # Only otel_config tests, skip global mocking
        return
    
    # Otherwise, apply mocks to prevent connection errors
    # Note: otel_config tests use their own internal mocks, so this won't interfere
    if not _otel_mocks_applied:
        _setup_otel_mocks()
        _otel_mocks_applied = True

def _setup_otel_mocks():
    """Set up mocks for OpenTelemetry instrumentation"""
    global _patches
    
    # Mock the instrumentation functions to do nothing
    mock_initialize = MagicMock(return_value=None)
    mock_instrument_fastapi = MagicMock(return_value=None)
    mock_tracer = MagicMock()
    mock_meter = MagicMock()
    
    # Patch otel_config module before it's imported
    patches = [
        patch('otel_config.initialize_instrumentation', mock_initialize),
        patch('otel_config.instrument_fastapi', mock_instrument_fastapi),
        patch('otel_config.tracer', mock_tracer),
        patch('otel_config.meter', mock_meter),
    ]
    
    # Start all patches
    for p in patches:
        p.start()
        _patches.append(p)
    
    return patches

# Don't set up mocks immediately - wait for pytest_collection_modifyitems
# This ensures we can check which tests are being run before applying mocks

def pytest_unconfigure(config):
    """Clean up patches after tests"""
    for p in _patches:
        try:
            p.stop()
        except Exception:
            pass

