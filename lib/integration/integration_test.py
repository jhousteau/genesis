#!/usr/bin/env python3
"""
Integration Test Suite
Comprehensive tests for the complete system integration
"""

import os
import sys
import time
from datetime import datetime
from typing import Any, Dict

# Add the integration module to path
sys.path.insert(0, os.path.dirname(__file__))

from component_registry import ComponentState, ComponentType, get_registry
from config_manager import get_config_manager
from event_bus import EventPriority, EventType, get_event_bus
from health_aggregator import (CheckType, HealthCheck, HealthStatus,
                               get_health_aggregator)

from . import get_system_integrator


class IntegrationTester:
    """Comprehensive integration test suite"""

    def __init__(self):
        self.test_results = {}
        self.temp_files = []

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        print("🧪 Starting Comprehensive Integration Tests")
        print("=" * 60)

        tests = [
            ("Component Registry", self.test_component_registry),
            ("Event Bus", self.test_event_bus),
            ("Configuration Manager", self.test_config_manager),
            ("Health Aggregator", self.test_health_aggregator),
            ("System Integration", self.test_system_integration),
            ("Cross-Component Communication", self.test_cross_component_communication),
            ("End-to-End Workflow", self.test_end_to_end_workflow),
        ]

        for test_name, test_func in tests:
            print(f"\n🔍 Testing: {test_name}")
            try:
                result = test_func()
                self.test_results[test_name] = result
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                print(f"   {status}: {result.get('message', '')}")

                if not result["success"] and "error" in result:
                    print(f"   Error: {result['error']}")

            except Exception as e:
                self.test_results[test_name] = {
                    "success": False,
                    "error": str(e),
                    "message": "Test execution failed",
                }
                print(f"   ❌ FAIL: Test execution failed - {e}")

        # Cleanup
        self.cleanup()

        # Generate summary
        return self.generate_summary()

    def test_component_registry(self) -> Dict[str, Any]:
        """Test component registry functionality"""
        registry = get_registry()

        try:
            # Test component registration
            component_id = registry.register(
                name="test_component",
                component_type=ComponentType.CUSTOM,
                version="1.0.0",
                description="Test component for integration testing",
                capabilities=[],
                dependencies=[],
            )

            # Test component discovery
            components = registry.discover(component_type=ComponentType.CUSTOM)
            test_component = next(
                (c for c in components if c.metadata.name == "test_component"), None
            )

            if not test_component:
                return {
                    "success": False,
                    "message": "Component registration/discovery failed",
                }

            # Test state updates
            registry.update_state(component_id, ComponentState.RUNNING)
            updated_component = registry.locate(component_id)

            if updated_component.state != ComponentState.RUNNING:
                return {"success": False, "message": "State update failed"}

            # Test heartbeat
            registry.heartbeat(component_id, {"cpu": 50.0, "memory": 30.0})

            # Test cleanup
            registry.unregister(component_id)

            return {
                "success": True,
                "message": "All registry operations successful",
                "component_id": component_id,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_event_bus(self) -> Dict[str, Any]:
        """Test event bus functionality"""
        event_bus = get_event_bus()

        try:
            # Test event publishing and subscription
            received_events = []

            def event_handler(event):
                received_events.append(event)

            # Subscribe to test events
            sub_id = event_bus.subscribe(
                pattern="test.*",
                callback=event_handler,
                subscriber_id="integration_tester",
            )

            # Publish test event
            event_id = event_bus.publish(
                event_type="test.integration",
                data={"test": True, "timestamp": datetime.now().isoformat()},
                source="integration_tester",
                priority=EventPriority.NORMAL,
            )

            # Wait for event processing
            time.sleep(0.5)

            # Check if event was received
            if not received_events:
                return {"success": False, "message": "Event not received"}

            received_event = received_events[0]
            if received_event.data.get("test") != True:
                return {"success": False, "message": "Event data incorrect"}

            # Test request-reply pattern
            def reply_handler(event):
                if event.type == "test.request":
                    event_bus.reply(
                        original_event=event,
                        data={"reply": True, "received": event.data},
                        source="integration_tester",
                    )

            reply_sub_id = event_bus.subscribe(
                pattern="test.request",
                callback=reply_handler,
                subscriber_id="reply_handler",
            )

            # Send request and wait for reply
            reply_event = event_bus.request_reply(
                event_type="test.request",
                data={"request": True},
                source="integration_tester",
                target="reply_handler",
                timeout=2.0,
            )

            if not reply_event or not reply_event.data.get("reply"):
                return {"success": False, "message": "Request-reply failed"}

            # Cleanup subscriptions
            event_bus.unsubscribe(sub_id)
            event_bus.unsubscribe(reply_sub_id)

            return {
                "success": True,
                "message": "All event bus operations successful",
                "events_received": len(received_events),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_config_manager(self) -> Dict[str, Any]:
        """Test configuration manager functionality"""
        config_manager = get_config_manager()

        try:
            # Test setting and getting configuration
            test_key = "integration.test.value"
            test_value = "test_configuration_value"

            config_manager.set(test_key, test_value)
            retrieved_value = config_manager.get(test_key)

            if retrieved_value != test_value:
                return {"success": False, "message": "Configuration set/get failed"}

            # Test configuration listening
            change_events = []

            def config_listener(key, old_value, new_value):
                change_events.append(
                    {"key": key, "old_value": old_value, "new_value": new_value}
                )

            config_manager.add_listener("integration.test.*", config_listener)

            # Update configuration
            new_value = "updated_test_value"
            config_manager.set(test_key, new_value)

            # Wait for listener to be called
            time.sleep(0.1)

            if not change_events:
                return {
                    "success": False,
                    "message": "Configuration change listener not called",
                }

            change_event = change_events[0]
            if change_event["new_value"] != new_value:
                return {
                    "success": False,
                    "message": "Configuration change event incorrect",
                }

            # Test nested configuration
            config_manager.set("integration.nested.deep.value", 42)
            nested_value = config_manager.get("integration.nested.deep.value")

            if nested_value != 42:
                return {"success": False, "message": "Nested configuration failed"}

            # Test configuration export
            all_config = config_manager.get_all("integration")
            if "test" not in all_config or "nested" not in all_config:
                return {"success": False, "message": "Configuration export failed"}

            return {
                "success": True,
                "message": "All configuration operations successful",
                "change_events": len(change_events),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_health_aggregator(self) -> Dict[str, Any]:
        """Test health aggregator functionality"""
        health_aggregator = get_health_aggregator()

        try:
            # Add test health checks
            test_check_passing = HealthCheck(
                name="test_passing_check",
                component="test_component",
                check_type=CheckType.LIVENESS,
                function=lambda: True,  # Always passes
                interval=1,
            )

            test_check_failing = HealthCheck(
                name="test_failing_check",
                component="test_component",
                check_type=CheckType.READINESS,
                function=lambda: False,  # Always fails
                interval=1,
            )

            health_aggregator.add_check(test_check_passing)
            health_aggregator.add_check(test_check_failing)

            # Start monitoring briefly
            health_aggregator.start_monitoring()
            time.sleep(2)  # Let it run a few checks
            health_aggregator.stop_monitoring()

            # Check component health
            component_health = health_aggregator.get_component_health("test_component")
            if not component_health:
                return {"success": False, "message": "Component health not found"}

            # Should be degraded due to failing check
            if component_health.status not in [
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]:
                return {
                    "success": False,
                    "message": f"Expected degraded/unhealthy, got {component_health.status}",
                }

            # Check that both checks were executed
            if "test_passing_check" not in component_health.checks:
                return {"success": False, "message": "Passing check not executed"}

            if "test_failing_check" not in component_health.checks:
                return {"success": False, "message": "Failing check not executed"}

            # Verify check results
            if component_health.checks["test_passing_check"] != True:
                return {"success": False, "message": "Passing check should pass"}

            if component_health.checks["test_failing_check"] != False:
                return {"success": False, "message": "Failing check should fail"}

            # Test system health
            system_health = health_aggregator.get_system_health()
            if not system_health:
                return {"success": False, "message": "System health not available"}

            # Cleanup
            health_aggregator.remove_check("test_passing_check", "test_component")
            health_aggregator.remove_check("test_failing_check", "test_component")

            return {
                "success": True,
                "message": "All health monitoring operations successful",
                "component_status": component_health.status.value,
                "system_score": system_health.score,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_system_integration(self) -> Dict[str, Any]:
        """Test the main system integrator"""
        integrator = get_system_integrator()

        try:
            # Test component integration
            component_id = integrator.integrate_new_component(
                name="test_integrated_component",
                component_type=ComponentType.CUSTOM,
                capabilities=["test_capability"],
                dependencies=[],
                config={"enabled": True, "test_setting": "integration_test"},
            )

            # Verify component was registered
            registry = get_registry()
            component = registry.locate(component_id)
            if not component:
                return {
                    "success": False,
                    "message": "Component not found after integration",
                }

            # Verify configuration was set
            config_manager = get_config_manager()
            config_value = config_manager.get(
                "components.test_integrated_component.enabled"
            )
            if config_value != True:
                return {
                    "success": False,
                    "message": "Component configuration not set correctly",
                }

            # Test integration status
            status = integrator.get_integration_status()
            if not status["initialized"]:
                return {"success": False, "message": "System not properly initialized"}

            # Test monitoring start/stop
            integrator.start_monitoring()
            time.sleep(1)
            integrator.stop_monitoring()

            return {
                "success": True,
                "message": "System integration successful",
                "component_id": component_id,
                "status": status,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_cross_component_communication(self) -> Dict[str, Any]:
        """Test communication between components through the integration layer"""
        try:
            event_bus = get_event_bus()
            config_manager = get_config_manager()

            # Test configuration change triggering events
            config_events = []

            def config_event_handler(event):
                if event.type == EventType.CONFIG_CHANGED:
                    config_events.append(event)

            event_bus.subscribe(
                pattern="config.*",
                callback=config_event_handler,
                subscriber_id="cross_component_tester",
            )

            # Change configuration (should trigger event through integration)
            config_manager.set("cross_component.test", "trigger_event")

            # Wait for event
            time.sleep(0.5)

            if not config_events:
                return {
                    "success": False,
                    "message": "Configuration change did not trigger event",
                }

            # Test component event affecting health
            health_aggregator = get_health_aggregator()

            # Publish component started event
            event_bus.publish(
                event_type=EventType.COMPONENT_STARTED,
                data={"component": "cross_component_test"},
                source="cross_component_tester",
            )

            # Check if health monitoring was added
            time.sleep(0.5)
            component_health = health_aggregator.get_component_health(
                "cross_component_test"
            )

            return {
                "success": True,
                "message": "Cross-component communication successful",
                "config_events": len(config_events),
                "health_added": component_health is not None,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_end_to_end_workflow(self) -> Dict[str, Any]:
        """Test complete end-to-end workflow"""
        try:
            integrator = get_system_integrator()

            # Simulate complete component lifecycle

            # 1. Register new component
            component_id = integrator.integrate_new_component(
                name="e2e_test_component",
                component_type=ComponentType.CUSTOM,
                capabilities=["data_processing", "api_endpoint"],
                dependencies=["registry"],
                config={"port": 8080, "debug": True, "max_connections": 100},
            )

            # 2. Start monitoring
            integrator.start_monitoring()

            # 3. Simulate component activity
            event_bus = get_event_bus()

            # Component started
            event_bus.publish(
                event_type=EventType.COMPONENT_STARTED,
                data={"component": "e2e_test_component", "pid": 12345},
                source="e2e_test_component",
            )

            # Component processing data
            event_bus.publish(
                event_type="data.processed",
                data={"records": 1000, "duration": 5.2},
                source="e2e_test_component",
            )

            # 4. Configuration update
            config_manager = get_config_manager()
            config_manager.set("components.e2e_test_component.max_connections", 200)

            # 5. Health status check
            time.sleep(2)  # Let monitoring run
            health_aggregator = get_health_aggregator()
            system_health = health_aggregator.get_system_health()

            # 6. Component shutdown
            event_bus.publish(
                event_type=EventType.COMPONENT_STOPPED,
                data={"component": "e2e_test_component", "reason": "shutdown"},
                source="e2e_test_component",
            )

            # 7. Cleanup
            integrator.stop_monitoring()

            # Verify final state
            final_status = integrator.get_integration_status()

            return {
                "success": True,
                "message": "End-to-end workflow completed successfully",
                "component_id": component_id,
                "final_health_score": system_health.score,
                "total_components": final_status["registry"]["total_components"],
                "events_published": final_status["event_bus"]["events_published"],
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cleanup(self):
        """Cleanup test resources"""
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(
            1 for result in self.test_results.values() if result["success"]
        )
        failed_tests = total_tests - passed_tests

        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        print("\n" + "=" * 60)
        print("📊 INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {success_rate:.1f}%")

        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for test_name, result in self.test_results.items():
                if not result["success"]:
                    print(f"   - {test_name}: {result.get('message', 'Unknown error')}")

        overall_success = failed_tests == 0
        status_emoji = "🎉" if overall_success else "⚠️"
        status_text = "PASS" if overall_success else "FAIL"

        print(f"\n{status_emoji} OVERALL STATUS: {status_text}")
        print("=" * 60)

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_success": overall_success,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "test_results": self.test_results,
        }


def main():
    """Main entry point for integration tests"""
    tester = IntegrationTester()
    summary = tester.run_all_tests()

    # Exit with appropriate code
    exit_code = 0 if summary["overall_success"] else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
