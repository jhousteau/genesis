"""
Bootstrapper Integration Test Suite
Comprehensive testing framework for all bootstrapper components
"""

__version__ = "1.0.0"
__author__ = "Agent 8 - Integration Coordinator"

# Import only what exists
try:
    from .integration_tests import *
except ImportError:
    pass

try:
    from .end_to_end_tests import *
except ImportError:
    pass

try:
    from .test_complete_integration import *
except ImportError:
    pass

# Test configuration
TEST_CONFIG = {
    "test_timeout": 300,  # 5 minutes default timeout
    "parallel_workers": 4,
    "test_data_dir": "/tmp/bootstrapper_test_data",
    "cleanup_after_tests": True,
    "verbose_logging": True,
}
