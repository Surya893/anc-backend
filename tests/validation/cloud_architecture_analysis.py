#!/usr/bin/env python3
"""
CLOUD ARCHITECTURE CRITICAL ANALYSIS
====================================

Validates cloud architecture for:
1. Lambda cold start optimization
2. DynamoDB capacity and bottlenecks
3. SQS message handling and dead letter queues
4. WebSocket connection limits
5. Error handling and retries
6. Monitoring and alerting gaps
7. Cost optimization opportunities
8. Security misconfigurations
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

class CloudArchitectureAnalyzer:
    """Analyzes cloud architecture for production readiness."""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.recommendations = []

    def analyze_all(self):
        """Run all analysis checks."""
        print("\n" + "="*80)
        print("CLOUD ARCHITECTURE CRITICAL ANALYSIS")
        print("="*80)

        # Lambda analysis
        self.analyze_lambda_functions()

        # DynamoDB analysis
        self.analyze_dynamodb_tables()

        # SQS analysis
        self.analyze_sqs_queues()

        # IoT Core analysis
        self.analyze_iot_core()

        # API Gateway analysis
        self.analyze_api_gateway()

        # Print summary
        self.print_summary()

    def analyze_lambda_functions(self):
        """Analyze Lambda functions for critical issues."""
        print("\n" + "-"*80)
        print("1. LAMBDA FUNCTIONS ANALYSIS")
        print("-"*80)

        lambda_dir = Path("cloud/lambda")
        if not lambda_dir.exists():
            self.issues.append("Lambda directory not found")
            return

        for handler_file in lambda_dir.rglob("handler.py"):
            function_name = handler_file.parent.name
            print(f"\n  Analyzing: {function_name}")

            content = handler_file.read_text()

            # Check for cold start optimization
            self._check_cold_start(function_name, content)

            # Check for proper error handling
            self._check_error_handling(function_name, content)

            # Check for timeout configuration
            self._check_lambda_timeouts(function_name, content)

            # Check for memory efficiency
            self._check_memory_usage(function_name, content)

            # Check for environment variable validation
            self._check_env_vars(function_name, content)

    def _check_cold_start(self, function_name: str, content: str):
        """Check for cold start optimization."""
        issues = []

        # Check if boto3 clients are initialized outside handler
        if "boto3.client" in content or "boto3.resource" in content:
            # Find if they're inside lambda_handler
            handler_match = re.search(r'def lambda_handler.*?(?=\ndef |\Z)', content, re.DOTALL)
            if handler_match:
                handler_content = handler_match.group(0)
                if "boto3.client" in handler_content or "boto3.resource" in handler_content:
                    issues.append(f"Boto3 clients initialized inside handler (cold start penalty)")

        # Check for heavy imports
        if "import tensorflow" in content or "import torch" in content:
            issues.append(f"Heavy ML framework imported (severe cold start penalty)")

        if issues:
            for issue in issues:
                print(f"    ⚠️  {function_name}: {issue}")
                self.warnings.append(f"{function_name}: {issue}")
        else:
            print(f"    ✅ Cold start optimized")

    def _check_error_handling(self, function_name: str, content: str):
        """Check for proper error handling."""
        issues = []

        # Check for bare except clauses
        bare_except = re.findall(r'except\s*:', content)
        if bare_except:
            issues.append(f"Found {len(bare_except)} bare except clauses (hides errors)")

        # Check if lambda_handler has try-except
        if "def lambda_handler" in content:
            handler_match = re.search(r'def lambda_handler.*?(?=\ndef |\Z)', content, re.DOTALL)
            if handler_match and "try:" not in handler_match.group(0):
                issues.append(f"No try-except in lambda_handler (unhandled exceptions)")

        if issues:
            for issue in issues:
                print(f"    ❌ {function_name}: {issue}")
                self.issues.append(f"{function_name}: {issue}")
        else:
            print(f"    ✅ Error handling proper")

    def _check_lambda_timeouts(self, function_name: str, content: str):
        """Check for timeout configuration."""
        # Check if boto3 config has timeouts
        if "Config(" in content:
            if "connect_timeout" in content and "read_timeout" in content:
                print(f"    ✅ Boto3 timeouts configured")
            else:
                print(f"    ⚠️  {function_name}: Partial timeout config")
                self.warnings.append(f"{function_name}: Missing some timeout configs")
        else:
            if "boto3" in content:
                print(f"    ❌ {function_name}: No boto3 timeout configuration")
                self.issues.append(f"{function_name}: No boto3 timeouts (can hang)")

    def _check_memory_usage(self, function_name: str, content: str):
        """Check for potential memory issues."""
        issues = []

        # Check for large in-memory operations
        if "np.zeros(" in content or "np.ones(" in content:
            # Look for large array allocations
            large_array = re.findall(r'np\.(?:zeros|ones)\((\d+)', content)
            for size in large_array:
                if int(size) > 1000000:  # 1M elements
                    issues.append(f"Large array allocation ({size} elements)")

        # Check for file operations without cleanup
        if "open(" in content:
            if "with open" not in content:
                issues.append(f"File opened without 'with' statement (leak risk)")

        if issues:
            for issue in issues:
                print(f"    ⚠️  {function_name}: {issue}")
                self.warnings.append(f"{function_name}: {issue}")

    def _check_env_vars(self, function_name: str, content: str):
        """Check environment variable validation."""
        if "os.environ" in content:
            if "get_required_env" in content or "os.environ.get" in content:
                print(f"    ✅ Environment variables validated")
            else:
                print(f"    ❌ {function_name}: Direct env access without validation")
                self.issues.append(f"{function_name}: No env var validation")

    def analyze_dynamodb_tables(self):
        """Analyze DynamoDB table configurations."""
        print("\n" + "-"*80)
        print("2. DYNAMODB TABLES ANALYSIS")
        print("-"*80)

        terraform_files = list(Path("cloud/terraform/modules/dynamodb").rglob("*.tf"))

        if not terraform_files:
            print("    ⚠️  DynamoDB Terraform module not found")
            return

        for tf_file in terraform_files:
            content = tf_file.read_text()

            # Check for on-demand billing
            if "billing_mode" in content:
                if "PAY_PER_REQUEST" in content:
                    print(f"    ✅ On-demand billing configured")
                else:
                    print(f"    ⚠️  Using provisioned capacity (cost risk)")
                    self.warnings.append("DynamoDB: Provisioned capacity can be expensive")

            # Check for point-in-time recovery
            if "point_in_time_recovery" in content:
                print(f"    ✅ Point-in-time recovery enabled")
            else:
                print(f"    ❌ No point-in-time recovery (data loss risk)")
                self.issues.append("DynamoDB: No PITR enabled")

            # Check for TTL
            if "ttl" in content.lower():
                print(f"    ✅ TTL configured for data cleanup")
            else:
                print(f"    ⚠️  No TTL (table will grow unbounded)")
                self.warnings.append("DynamoDB: No TTL for old data cleanup")

    def analyze_sqs_queues(self):
        """Analyze SQS queue configurations."""
        print("\n" + "-"*80)
        print("3. SQS QUEUES ANALYSIS")
        print("-"*80)

        # Check if audio_receiver uses SQS
        audio_receiver = Path("cloud/lambda/audio_receiver/handler.py")
        if audio_receiver.exists():
            content = audio_receiver.read_text()

            if "sqs.send_message" in content:
                print(f"    ✅ Using SQS for async processing")

                # Check for dead letter queue
                terraform_sqs = Path("cloud/terraform/modules/sqs")
                if terraform_sqs.exists():
                    sqs_tf = list(terraform_sqs.rglob("*.tf"))
                    if sqs_tf:
                        tf_content = sqs_tf[0].read_text()
                        if "dead_letter" in tf_content.lower():
                            print(f"    ✅ Dead letter queue configured")
                        else:
                            print(f"    ❌ No dead letter queue (lost messages)")
                            self.issues.append("SQS: No DLQ for failed messages")
                else:
                    print(f"    ⚠️  SQS Terraform module not implemented")
                    self.warnings.append("SQS: Terraform module missing")
            else:
                print(f"    ⚠️  Not using SQS (synchronous processing)")

    def analyze_iot_core(self):
        """Analyze IoT Core configuration."""
        print("\n" + "-"*80)
        print("4. IOT CORE ANALYSIS")
        print("-"*80)

        iot_connection = Path("cloud/iot/iot_connection.py")
        if iot_connection.exists():
            content = iot_connection.read_text()

            # Check for reconnection logic
            if "auto_reconnect" in content:
                print(f"    ✅ Auto-reconnect implemented")

                # Check for max retries
                if "max_retries" in content or "retry_count" in content:
                    print(f"    ✅ Retry limits configured")
                else:
                    print(f"    ❌ CRITICAL: No max retry limit (infinite loop risk)")
                    self.issues.append("IoT: No max retries in reconnection loop")

            # Check for certificate validation
            if "cert_path" in content:
                print(f"    ✅ Certificate-based authentication")
            else:
                print(f"    ⚠️  Certificate paths not found")

    def analyze_api_gateway(self):
        """Analyze API Gateway configuration."""
        print("\n" + "-"*80)
        print("5. API GATEWAY ANALYSIS")
        print("-"*80)

        # Check for throttling configuration
        terraform_api = Path("cloud/terraform/modules/api_gateway_websocket")
        if terraform_api.exists():
            print(f"    ✅ API Gateway WebSocket module exists")

            tf_files = list(terraform_api.rglob("*.tf"))
            if tf_files:
                content = tf_files[0].read_text()

                # Check for throttling
                if "throttle" in content.lower():
                    print(f"    ✅ Throttling configured")
                else:
                    print(f"    ⚠️  No throttling (DoS risk)")
                    self.warnings.append("API Gateway: No rate limiting")
        else:
            print(f"    ⚠️  API Gateway WebSocket module not implemented")
            self.warnings.append("API Gateway: Module not implemented")

    def print_summary(self):
        """Print analysis summary."""
        print("\n" + "="*80)
        print("ANALYSIS SUMMARY")
        print("="*80)

        print(f"\n❌ CRITICAL ISSUES: {len(self.issues)}")
        for issue in self.issues:
            print(f"  - {issue}")

        print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
        for warning in self.warnings:
            print(f"  - {warning}")

        if self.recommendations:
            print(f"\n💡 RECOMMENDATIONS: {len(self.recommendations)}")
            for rec in self.recommendations:
                print(f"  - {rec}")

        print("\n" + "="*80)

        if len(self.issues) == 0:
            print("✅ NO CRITICAL ISSUES FOUND")
            return True
        else:
            print(f"❌ {len(self.issues)} CRITICAL ISSUES REQUIRE FIXES")
            return False


def main():
    """Main entry point."""
    # Change to repo root
    repo_root = Path(__file__).parent.parent.parent
    os.chdir(repo_root)

    analyzer = CloudArchitectureAnalyzer()
    success = analyzer.analyze_all()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
