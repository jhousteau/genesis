"""AI safety validation utilities for testing."""

from pathlib import Path
from typing import Dict, List, Any, Optional


def count_files_in_directory(directory: Path, include_hidden: bool = False,
                            use_gitignore: bool = True) -> int:
    """Count files in directory, respecting gitignore patterns by default."""
    import subprocess
    
    if use_gitignore:
        # Use git ls-files to get only tracked and untracked files that git would track
        try:
            # Get all files that git would track (respects .gitignore)
            result = subprocess.run(
                ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                cwd=directory,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                return len(files)
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fall back to manual counting if git is not available
            pass
    
    # Fallback: manual file counting with basic exclusions
    exclude_patterns = ['.git', '__pycache__', '.pytest_cache', 'node_modules', 'old-bloated-code-read-only']
    
    files = []
    for item in directory.rglob('*'):
        if not item.is_file():
            continue
            
        # Skip hidden files unless requested
        if not include_hidden and any(part.startswith('.') for part in item.parts):
            if not any(part in str(item) for part in ['.py', '.js', '.ts', '.sh', '.md']):
                continue
        
        # Skip excluded patterns
        if any(pattern in str(item) for pattern in exclude_patterns):
            continue
            
        files.append(item)
    
    return len(files)


def validate_ai_safety_limits(directory: Path, max_files: int = 100,
                             max_component_files: int = 30) -> Dict[str, Any]:
    """Validate directory meets AI safety file count limits."""
    total_files = count_files_in_directory(directory)
    
    # Check component directories
    component_results = {}
    for component_dir in directory.iterdir():
        if component_dir.is_dir() and not component_dir.name.startswith('.'):
            if component_dir.name in ['bootstrap', 'genesis-cli', 'smart-commit', 
                                     'worktree-tools', 'shared-python', 'testing']:
                component_files = count_files_in_directory(component_dir)
                component_results[component_dir.name] = {
                    'file_count': component_files,
                    'is_safe': component_files <= max_component_files,
                    'limit': max_component_files
                }
    
    return {
        'total_files': total_files,
        'max_files': max_files,
        'is_safe': total_files <= max_files,
        'components': component_results,
        'all_components_safe': all(result['is_safe'] for result in component_results.values())
    }


def assert_file_count_safe(directory: Path, max_files: int = 100,
                          message: str = None):
    """Assert that directory has safe file count for AI."""
    file_count = count_files_in_directory(directory)
    if message is None:
        message = f"Directory has {file_count} files, exceeds AI safety limit of {max_files}"
    
    assert file_count <= max_files, message


def assert_component_isolation(component_path: Path, max_files: int = 30):
    """Assert that component meets isolation requirements."""
    assert component_path.exists(), f"Component directory {component_path} does not exist"
    
    # Check required structure
    assert (component_path / "README.md").exists(), f"Component {component_path.name} missing README.md"
    
    # Check file count
    file_count = count_files_in_directory(component_path)
    assert file_count <= max_files, f"Component {component_path.name} has {file_count} files, exceeds limit of {max_files}"


def get_file_count_report(directory: Path) -> Dict[str, Any]:
    """Generate detailed file count report for directory."""
    report = {
        'directory': str(directory),
        'total_files': 0,
        'file_types': {},
        'components': {},
        'largest_files': [],
        'ai_safety_status': {}
    }
    
    # Count total files and analyze types
    all_files = []
    for item in directory.rglob('*'):
        if item.is_file():
            all_files.append(item)
            
            # Count by extension
            ext = item.suffix or 'no_extension'
            report['file_types'][ext] = report['file_types'].get(ext, 0) + 1
    
    report['total_files'] = len(all_files)
    
    # Analyze components
    for component_dir in directory.iterdir():
        if component_dir.is_dir() and not component_dir.name.startswith('.'):
            if component_dir.name in ['bootstrap', 'genesis-cli', 'smart-commit', 
                                     'worktree-tools', 'shared-python', 'testing']:
                component_files = count_files_in_directory(component_dir)
                report['components'][component_dir.name] = component_files
    
    # Find largest files (by line count if possible)
    sorted_files = sorted(all_files, key=lambda f: f.stat().st_size, reverse=True)
    report['largest_files'] = [
        {'path': str(f.relative_to(directory)), 'size': f.stat().st_size}
        for f in sorted_files[:10]
    ]
    
    # AI safety assessment
    report['ai_safety_status'] = validate_ai_safety_limits(directory)
    
    return report


def print_ai_safety_report(directory: Path):
    """Print human-readable AI safety report."""
    report = get_file_count_report(directory)
    
    print(f"\n🤖 AI Safety Report for {report['directory']}")
    print("=" * 50)
    
    print(f"Total files: {report['total_files']}")
    
    status = report['ai_safety_status']
    if status['is_safe']:
        print(f"✅ SAFE: Within limit of {status['max_files']} files")
    else:
        print(f"❌ UNSAFE: Exceeds limit of {status['max_files']} files")
    
    print("\nComponent breakdown:")
    for component, count in report['components'].items():
        status_icon = "✅" if count <= 30 else "❌"
        print(f"  {status_icon} {component}: {count} files")
    
    print("\nFile types:")
    for ext, count in sorted(report['file_types'].items()):
        print(f"  {ext}: {count}")
    
    if not status['is_safe'] or not status['all_components_safe']:
        print(f"\n⚠️  Action needed to maintain AI safety!")
        print("   Consider reducing file count or improving component isolation.")


class AISafetyChecker:
    """Class for checking AI safety constraints during tests."""
    
    def __init__(self, max_total_files: int = 100, max_component_files: int = 30):
        self.max_total_files = max_total_files
        self.max_component_files = max_component_files
        
    def check_project(self, project_path: Path) -> Dict[str, Any]:
        """Check entire project for AI safety."""
        return validate_ai_safety_limits(
            project_path, 
            self.max_total_files,
            self.max_component_files
        )
        
    def check_component(self, component_path: Path) -> Dict[str, Any]:
        """Check single component for AI safety."""
        file_count = count_files_in_directory(component_path)
        return {
            'component': component_path.name,
            'file_count': file_count,
            'max_files': self.max_component_files,
            'is_safe': file_count <= self.max_component_files
        }
        
    def assert_project_safe(self, project_path: Path):
        """Assert project meets AI safety requirements."""
        result = self.check_project(project_path)
        assert result['is_safe'], f"Project unsafe: {result['total_files']} > {result['max_files']} files"
        assert result['all_components_safe'], "Some components exceed file limits"
        
    def assert_component_safe(self, component_path: Path):
        """Assert component meets AI safety requirements."""
        result = self.check_component(component_path)
        assert result['is_safe'], f"Component {result['component']} unsafe: {result['file_count']} > {result['max_files']} files"