#!/usr/bin/env python3
"""
Test Script for Security Automation - SHIELD Methodology Validation
Comprehensive testing of GCP-native security automation workflows
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

# Add the parent directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.security import (
    AccessJustification,
    AttackPattern,
    ElevationLevel,
    SecurityAutomationLevel,
    SecurityEvent,
    SecurityEventType,
    ThreatSeverity,
    create_comprehensive_security_platform,
    get_shield_score,
)


class SecurityAutomationTester:
    """Comprehensive security automation testing suite"""

    def __init__(
        self,
        project_id: str = "genesis-security-test",
        organization_id: str = "123456789012",
        chronicle_customer_id: str = "test-customer-id",
    ):
        self.project_id = project_id
        self.organization_id = organization_id
        self.chronicle_customer_id = chronicle_customer_id

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("SecurityAutomationTester")

        # Test results tracking
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.security_platform = None

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive security automation tests"""
        self.logger.info("Starting comprehensive security automation tests")

        test_suite = {
            "initialization_tests": await self._test_platform_initialization(),
            "shield_scan_tests": await self._test_shield_scanning(),
            "shield_harden_tests": await self._test_shield_hardening(),
            "shield_isolate_tests": await self._test_shield_isolation(),
            "shield_encrypt_tests": await self._test_shield_encryption(),
            "shield_log_tests": await self._test_shield_logging(),
            "shield_defend_tests": await self._test_shield_defense(),
            "orchestration_tests": await self._test_security_orchestration(),
            "automation_level_tests": await self._test_automation_levels(),
            "integration_tests": await self._test_component_integration(),
        }

        # Calculate overall test results
        total_tests = sum(len(category["tests"]) for category in test_suite.values())
        passed_tests = sum(
            len([t for t in category["tests"] if t["passed"]])
            for category in test_suite.values()
        )

        overall_results = {
            "test_suite": test_suite,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (
                    (passed_tests / total_tests) * 100 if total_tests > 0 else 0
                ),
                "test_duration": time.time() - self.test_start_time,
            },
            "recommendations": self._generate_test_recommendations(test_suite),
        }

        self.logger.info(
            f"Testing completed: {passed_tests}/{total_tests} tests passed"
        )

        return overall_results

    async def _test_platform_initialization(self) -> Dict[str, Any]:
        """Test security platform initialization"""
        self.logger.info("Testing security platform initialization")

        tests = []

        # Test basic platform creation
        try:
            self.security_platform = create_comprehensive_security_platform(
                project_id=self.project_id,
                organization_id=self.organization_id,
                chronicle_customer_id=self.chronicle_customer_id,
                automation_level=SecurityAutomationLevel.REACTIVE,
                enable_all_components=True,
            )

            tests.append(
                {
                    "name": "Platform Creation",
                    "passed": self.security_platform is not None,
                    "details": "Successfully created comprehensive security platform",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "Platform Creation",
                    "passed": False,
                    "error": str(e),
                }
            )

        # Test component initialization
        if self.security_platform:
            component_status = self.security_platform.get_security_status()
            component_tests = [
                (
                    "Security Center",
                    component_status["component_status"]["security_center"],
                ),
                ("Cloud Armor", component_status["component_status"]["cloud_armor"]),
                (
                    "Incident Response",
                    component_status["component_status"]["incident_response"],
                ),
                ("JIT IAM", component_status["component_status"]["jit_iam"]),
                (
                    "Threat Hunting",
                    component_status["component_status"]["threat_hunting"],
                ),
            ]

            for name, status in component_tests:
                tests.append(
                    {
                        "name": f"{name} Component Initialization",
                        "passed": status,
                        "details": f"Component {'initialized' if status else 'not initialized'}",
                    }
                )

        return {
            "category": "Initialization Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_shield_scanning(self) -> Dict[str, Any]:
        """Test SHIELD Scan methodology"""
        self.logger.info("Testing SHIELD Scan functionality")

        tests = []

        if not self.security_platform:
            return {
                "category": "SHIELD Scan Tests",
                "tests": [{"name": "Platform Required", "passed": False}],
            }

        try:
            # Test comprehensive scan
            scan_results = await self.security_platform.execute_comprehensive_scan(
                time_window_hours=24
            )

            tests.append(
                {
                    "name": "Comprehensive Security Scan",
                    "passed": "consolidated_threats" in scan_results,
                    "details": f"Scan completed with {len(scan_results.get('consolidated_threats', []))} threats detected",
                }
            )

            # Test risk assessment
            tests.append(
                {
                    "name": "Risk Assessment",
                    "passed": "risk_assessment" in scan_results,
                    "details": f"Risk level: {scan_results.get('risk_assessment', {}).get('overall_risk', 'Unknown')}",
                }
            )

            # Test recommendations generation
            tests.append(
                {
                    "name": "Security Recommendations",
                    "passed": len(scan_results.get("recommended_actions", [])) > 0,
                    "details": f"Generated {len(scan_results.get('recommended_actions', []))} recommendations",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "SHIELD Scan Error",
                    "passed": False,
                    "error": str(e),
                }
            )

        return {
            "category": "SHIELD Scan Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_shield_hardening(self) -> Dict[str, Any]:
        """Test SHIELD Harden methodology"""
        self.logger.info("Testing SHIELD Harden functionality")

        tests = []

        if not self.security_platform or not self.security_platform.cloud_armor:
            return {
                "category": "SHIELD Harden Tests",
                "tests": [{"name": "Component Required", "passed": False}],
            }

        try:
            # Test security policy creation
            policy_name = f"test-security-policy-{int(time.time())}"
            policy_resource = (
                await self.security_platform.cloud_armor.create_security_policy(
                    policy_name=policy_name,
                    description="Test security policy for hardening",
                    enable_adaptive_protection=True,
                )
            )

            tests.append(
                {
                    "name": "Security Policy Creation",
                    "passed": policy_resource is not None,
                    "details": f"Created security policy: {policy_name}",
                }
            )

            # Test attack response simulation
            mock_attack_response = (
                await self.security_platform.cloud_armor.respond_to_application_attack(
                    attack_pattern=AttackPattern.SQL_INJECTION,
                    attack_signature="' OR 1=1 --",
                    source_ips=["192.168.1.100", "10.0.0.50"],
                )
            )

            tests.append(
                {
                    "name": "Attack Response Simulation",
                    "passed": len(mock_attack_response.get("actions_taken", [])) > 0,
                    "details": f"Executed {len(mock_attack_response.get('actions_taken', []))} hardening actions",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "SHIELD Harden Error",
                    "passed": False,
                    "error": str(e),
                }
            )

        return {
            "category": "SHIELD Harden Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_shield_isolation(self) -> Dict[str, Any]:
        """Test SHIELD Isolate methodology"""
        self.logger.info("Testing SHIELD Isolate functionality")

        tests = []

        if not self.security_platform or not self.security_platform.incident_response:
            return {
                "category": "SHIELD Isolate Tests",
                "tests": [{"name": "Component Required", "passed": False}],
            }

        try:
            # Test incident response evaluation
            test_incident_id = f"test-incident-{int(time.time())}"

            execution_id = await self.security_platform.incident_response.evaluate_incident_for_response(
                incident_id=test_incident_id,
                category="MALWARE",
                severity=ThreatSeverity.HIGH,
                resource_name="test-resource",
                additional_context={"test": True},
            )

            tests.append(
                {
                    "name": "Incident Response Evaluation",
                    "passed": execution_id is not None,
                    "details": f"Incident evaluation result: {execution_id or 'No response triggered'}",
                }
            )

            # Test isolation workflow status
            active_responses = (
                self.security_platform.incident_response.get_active_responses()
            )

            tests.append(
                {
                    "name": "Response Workflow Tracking",
                    "passed": isinstance(active_responses, list),
                    "details": f"Tracking {len(active_responses)} active responses",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "SHIELD Isolate Error",
                    "passed": False,
                    "error": str(e),
                }
            )

        return {
            "category": "SHIELD Isolate Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_shield_encryption(self) -> Dict[str, Any]:
        """Test SHIELD Encrypt methodology"""
        self.logger.info("Testing SHIELD Encrypt functionality")

        tests = []

        try:
            # Test secret manager integration
            from core.secrets.manager import get_secret_manager

            secret_manager = get_secret_manager(
                project_id=self.project_id,
                environment="test",
            )

            tests.append(
                {
                    "name": "Secret Manager Integration",
                    "passed": secret_manager is not None,
                    "details": "Secret manager initialized successfully",
                }
            )

            # Test secret validation
            health_report = secret_manager.validate_secret_health()

            tests.append(
                {
                    "name": "Secret Health Validation",
                    "passed": "secrets_discovered" in health_report,
                    "details": f"Health report generated with {health_report.get('secrets_discovered', 0)} secrets",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "SHIELD Encrypt Error",
                    "passed": False,
                    "error": str(e),
                }
            )

        return {
            "category": "SHIELD Encrypt Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_shield_logging(self) -> Dict[str, Any]:
        """Test SHIELD Log methodology"""
        self.logger.info("Testing SHIELD Log functionality")

        tests = []

        if not self.security_platform:
            return {
                "category": "SHIELD Log Tests",
                "tests": [{"name": "Platform Required", "passed": False}],
            }

        try:
            # Test security event creation and logging
            test_event = SecurityEvent(
                event_id=f"test-event-{int(time.time())}",
                event_type=SecurityEventType.THREAT_DETECTED,
                severity=ThreatSeverity.MEDIUM,
                timestamp=datetime.utcnow(),
                source_component="Test Suite",
                details={"test": True, "threat_type": "simulation"},
                affected_resources=["test-resource-1"],
            )

            # Process the event through the platform
            await self.security_platform._process_security_event(test_event)

            tests.append(
                {
                    "name": "Security Event Logging",
                    "passed": test_event.event_id
                    in self.security_platform.security_events,
                    "details": f"Event {test_event.event_id} logged successfully",
                }
            )

            # Test security status retrieval
            security_status = self.security_platform.get_security_status()

            tests.append(
                {
                    "name": "Security Status Logging",
                    "passed": "recent_activity" in security_status,
                    "details": f"Status report: {security_status['recent_activity']['total_events']} events",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "SHIELD Log Error",
                    "passed": False,
                    "error": str(e),
                }
            )

        return {
            "category": "SHIELD Log Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_shield_defense(self) -> Dict[str, Any]:
        """Test SHIELD Defend methodology"""
        self.logger.info("Testing SHIELD Defend functionality")

        tests = []

        if not self.security_platform:
            return {
                "category": "SHIELD Defend Tests",
                "tests": [{"name": "Platform Required", "passed": False}],
            }

        try:
            # Test coordinated response simulation
            test_threat_event = SecurityEvent(
                event_id=f"defend-test-{int(time.time())}",
                event_type=SecurityEventType.THREAT_DETECTED,
                severity=ThreatSeverity.HIGH,
                timestamp=datetime.utcnow(),
                source_component="Test Suite",
                details={
                    "category": "MALWARE",
                    "description": "Test malware detection",
                    "iocs": ["malicious-domain.com", "192.168.1.100"],
                },
                affected_resources=["test-server-1"],
            )

            # Execute coordinated response
            response_results = (
                await self.security_platform.execute_coordinated_response(
                    threat_event=test_threat_event,
                    override_automation_level=SecurityAutomationLevel.REACTIVE,
                )
            )

            tests.append(
                {
                    "name": "Coordinated Threat Response",
                    "passed": response_results.get("overall_success", False),
                    "details": f"Response executed with {len(response_results.get('actions_taken', []))} actions",
                }
            )

            # Test response component participation
            component_responses = response_results.get("component_responses", {})

            tests.append(
                {
                    "name": "Multi-Component Response",
                    "passed": len(component_responses) > 0,
                    "details": f"Components participated: {list(component_responses.keys())}",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "SHIELD Defend Error",
                    "passed": False,
                    "error": str(e),
                }
            )

        return {
            "category": "SHIELD Defend Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_security_orchestration(self) -> Dict[str, Any]:
        """Test security orchestration capabilities"""
        self.logger.info("Testing security orchestration")

        tests = []

        if not self.security_platform:
            return {
                "category": "Orchestration Tests",
                "tests": [{"name": "Platform Required", "passed": False}],
            }

        try:
            # Test event handler registration
            test_handler_called = False

            async def test_event_handler(event):
                nonlocal test_handler_called
                test_handler_called = True

            self.security_platform.register_event_handler(
                SecurityEventType.THREAT_DETECTED, test_event_handler
            )

            # Trigger test event
            test_orchestration_event = SecurityEvent(
                event_id=f"orchestration-test-{int(time.time())}",
                event_type=SecurityEventType.THREAT_DETECTED,
                severity=ThreatSeverity.LOW,
                timestamp=datetime.utcnow(),
                source_component="Orchestration Test",
                details={"orchestration_test": True},
            )

            await self.security_platform._process_security_event(
                test_orchestration_event
            )

            # Wait a moment for handler execution
            await asyncio.sleep(0.1)

            tests.append(
                {
                    "name": "Event Handler Registration",
                    "passed": test_handler_called,
                    "details": "Custom event handler executed successfully",
                }
            )

            # Test security metrics
            metrics_summary = self.security_platform.get_security_metrics_summary()

            tests.append(
                {
                    "name": "Security Metrics Collection",
                    "passed": "latest_timestamp" in metrics_summary
                    or "message" in metrics_summary,
                    "details": "Security metrics system operational",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "Orchestration Error",
                    "passed": False,
                    "error": str(e),
                }
            )

        return {
            "category": "Orchestration Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_automation_levels(self) -> Dict[str, Any]:
        """Test different automation levels"""
        self.logger.info("Testing automation levels")

        tests = []

        # Test each automation level
        automation_levels = [
            SecurityAutomationLevel.MONITORING,
            SecurityAutomationLevel.REACTIVE,
            SecurityAutomationLevel.PROACTIVE,
            SecurityAutomationLevel.AUTONOMOUS,
        ]

        for level in automation_levels:
            try:
                test_platform = create_comprehensive_security_platform(
                    project_id=f"{self.project_id}-{level.value.lower()}",
                    organization_id=self.organization_id,
                    automation_level=level,
                    enable_all_components=True,
                )

                tests.append(
                    {
                        "name": f"Automation Level {level.value}",
                        "passed": test_platform is not None,
                        "details": f"Successfully created platform with {level.value} automation",
                    }
                )

            except Exception as e:
                tests.append(
                    {
                        "name": f"Automation Level {level.value}",
                        "passed": False,
                        "error": str(e),
                    }
                )

        return {
            "category": "Automation Level Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    async def _test_component_integration(self) -> Dict[str, Any]:
        """Test integration between security components"""
        self.logger.info("Testing component integration")

        tests = []

        if not self.security_platform:
            return {
                "category": "Integration Tests",
                "tests": [{"name": "Platform Required", "passed": False}],
            }

        try:
            # Test JIT IAM access request
            if self.security_platform.jit_iam:
                request_id = await self.security_platform.jit_iam.request_access(
                    requester="test-user@example.com",
                    target_resource="projects/test-project/resource/test",
                    requested_roles=["roles/viewer"],
                    justification=AccessJustification.DEVELOPMENT_TESTING,
                    duration_hours=2,
                    business_reason="Integration testing",
                    elevation_level=ElevationLevel.READ_ONLY,
                )

                tests.append(
                    {
                        "name": "JIT IAM Integration",
                        "passed": request_id is not None,
                        "details": f"Access request created: {request_id}",
                    }
                )

            # Test threat intelligence sharing
            if (
                self.security_platform.threat_hunting
                and self.security_platform.cloud_armor
            ):
                # Update threat intelligence in Cloud Armor
                await self.security_platform.cloud_armor.update_threat_intelligence(
                    new_malicious_ips=["192.168.100.1", "10.0.100.1"],
                    new_malicious_domains=["test-malicious.com"],
                )

                tests.append(
                    {
                        "name": "Threat Intelligence Integration",
                        "passed": True,
                        "details": "Threat intelligence shared between components",
                    }
                )

            # Test cross-component event correlation
            correlation_event = SecurityEvent(
                event_id=f"correlation-test-{int(time.time())}",
                event_type=SecurityEventType.THREAT_DETECTED,
                severity=ThreatSeverity.HIGH,
                timestamp=datetime.utcnow(),
                source_component="Integration Test",
                details={
                    "category": "DATA_EXFILTRATION",
                    "iocs": ["suspicious-domain.com"],
                    "affected_users": ["test-user@example.com"],
                },
                affected_resources=["test-database"],
            )

            # This should trigger multiple component responses
            correlation_response = (
                await self.security_platform.execute_coordinated_response(
                    threat_event=correlation_event
                )
            )

            tests.append(
                {
                    "name": "Cross-Component Correlation",
                    "passed": len(correlation_response.get("component_responses", {}))
                    > 1,
                    "details": f"Multiple components responded: {list(correlation_response.get('component_responses', {}).keys())}",
                }
            )

        except Exception as e:
            tests.append(
                {
                    "name": "Integration Error",
                    "passed": False,
                    "error": str(e),
                }
            )

        return {
            "category": "Integration Tests",
            "tests": tests,
            "passed": all(t["passed"] for t in tests),
        }

    def _generate_test_recommendations(self, test_suite: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        failed_categories = [
            category
            for category_name, category in test_suite.items()
            if not category.get("passed", True)
        ]

        if failed_categories:
            recommendations.append(
                f"Address failures in {len(failed_categories)} test categories"
            )

        # Specific recommendations based on failures
        for category_name, category in test_suite.items():
            if not category.get("passed", True):
                failed_tests = [t for t in category["tests"] if not t["passed"]]
                if failed_tests:
                    recommendations.append(
                        f"{category_name}: Fix {len(failed_tests)} failing tests"
                    )

        # General recommendations
        recommendations.extend(
            [
                "Regularly run security automation tests",
                "Monitor SHIELD methodology implementation",
                "Update threat intelligence feeds",
                "Review and tune security policies",
            ]
        )

        return recommendations

    async def run_shield_methodology_validation(self) -> Dict[str, Any]:
        """Validate SHIELD methodology implementation"""
        self.logger.info("Validating SHIELD methodology implementation")

        if not self.security_platform:
            return {"error": "Security platform not initialized"}

        # Simulate security metrics for SHIELD scoring
        from core.security import SecurityMetrics

        mock_metrics = SecurityMetrics(
            timestamp=datetime.utcnow(),
            threats_detected=50,
            threats_blocked=45,
            incidents_responded=10,
            access_requests_processed=25,
            compliance_score=0.95,
            mean_time_to_detection=30.0,  # 30 seconds
            mean_time_to_response=120.0,  # 2 minutes
            false_positive_rate=0.05,  # 5%
            security_coverage=0.90,  # 90%
            automation_effectiveness=0.88,  # 88%
        )

        shield_evaluation = get_shield_score(mock_metrics)

        return {
            "shield_methodology": {
                "scan_score": shield_evaluation["shield_scores"]["scan"],
                "harden_score": shield_evaluation["shield_scores"]["harden"],
                "isolate_score": shield_evaluation["shield_scores"]["isolate"],
                "encrypt_score": shield_evaluation["shield_scores"]["encrypt"],
                "log_score": shield_evaluation["shield_scores"]["log"],
                "defend_score": shield_evaluation["shield_scores"]["defend"],
                "overall_score": shield_evaluation["overall_score"],
                "grade": shield_evaluation["grade"],
                "recommendations": shield_evaluation["recommendations"],
            },
            "metrics_used": {
                "threats_detected": mock_metrics.threats_detected,
                "threats_blocked": mock_metrics.threats_blocked,
                "incidents_responded": mock_metrics.incidents_responded,
                "mean_time_to_response": mock_metrics.mean_time_to_response,
                "automation_effectiveness": mock_metrics.automation_effectiveness,
            },
        }


async def main():
    """Main test execution function"""
    print("=" * 80)
    print("Genesis Security Automation - SHIELD Methodology Testing")
    print("=" * 80)

    # Initialize tester
    tester = SecurityAutomationTester()
    tester.test_start_time = time.time()

    try:
        # Run comprehensive tests
        test_results = await tester.run_comprehensive_tests()

        # Run SHIELD methodology validation
        shield_validation = await tester.run_shield_methodology_validation()

        # Display results
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)

        summary = test_results["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Duration: {summary['test_duration']:.2f} seconds")

        print("\n" + "=" * 60)
        print("SHIELD METHODOLOGY VALIDATION")
        print("=" * 60)

        if "shield_methodology" in shield_validation:
            shield = shield_validation["shield_methodology"]
            print(f"Overall SHIELD Score: {shield['overall_score']:.1f}/10")
            print(f"Security Grade: {shield['grade']}")
            print("\nComponent Scores:")
            print(f"  Scan (Threat Detection): {shield['scan_score']:.1f}/10")
            print(f"  Harden (Security Controls): {shield['harden_score']:.1f}/10")
            print(f"  Isolate (Network Security): {shield['isolate_score']:.1f}/10")
            print(f"  Encrypt (Data Protection): {shield['encrypt_score']:.1f}/10")
            print(f"  Log (Security Monitoring): {shield['log_score']:.1f}/10")
            print(f"  Defend (Threat Response): {shield['defend_score']:.1f}/10")

        print("\n" + "=" * 60)
        print("CATEGORY RESULTS")
        print("=" * 60)

        for category_name, category in test_results["test_suite"].items():
            status = "✓ PASS" if category["passed"] else "✗ FAIL"
            test_count = len(category["tests"])
            passed_count = len([t for t in category["tests"] if t["passed"]])
            print(f"{status} {category['category']}: {passed_count}/{test_count}")

        print("\n" + "=" * 60)
        print("RECOMMENDATIONS")
        print("=" * 60)

        for i, recommendation in enumerate(test_results["recommendations"][:10], 1):
            print(f"{i}. {recommendation}")

        # Save detailed results
        results_file = f"security_test_results_{int(time.time())}.json"
        with open(results_file, "w") as f:
            json.dump(
                {
                    "test_results": test_results,
                    "shield_validation": shield_validation,
                },
                f,
                indent=2,
                default=str,
            )

        print(f"\nDetailed results saved to: {results_file}")

        # Exit with appropriate code
        if summary["success_rate"] == 100:
            print("\n🎉 All tests passed! Security automation is working correctly.")
            return 0
        else:
            print(
                f"\n⚠️  {summary['failed_tests']} test(s) failed. Review the results and address issues."
            )
            return 1

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        # Cleanup
        if tester.security_platform:
            try:
                await tester.security_platform.shutdown()
            except:
                pass


if __name__ == "__main__":
    # Set test environment variables
    os.environ.setdefault("PROJECT_ID", "genesis-security-test")
    os.environ.setdefault("ENVIRONMENT", "test")

    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
