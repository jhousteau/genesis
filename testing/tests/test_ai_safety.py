"""Tests for AI safety validation and file count limits."""

import pytest
from pathlib import Path
from testing.fixtures import create_genesis_project_structure
from testing.utilities import (
    validate_ai_safety_limits, assert_file_count_safe,
    assert_component_isolation, AISafetyChecker
)


class TestAISafetyValidation:
    """Test AI safety constraint validation."""
    
    def test_validate_file_limits_safe_project(self, temp_dir):
        """Test validation of a safe project."""
        # Create small project
        fs = create_genesis_project_structure(temp_dir)
        
        result = validate_ai_safety_limits(temp_dir, max_files=100)
        
        assert result['is_safe']
        assert result['total_files'] <= 100
        assert result['all_components_safe']
    
    def test_validate_file_limits_unsafe_project(self, temp_dir):
        """Test validation of project exceeding limits."""
        # Create project with many files
        for i in range(50):
            (temp_dir / f"extra_file_{i}.py").write_text(f"# File {i}")
        
        result = validate_ai_safety_limits(temp_dir, max_files=30)
        
        assert not result['is_safe']
        assert result['total_files'] > 30
    
    def test_component_isolation_validation(self, temp_dir):
        """Test component isolation validation."""
        fs = create_genesis_project_structure(temp_dir)
        
        # Test valid component
        bootstrap_path = temp_dir / "bootstrap"
        assert_component_isolation(bootstrap_path, max_files=30)
        
        # Test component with too many files
        for i in range(25):
            (bootstrap_path / f"extra_{i}.py").write_text(f"# Extra {i}")
        
        with pytest.raises(AssertionError, match="exceeds limit"):
            assert_component_isolation(bootstrap_path, max_files=20)
    
    def test_ai_safety_checker_class(self, temp_dir):
        """Test AISafetyChecker class functionality."""
        checker = AISafetyChecker(max_total_files=50, max_component_files=20)
        fs = create_genesis_project_structure(temp_dir)
        
        # Test project check
        result = checker.check_project(temp_dir)
        assert result['is_safe']
        
        # Test component check
        bootstrap_path = temp_dir / "bootstrap"
        component_result = checker.check_component(bootstrap_path)
        assert component_result['is_safe']
        assert component_result['component'] == 'bootstrap'
    
    def test_file_count_safe_assertion(self, temp_dir):
        """Test file count safety assertion."""
        # Create a few files
        for i in range(5):
            (temp_dir / f"file_{i}.txt").write_text("content")
        
        # Should pass with high limit
        assert_file_count_safe(temp_dir, max_files=10)
        
        # Should fail with low limit
        with pytest.raises(AssertionError):
            assert_file_count_safe(temp_dir, max_files=3)
    
    @pytest.mark.ai_safety
    def test_genesis_project_ai_safety(self, genesis_root):
        """Test that actual Genesis project meets AI safety limits."""
        checker = AISafetyChecker(max_total_files=100, max_component_files=30)
        
        # This should pass for the real Genesis project
        result = checker.check_project(genesis_root)
        
        # Print report for debugging if needed
        if not result['is_safe']:
            from testing.utilities import print_ai_safety_report
            print_ai_safety_report(genesis_root)
        
        assert result['is_safe'], f"Genesis project has {result['total_files']} files, exceeds AI safety limit"
        
        # Check individual components
        components = ['bootstrap', 'genesis-cli', 'smart-commit', 'worktree-tools', 'shared-python']
        for component_name in components:
            component_path = genesis_root / component_name
            if component_path.exists():
                component_result = checker.check_component(component_path)
                assert component_result['is_safe'], f"Component {component_name} has {component_result['file_count']} files, exceeds limit"
    
    def test_exclude_patterns_working(self, temp_dir):
        """Test that file counting excludes appropriate patterns."""
        # Create files that should be excluded
        (temp_dir / ".git").mkdir()
        (temp_dir / ".git" / "config").write_text("git config")
        (temp_dir / "__pycache__").mkdir()
        (temp_dir / "__pycache__" / "cache.pyc").write_text("cached")
        (temp_dir / "node_modules").mkdir()
        (temp_dir / "node_modules" / "package").write_text("package")
        
        # Create files that should be included
        (temp_dir / "main.py").write_text("# main")
        (temp_dir / "README.md").write_text("# readme")
        
        from testing.utilities.ai_safety import count_files_in_directory
        file_count = count_files_in_directory(temp_dir)
        
        # Should only count main.py and README.md
        assert file_count == 2
    
    def test_component_structure_requirements(self, temp_dir):
        """Test that components have required structure."""
        # Create incomplete component
        component_path = temp_dir / "test-component"
        component_path.mkdir()
        (component_path / "src").mkdir()
        # Missing README.md and tests/
        
        with pytest.raises(AssertionError, match="missing README.md"):
            assert_component_isolation(component_path)
        
        # Add README.md
        (component_path / "README.md").write_text("# Test Component")
        
        # Now should pass (has README.md and is under file limit)
        assert_component_isolation(component_path)


class TestFileCountReporting:
    """Test file count reporting functionality."""
    
    def test_file_count_report_generation(self, temp_dir):
        """Test generation of detailed file count reports."""
        fs = create_genesis_project_structure(temp_dir)
        
        from testing.utilities.ai_safety import get_file_count_report
        report = get_file_count_report(temp_dir)
        
        assert 'directory' in report
        assert 'total_files' in report
        assert 'file_types' in report
        assert 'components' in report
        assert 'ai_safety_status' in report
        
        # Should have detected Genesis components
        expected_components = ['bootstrap', 'genesis-cli', 'smart-commit', 'worktree-tools', 'shared-python']
        for component in expected_components:
            assert component in report['components']
        
        # Should have file type breakdown
        assert '.py' in report['file_types']
        assert '.md' in report['file_types']
        assert '.sh' in report['file_types']
    
    def test_print_ai_safety_report(self, temp_dir, capsys):
        """Test printing of AI safety report."""
        fs = create_genesis_project_structure(temp_dir)
        
        from testing.utilities.ai_safety import print_ai_safety_report
        print_ai_safety_report(temp_dir)
        
        captured = capsys.readouterr()
        assert "AI Safety Report" in captured.out
        assert "Total files:" in captured.out
        assert "Component breakdown:" in captured.out
        assert "File types:" in captured.out