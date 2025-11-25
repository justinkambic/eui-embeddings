"""
Unit tests for otel_config.py
"""
import pytest
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from opentelemetry import trace, metrics

# Stop global OTEL mocks from conftest.py before running these tests
# These tests need to test the actual otel_config code
@pytest.fixture(autouse=True, scope="class")
def stop_global_otel_mocks():
    """Stop global OTEL mocks so we can test actual otel_config functionality"""
    # Import conftest to access the patches
    import tests.conftest as conftest_module
    import importlib
    
    # Stop all global patches
    for p in conftest_module._patches:
        try:
            p.stop()
        except Exception:
            pass
    
    # Reload otel_config to get the real functions back
    if 'otel_config' in sys.modules:
        importlib.reload(sys.modules['otel_config'])
    
    yield
    
    # Restart mocks after these tests to prevent connection errors in other tests
    if not conftest_module._otel_mocks_applied:
        conftest_module._setup_otel_mocks()
        conftest_module._otel_mocks_applied = True


class TestOTELConfiguration:
    """Tests for OpenTelemetry configuration"""
    
    def test_initialize_instrumentation(self):
        """Test initialization of instrumentation"""
        with patch('otel_config.RequestsInstrumentor') as mock_requests, \
             patch('otel_config.ElasticsearchInstrumentor') as mock_es:
            
            from otel_config import initialize_instrumentation
            initialize_instrumentation()
            
            mock_requests.return_value.instrument.assert_called_once()
            mock_es.return_value.instrument.assert_called_once()
    
    def test_resource_attributes_parsing(self):
        """Test parsing of resource attributes from environment"""
        with patch.dict(os.environ, {
            'OTEL_SERVICE_NAME': 'test-service',
            'OTEL_SERVICE_VERSION': '1.0.0',
            'OTEL_RESOURCE_ATTRIBUTES': 'deployment.environment=test,key1=value1'
        }):
            # Re-import to pick up new env vars
            import importlib
            import otel_config
            importlib.reload(otel_config)
            
            # Check that resource attributes are parsed
            assert hasattr(otel_config, 'resource')
    
    def test_otlp_exporter_configuration(self):
        """Test OTLP exporter configuration"""
        with patch.dict(os.environ, {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'https://test-endpoint.com',
            'OTEL_EXPORTER_OTLP_HEADERS': 'Authorization=Bearer token'
        }):
            import importlib
            import otel_config
            importlib.reload(otel_config)
            
            # Check exporter is configured
            assert hasattr(otel_config, 'otlp_exporter')
    
    def test_instrument_fastapi(self):
        """Test FastAPI instrumentation"""
        mock_app = Mock()
        with patch('otel_config.FastAPIInstrumentor') as mock_instrumentor:
            from otel_config import instrument_fastapi
            instrument_fastapi(mock_app)
            mock_instrumentor.instrument_app.assert_called_once_with(mock_app)
    
    def test_default_configuration(self):
        """Test default configuration values"""
        # Clear environment variables
        env_vars_to_clear = [
            'OTEL_SERVICE_NAME',
            'OTEL_SERVICE_VERSION',
            'OTEL_EXPORTER_OTLP_ENDPOINT',
            'OTEL_EXPORTER_OTLP_HEADERS',
            'OTEL_RESOURCE_ATTRIBUTES'
        ]
        
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.get(var)
            os.environ.pop(var, None)
        
        try:
            import importlib
            import otel_config
            importlib.reload(otel_config)
            
            # Check defaults are used
            assert otel_config.OTEL_SERVICE_NAME == "eui-python-api"
            assert otel_config.OTEL_SERVICE_VERSION == "unknown"
        finally:
            # Restore original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
    
    def test_tracer_provider_initialization(self):
        """Test tracer provider is initialized"""
        from otel_config import tracer_provider
        assert tracer_provider is not None
    
    def test_meter_provider_initialization(self):
        """Test meter provider is initialized"""
        from otel_config import meter_provider
        assert meter_provider is not None
    
    def test_tracer_and_meter_available(self):
        """Test tracer and meter are available"""
        from otel_config import tracer, meter
        assert tracer is not None
        assert meter is not None

