"""Tests for health check functionality."""

from shared_core.health import CheckResult, HealthCheck, HealthStatus


class TestHealthCheck:
    def test_add_and_run_single_check(self):
        """Test adding and running a single health check."""
        health = HealthCheck()
        
        def database_check():
            return CheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection OK"
            )
        
        health.add_check("database", database_check)
        result = health.run_check("database")
        
        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Database connection OK"
        assert result.duration_ms >= 0
    
    def test_run_nonexistent_check(self):
        """Test running a check that doesn't exist."""
        health = HealthCheck()
        result = health.run_check("nonexistent")
        
        assert result.name == "nonexistent"
        assert result.status == HealthStatus.UNHEALTHY
        assert "not found" in result.message
    
    def test_check_exception_handling(self):
        """Test that exceptions in checks are handled gracefully."""
        health = HealthCheck()
        
        def failing_check():
            raise Exception("Something went wrong")
        
        health.add_check("failing", failing_check)
        result = health.run_check("failing")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "Something went wrong" in result.message
        assert result.duration_ms >= 0
    
    def test_run_all_checks(self):
        """Test running multiple health checks."""
        health = HealthCheck()
        
        def healthy_check():
            return CheckResult("healthy", HealthStatus.HEALTHY)
        
        def degraded_check():
            return CheckResult("degraded", HealthStatus.DEGRADED)
        
        health.add_check("check1", healthy_check)
        health.add_check("check2", degraded_check)
        
        results = health.run_all_checks()
        
        assert len(results) == 2
        assert any(r.name == "check1" and r.status == HealthStatus.HEALTHY for r in results)
        assert any(r.name == "check2" and r.status == HealthStatus.DEGRADED for r in results)
    
    def test_overall_status_calculation(self):
        """Test overall status calculation logic."""
        health = HealthCheck()
        
        # No checks = healthy
        assert health.get_overall_status() == HealthStatus.HEALTHY
        
        # All healthy = healthy
        health.add_check("healthy1", lambda: CheckResult("healthy1", HealthStatus.HEALTHY))
        health.add_check("healthy2", lambda: CheckResult("healthy2", HealthStatus.HEALTHY))
        assert health.get_overall_status() == HealthStatus.HEALTHY
        
        # Any degraded = degraded
        health.add_check("degraded", lambda: CheckResult("degraded", HealthStatus.DEGRADED))
        assert health.get_overall_status() == HealthStatus.DEGRADED
        
        # Any unhealthy = unhealthy (takes precedence)
        health.add_check("unhealthy", lambda: CheckResult("unhealthy", HealthStatus.UNHEALTHY))
        assert health.get_overall_status() == HealthStatus.UNHEALTHY
    
    def test_get_summary(self):
        """Test getting comprehensive health summary."""
        health = HealthCheck()
        
        health.add_check("healthy", lambda: CheckResult("healthy", HealthStatus.HEALTHY))
        health.add_check("degraded", lambda: CheckResult("degraded", HealthStatus.DEGRADED))
        health.add_check("unhealthy", lambda: CheckResult("unhealthy", HealthStatus.UNHEALTHY))
        
        summary = health.get_summary()
        
        assert summary["overall_status"] == "unhealthy"
        assert "timestamp" in summary
        assert len(summary["checks"]) == 3
        
        # Check summary counts
        assert summary["summary"]["total_checks"] == 3
        assert summary["summary"]["healthy"] == 1
        assert summary["summary"]["degraded"] == 1
        assert summary["summary"]["unhealthy"] == 1
        
        # Verify check details
        check_names = [check["name"] for check in summary["checks"]]
        assert "healthy" in check_names
        assert "degraded" in check_names
        assert "unhealthy" in check_names
    
    def test_remove_check(self):
        """Test removing health checks."""
        health = HealthCheck()
        
        health.add_check("temp", lambda: CheckResult("temp", HealthStatus.HEALTHY))
        assert len(health.run_all_checks()) == 1
        
        health.remove_check("temp")
        assert len(health.run_all_checks()) == 0
        
        # Removing non-existent check should not error
        health.remove_check("nonexistent")
    
    def test_check_result_with_metadata(self):
        """Test health check results with metadata."""
        health = HealthCheck()
        
        def check_with_metadata():
            return CheckResult(
                name="detailed",
                status=HealthStatus.HEALTHY,
                message="All systems operational",
                metadata={"response_time_ms": 150, "connections": 42}
            )
        
        health.add_check("detailed", check_with_metadata)
        result = health.run_check("detailed")
        
        assert result.metadata["response_time_ms"] == 150
        assert result.metadata["connections"] == 42