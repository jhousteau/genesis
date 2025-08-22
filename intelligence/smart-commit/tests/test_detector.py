"""Basic tests for smart-commit detector module."""

from pathlib import Path

from smart_commit.detector import ProjectDetector, ProjectType


def test_project_detector_initialization():
    """Test that ProjectDetector can be initialized."""
    detector = ProjectDetector()
    assert detector is not None
    assert isinstance(detector.project_root, Path)


def test_detect_project_types_returns_dict():
    """Test that detect_project_types returns a dictionary."""
    detector = ProjectDetector()
    result = detector.detect_project_types()
    assert isinstance(result, dict)


def test_get_primary_type_returns_project_type():
    """Test that get_primary_type returns a ProjectType."""
    detector = ProjectDetector()
    result = detector.get_primary_type()
    assert isinstance(result, ProjectType)


def test_detect_tools_returns_dict():
    """Test that detect_tools returns a dictionary."""
    detector = ProjectDetector()
    result = detector.detect_tools()
    assert isinstance(result, dict)
    assert all(isinstance(k, str) for k in result.keys())
    assert all(isinstance(v, bool) for v in result.values())
