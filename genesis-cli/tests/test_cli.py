"""Tests for Genesis CLI functionality."""

import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from genesis import cli


class TestGenesisCLI:
    """Test Genesis CLI commands."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_cli_help(self):
        """Test that CLI shows help message."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Genesis" in result.output
        assert "Development toolkit" in result.output

    def test_version(self):
        """Test version command."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_bootstrap_help(self):
        """Test bootstrap command help."""
        result = self.runner.invoke(cli, ["bootstrap", "--help"])
        assert result.exit_code == 0
        assert "Create new project" in result.output
        assert "NAME" in result.output

    def test_worktree_help(self):
        """Test worktree command help."""
        result = self.runner.invoke(cli, ["worktree", "--help"])
        assert result.exit_code == 0
        assert "AI-safe sparse worktree" in result.output

    def test_commit_help(self):
        """Test commit command help."""
        result = self.runner.invoke(cli, ["commit", "--help"])
        assert result.exit_code == 0
        assert "Smart commit" in result.output

    def test_status_help(self):
        """Test status command help."""
        result = self.runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "project health" in result.output

    def test_sync_help(self):
        """Test sync command help."""
        result = self.runner.invoke(cli, ["sync", "--help"])
        assert result.exit_code == 0
        assert "Update shared components" in result.output

    def test_clean_help(self):
        """Test clean command help."""
        result = self.runner.invoke(cli, ["clean", "--help"])
        assert result.exit_code == 0
        assert "Clean workspace" in result.output

    def test_no_genesis_root(self):
        """Test behavior when not in Genesis project."""
        with patch('genesis.find_genesis_root', return_value=None):
            result = self.runner.invoke(cli, ["status"])
            assert result.exit_code == 1
            assert "Not in a Genesis project" in result.output

    @patch('genesis.find_genesis_root')
    @patch('subprocess.run')
    def test_bootstrap_command(self, mock_run, mock_find_root):
        """Test bootstrap command execution."""
        mock_find_root.return_value = Path("/fake/genesis")
        mock_run.return_value.returncode = 0
        
        # Mock the bootstrap script exists
        with patch('pathlib.Path.exists', return_value=True):
            result = self.runner.invoke(cli, ["bootstrap", "test-project"])
            assert result.exit_code == 0
            assert mock_run.called

    @patch('genesis.find_genesis_root')  
    @patch('subprocess.run')
    def test_worktree_command(self, mock_run, mock_find_root):
        """Test worktree command execution."""
        mock_find_root.return_value = Path("/fake/genesis")
        mock_run.return_value.returncode = 0
        
        with patch('pathlib.Path.exists', return_value=True):
            result = self.runner.invoke(cli, ["worktree", "test-worktree", "src/"])
            assert result.exit_code == 0
            assert mock_run.called

    @patch('genesis.find_genesis_root')
    @patch('subprocess.run') 
    def test_commit_command(self, mock_run, mock_find_root):
        """Test commit command execution."""
        mock_find_root.return_value = Path("/fake/genesis")
        mock_run.return_value.returncode = 0
        
        with patch('pathlib.Path.exists', return_value=True):
            result = self.runner.invoke(cli, ["commit"])
            assert result.exit_code == 0
            assert mock_run.called

    @patch('genesis.find_genesis_root')
    def test_status_command(self, mock_find_root):
        """Test status command execution."""
        mock_find_root.return_value = Path("/fake/genesis")
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('subprocess.run') as mock_run:
                # Mock file count check
                mock_run.return_value.stdout = "file1\nfile2\nfile3"
                mock_run.return_value.returncode = 0
                
                result = self.runner.invoke(cli, ["status"])
                assert result.exit_code == 0
                assert "Genesis project is healthy" in result.output

    @patch('genesis.find_genesis_root')
    def test_clean_command(self, mock_find_root):
        """Test clean command execution.""" 
        mock_find_root.return_value = Path("/fake/genesis")
        
        with patch('pathlib.Path.exists', return_value=False):
            result = self.runner.invoke(cli, ["clean"])
            assert result.exit_code == 0
            assert "already clean" in result.output

    def test_find_genesis_root_function(self):
        """Test Genesis root detection."""
        from genesis import find_genesis_root
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Test when CLAUDE.md exists
            claude_file = tmpdir_path / "CLAUDE.md"
            claude_file.write_text("Test content")
            
            # Change to subdirectory and test detection
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            
            original_cwd = Path.cwd()
            try:
                os.chdir(subdir)
                result = find_genesis_root()
                # Resolve paths to handle /private/var/folders vs /var/folders difference on macOS
                assert result.resolve() == tmpdir_path.resolve()
            finally:
                os.chdir(original_cwd)

    def test_missing_script_error(self):
        """Test error when required scripts are missing."""
        with patch('genesis.find_genesis_root', return_value=Path("/fake/genesis")):
            with patch('pathlib.Path.exists', return_value=False):
                result = self.runner.invoke(cli, ["bootstrap", "test"])
                assert result.exit_code == 1
                assert "not found" in result.output