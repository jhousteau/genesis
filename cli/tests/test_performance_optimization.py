"""
Performance Optimization Testing
Tests for CLI startup time, response time, and efficiency validation.
"""

import pytest
import time
import subprocess
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import threading
import multiprocessing

# Add the parent directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.commands.main import GenesisCLI
from cli.services.performance_service import PerformanceService


class TestStartupPerformance:
    """Test CLI startup performance - target <200ms."""

    def test_cli_initialization_time(self):
        """Test CLI class initialization is fast."""
        start_time = time.perf_counter()
        cli = GenesisCLI()
        init_time = time.perf_counter() - start_time

        # Should initialize in less than 100ms
        assert (
            init_time < 0.1
        ), f"CLI initialization took {init_time:.3f}s, should be < 0.1s"

    def test_argument_parser_creation_time(self):
        """Test argument parser creation is fast."""
        cli = GenesisCLI()

        start_time = time.perf_counter()
        parser = cli.create_parser()
        parser_time = time.perf_counter() - start_time

        # Parser creation should be fast
        assert (
            parser_time < 0.05
        ), f"Parser creation took {parser_time:.3f}s, should be < 0.05s"
        assert parser is not None

    def test_ui_components_initialization_time(self):
        """Test UI components initialize quickly."""
        start_time = time.perf_counter()

        # Import and initialize UI components
        from ui import TerminalAdapter, ColorScheme, OutputFormatter, HelpSystem

        terminal_adapter = TerminalAdapter()
        color_scheme = ColorScheme()
        output_formatter = OutputFormatter(terminal_adapter, color_scheme)
        help_system = HelpSystem(terminal_adapter, color_scheme)

        ui_init_time = time.perf_counter() - start_time

        # UI initialization should be very fast
        assert (
            ui_init_time < 0.05
        ), f"UI initialization took {ui_init_time:.3f}s, should be < 0.05s"

    @pytest.mark.slow
    def test_cli_cold_start_time(self):
        """Test complete CLI cold start time including imports."""
        # This test measures the complete startup time including module imports
        start_script = """
import time
start_time = time.perf_counter()
from cli.commands.main import GenesisCLI
cli = GenesisCLI()
parser = cli.create_parser()
total_time = time.perf_counter() - start_time
print(f"STARTUP_TIME:{total_time:.6f}")
"""

        # Run in separate process to measure true cold start
        result = subprocess.run(
            [sys.executable, "-c", start_script],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Extract startup time from output
        startup_time = None
        for line in result.stdout.split("\n"):
            if line.startswith("STARTUP_TIME:"):
                startup_time = float(line.split(":")[1])
                break

        assert startup_time is not None, "Could not measure startup time"
        # Target: under 200ms for cold start
        assert (
            startup_time < 0.2
        ), f"Cold start took {startup_time:.3f}s, should be < 0.2s"

    def test_lazy_loading_effectiveness(self):
        """Test that expensive imports are loaded lazily."""
        # Measure time to import main module
        start_time = time.perf_counter()
        from commands.main import GenesisCLI

        import_time = time.perf_counter() - start_time

        # Should be fast since expensive operations should be lazy
        assert (
            import_time < 0.1
        ), f"Main module import took {import_time:.3f}s, should be < 0.1s"

        # Initialize CLI without triggering heavy operations
        cli = GenesisCLI()

        # Heavy operations should only happen when needed
        # This is a behavioral test - we're checking that initialization is fast


class TestRuntimePerformance:
    """Test CLI runtime performance - target <2s response time."""

    def test_help_command_response_time(self):
        """Test help command responds quickly."""
        cli = GenesisCLI()

        start_time = time.perf_counter()
        result = cli.run(["help", "quickstart"])
        response_time = time.perf_counter() - start_time

        # Help should be very fast
        assert (
            response_time < 0.5
        ), f"Help command took {response_time:.3f}s, should be < 0.5s"
        assert result == 0

    def test_command_parsing_performance(self):
        """Test command parsing performance."""
        cli = GenesisCLI()
        parser = cli.create_parser()

        # Test various command combinations
        commands_to_test = [
            ["vm", "list-pools"],
            ["container", "list-deployments"],
            ["infra", "status"],
            ["agent", "status"],
            ["--help"],
        ]

        total_time = 0
        for cmd in commands_to_test:
            start_time = time.perf_counter()
            try:
                args = parser.parse_args(cmd)
                parse_time = time.perf_counter() - start_time
                total_time += parse_time

                # Each parse should be fast
                assert (
                    parse_time < 0.01
                ), f"Parsing {cmd} took {parse_time:.3f}s, should be < 0.01s"
            except SystemExit:
                # Expected for --help
                pass

        # Average parse time should be very fast
        avg_time = total_time / len(commands_to_test)
        assert (
            avg_time < 0.005
        ), f"Average parse time {avg_time:.3f}s, should be < 0.005s"

    def test_output_formatting_performance(self):
        """Test output formatting performance with large datasets."""
        from ui.formatter import OutputFormatter

        formatter = OutputFormatter()

        # Create large test dataset
        large_dataset = [
            {"id": i, "name": f"item_{i}", "value": i * 100, "status": "active"}
            for i in range(1000)
        ]

        # Test different format types
        formats_to_test = ["json", "yaml", "table", "list"]

        for format_type in formats_to_test:
            start_time = time.perf_counter()
            result = formatter.format_output(large_dataset, format_type)
            format_time = time.perf_counter() - start_time

            # Should format even large datasets quickly
            assert (
                format_time < 1.0
            ), f"Formatting {len(large_dataset)} items as {format_type} took {format_time:.3f}s, should be < 1.0s"
            assert result is not None
            assert len(result) > 0

    def test_progress_indicator_overhead(self):
        """Test that progress indicators don't add significant overhead."""
        from ui.progress import ProgressIndicator

        progress = ProgressIndicator()

        # Measure overhead of progress updates
        start_time = time.perf_counter()

        progress.start("Testing performance")
        for i in range(100):
            progress.update(i, f"Step {i}")
        progress.stop("Complete")

        total_time = time.perf_counter() - start_time

        # Progress updates should be very lightweight
        assert (
            total_time < 0.1
        ), f"100 progress updates took {total_time:.3f}s, should be < 0.1s"

    def test_concurrent_operations_performance(self):
        """Test performance with concurrent operations."""
        from ui.progress import TaskProgress

        def simulate_task(task_id):
            """Simulate a task with progress updates."""
            progress = TaskProgress(10, task_name=f"Task {task_id}")
            progress.start()

            for i in range(10):
                progress.next_step(f"Step {i}")
                time.sleep(0.001)  # Minimal sleep to simulate work

            progress.complete()
            return task_id

        # Run multiple tasks concurrently
        start_time = time.perf_counter()

        with multiprocessing.dummy.Pool(5) as pool:
            results = pool.map(simulate_task, range(5))

        concurrent_time = time.perf_counter() - start_time

        # Concurrent operations should complete efficiently
        assert (
            concurrent_time < 2.0
        ), f"5 concurrent tasks took {concurrent_time:.3f}s, should be < 2.0s"
        assert len(results) == 5


class TestMemoryEfficiency:
    """Test memory usage and efficiency."""

    def test_memory_usage_initialization(self):
        """Test memory usage during initialization."""
        import psutil
        import gc

        # Force garbage collection
        gc.collect()

        # Get baseline memory
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Initialize CLI
        cli = GenesisCLI()

        # Force garbage collection again
        gc.collect()

        # Measure memory after initialization
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = after_memory - baseline_memory

        # CLI should not use excessive memory
        assert (
            memory_increase < 50
        ), f"CLI initialization increased memory by {memory_increase:.1f}MB, should be < 50MB"

    def test_memory_cleanup_after_operations(self):
        """Test that memory is properly cleaned up after operations."""
        import psutil
        import gc

        process = psutil.Process()
        cli = GenesisCLI()

        # Get memory after CLI initialization
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024

        # Perform several operations
        for i in range(10):
            # Simulate operations that might create temporary objects
            data = [{"id": j, "data": f"test_{j}" * 100} for j in range(100)]
            formatted = cli.format_output(data, "json")
            del data, formatted

        # Force cleanup
        gc.collect()

        # Check memory after operations
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory

        # Memory should not grow excessively
        assert (
            memory_growth < 20
        ), f"Memory grew by {memory_growth:.1f}MB after operations, should be < 20MB"

    def test_cache_memory_efficiency(self):
        """Test that caching doesn't consume excessive memory."""
        from ui.terminal import TerminalAdapter
        from ui.colors import ColorScheme

        # Create components with caching
        terminal_adapter = TerminalAdapter()
        color_scheme = ColorScheme()

        # Trigger cache population
        _ = terminal_adapter.width
        _ = terminal_adapter.height
        _ = terminal_adapter.get_capabilities()
        _ = color_scheme.supports_color
        _ = color_scheme.detect_color_level()

        # Caches should be populated but not excessive
        assert terminal_adapter._capabilities is not None
        assert color_scheme._color_level is not None

        # Cache data structures should be reasonable size
        import sys

        capabilities_size = sys.getsizeof(terminal_adapter._capabilities)
        assert (
            capabilities_size < 1024
        ), f"Capabilities cache is {capabilities_size} bytes, should be < 1KB"


class TestPerformanceService:
    """Test performance monitoring service."""

    def test_performance_service_initialization(self):
        """Test performance service initializes correctly."""
        service = PerformanceService()
        assert service is not None

        # Should have basic performance tracking capabilities
        assert hasattr(service, "start_operation")
        assert hasattr(service, "end_operation")

    def test_operation_timing(self):
        """Test operation timing functionality."""
        service = PerformanceService()

        operation_id = service.start_operation("test_operation")

        # Simulate some work
        time.sleep(0.01)

        duration = service.end_operation(operation_id)

        # Should measure time accurately
        assert duration >= 0.01
        assert duration < 0.1  # Should be close to sleep time

    def test_performance_metrics_collection(self):
        """Test performance metrics collection."""
        service = PerformanceService()

        # Perform several operations
        for i in range(5):
            op_id = service.start_operation(f"operation_{i}")
            time.sleep(0.001)
            service.end_operation(op_id)

        # Should collect metrics
        metrics = service.get_metrics()
        assert metrics is not None
        assert len(metrics) > 0

    def test_performance_thresholds(self):
        """Test performance threshold monitoring."""
        service = PerformanceService()

        # Set a threshold
        service.set_threshold("slow_operation", 0.5)

        # Test fast operation
        op_id = service.start_operation("fast_operation")
        time.sleep(0.001)
        duration = service.end_operation(op_id)

        assert not service.exceeds_threshold("slow_operation", duration)

        # Test slow operation
        slow_duration = 0.6
        assert service.exceeds_threshold("slow_operation", slow_duration)


@pytest.mark.benchmark
class TestBenchmarks:
    """Benchmark tests for performance validation."""

    def test_cli_startup_benchmark(self):
        """Benchmark CLI startup time across multiple runs."""
        startup_times = []

        for _ in range(10):
            start_time = time.perf_counter()
            cli = GenesisCLI()
            parser = cli.create_parser()
            startup_time = time.perf_counter() - start_time
            startup_times.append(startup_time)

            # Clean up
            del cli, parser

        avg_startup = sum(startup_times) / len(startup_times)
        max_startup = max(startup_times)
        min_startup = min(startup_times)

        print(
            f"Startup times: avg={avg_startup:.3f}s, min={min_startup:.3f}s, max={max_startup:.3f}s"
        )

        # Performance targets
        assert (
            avg_startup < 0.1
        ), f"Average startup time {avg_startup:.3f}s exceeds 0.1s target"
        assert (
            max_startup < 0.2
        ), f"Maximum startup time {max_startup:.3f}s exceeds 0.2s target"

    def test_output_formatting_benchmark(self):
        """Benchmark output formatting performance."""
        from ui.formatter import OutputFormatter

        formatter = OutputFormatter()

        # Test datasets of different sizes
        dataset_sizes = [10, 100, 1000, 5000]

        for size in dataset_sizes:
            dataset = [{"id": i, "name": f"item_{i}", "value": i} for i in range(size)]

            # Benchmark JSON formatting
            start_time = time.perf_counter()
            json_result = formatter.format_json(dataset)
            json_time = time.perf_counter() - start_time

            # Benchmark table formatting
            start_time = time.perf_counter()
            table_result = formatter.format_table(dataset)
            table_time = time.perf_counter() - start_time

            print(
                f"Dataset size {size}: JSON={json_time:.3f}s, Table={table_time:.3f}s"
            )

            # Performance should scale reasonably
            per_item_json = json_time / size
            per_item_table = table_time / size

            assert (
                per_item_json < 0.001
            ), f"JSON formatting too slow: {per_item_json:.6f}s per item"
            assert (
                per_item_table < 0.001
            ), f"Table formatting too slow: {per_item_table:.6f}s per item"

    def test_terminal_adaptation_benchmark(self):
        """Benchmark terminal adaptation performance."""
        from ui.terminal import TerminalAdapter

        adapter = TerminalAdapter()

        # Benchmark capability detection
        detection_times = []
        for _ in range(100):
            adapter.invalidate_cache()  # Force re-detection
            start_time = time.perf_counter()
            capabilities = adapter.get_capabilities()
            detection_time = time.perf_counter() - start_time
            detection_times.append(detection_time)

        avg_detection = sum(detection_times) / len(detection_times)

        print(f"Average capability detection time: {avg_detection:.6f}s")

        # Should be very fast
        assert (
            avg_detection < 0.001
        ), f"Capability detection too slow: {avg_detection:.6f}s average"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow and not benchmark"])
