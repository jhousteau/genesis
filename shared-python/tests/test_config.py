"""Tests for configuration functionality."""

import os
import tempfile

import yaml
from shared_core.config import ConfigLoader, load_config


class TestConfigLoader:
    def test_load_yaml_file(self):
        """Test loading configuration from YAML file."""
        config_data = {"database_url": "sqlite:///test.db", "debug": True}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_file(temp_path)
            
            assert config["database_url"] == "sqlite:///test.db"
            assert config["debug"] is True
        finally:
            os.unlink(temp_path)
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file returns empty dict."""
        loader = ConfigLoader()
        config = loader.load_file("nonexistent.yml")
        
        assert config == {}
    
    def test_env_override_with_prefix(self):
        """Test environment variable overrides with prefix."""
        os.environ["TEST_DATABASE_URL"] = "postgresql://test"
        os.environ["TEST_PORT"] = "5432"
        os.environ["TEST_DEBUG"] = "false"
        
        try:
            loader = ConfigLoader(env_prefix="TEST_")
            base_config = {"database_url": "sqlite://", "debug": True}
            config = loader.load_env(base_config)
            
            assert config["database_url"] == "postgresql://test"
            assert config["port"] == 5432  # Converted to int
            assert config["debug"] is False  # Converted to bool
        finally:
            for key in ["TEST_DATABASE_URL", "TEST_PORT", "TEST_DEBUG"]:
                os.environ.pop(key, None)
    
    def test_load_with_precedence(self):
        """Test configuration precedence: defaults < file < env."""
        config_data = {"database_url": "sqlite:///file.db", "port": 3000}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        os.environ["APP_DATABASE_URL"] = "postgresql://env"
        
        try:
            loader = ConfigLoader(env_prefix="APP_")
            defaults = {"database_url": "sqlite:///default.db", "timeout": 30}
            
            config = loader.load(temp_path, defaults)
            
            # Environment should override file
            assert config["database_url"] == "postgresql://env"
            # File should override defaults
            assert config["port"] == 3000
            # Defaults should be preserved if not overridden
            assert config["timeout"] == 30
        finally:
            os.unlink(temp_path)
            os.environ.pop("APP_DATABASE_URL", None)
    
    def test_type_conversion(self):
        """Test automatic type conversion from environment variables."""
        os.environ["TEST_INT_VAL"] = "42"
        os.environ["TEST_FLOAT_VAL"] = "3.14"
        os.environ["TEST_BOOL_TRUE"] = "true"
        os.environ["TEST_BOOL_FALSE"] = "FALSE"
        os.environ["TEST_STRING_VAL"] = "hello world"
        
        try:
            loader = ConfigLoader(env_prefix="TEST_")
            config = loader.load_env({})
            
            assert config["int_val"] == 42
            assert config["float_val"] == 3.14
            assert config["bool_true"] is True
            assert config["bool_false"] is False
            assert config["string_val"] == "hello world"
        finally:
            for key in ["TEST_INT_VAL", "TEST_FLOAT_VAL", "TEST_BOOL_TRUE", 
                       "TEST_BOOL_FALSE", "TEST_STRING_VAL"]:
                os.environ.pop(key, None)
    
    def test_simple_load_config_function(self):
        """Test the simple load_config function interface."""
        defaults = {"timeout": 30, "debug": False}
        os.environ["SIMPLE_DEBUG"] = "true"
        
        try:
            config = load_config(env_prefix="SIMPLE_", defaults=defaults)
            
            assert config["timeout"] == 30  # From defaults
            assert config["debug"] is True  # From environment
        finally:
            os.environ.pop("SIMPLE_DEBUG", None)