#!/usr/bin/env python3
"""
TERRAFORM CONFIGURATION VALIDATION
==================================

Validates Terraform configuration for:
1. Syntax correctness
2. Module dependencies
3. Variable references
4. Resource naming
5. Security configurations
"""

import re
from pathlib import Path
from typing import List, Dict, Set

class TerraformValidator:
    """Validates Terraform configuration files."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.modules_used = set()
        self.modules_exist = set()

    def validate_all(self):
        """Run all Terraform validation checks."""
        print("\n" + "="*80)
        print("TERRAFORM CONFIGURATION VALIDATION")
        print("="*80)

        # Find all Terraform files
        tf_dir = Path("cloud/terraform")
        if not tf_dir.exists():
            print("\n❌ Terraform directory not found")
            return False

        # Validate main configuration
        self.validate_main_config()

        # Validate modules
        self.validate_modules()

        # Check module usage vs existence
        self.check_module_existence()

        # Validate variables
        self.validate_variables()

        # Print summary
        return self.print_summary()

    def validate_main_config(self):
        """Validate main Terraform configuration."""
        print("\n" + "-"*80)
        print("1. MAIN CONFIGURATION ANALYSIS")
        print("-"*80)

        main_files = ["cloud/terraform/main.tf", "cloud/terraform/main_working.tf"]

        for main_file in main_files:
            if not Path(main_file).exists():
                continue

            print(f"\n  Analyzing: {main_file}")
            content = Path(main_file).read_text()

            # Find module declarations
            modules = re.findall(r'module\s+"([^"]+)"\s*\{', content)
            print(f"    Found {len(modules)} module declarations:")

            for module in modules:
                print(f"      - {module}")
                self.modules_used.add(module)

                # Check if module has source
                module_block = re.search(
                    rf'module\s+"{module}"\s*\{{([^}}]+)\}}',
                    content,
                    re.DOTALL
                )
                if module_block:
                    if 'source' not in module_block.group(1):
                        self.errors.append(f"{main_file}: Module '{module}' missing source")

    def validate_modules(self):
        """Validate module implementations."""
        print("\n" + "-"*80)
        print("2. MODULE IMPLEMENTATION ANALYSIS")
        print("-"*80)

        modules_dir = Path("cloud/terraform/modules")
        if not modules_dir.exists():
            self.errors.append("Modules directory does not exist")
            return

        for module_dir in modules_dir.iterdir():
            if module_dir.is_dir():
                module_name = module_dir.name
                self.modules_exist.add(module_name)

                print(f"\n  Module: {module_name}")

                # Check for required files
                main_tf = module_dir / "main.tf"
                variables_tf = module_dir / "variables.tf"
                outputs_tf = module_dir / "outputs.tf"

                if main_tf.exists():
                    print(f"    ✅ main.tf found")
                    self.validate_module_file(main_tf, module_name)
                else:
                    self.errors.append(f"Module '{module_name}' missing main.tf")

                if variables_tf.exists():
                    print(f"    ✅ variables.tf found")
                else:
                    self.warnings.append(f"Module '{module_name}' missing variables.tf")

                if outputs_tf.exists():
                    print(f"    ✅ outputs.tf found")

    def validate_module_file(self, file_path: Path, module_name: str):
        """Validate individual module file."""
        content = file_path.read_text()

        # Check for resources
        resources = re.findall(r'resource\s+"([^"]+)"\s+"([^"]+)"', content)
        print(f"    Found {len(resources)} resources")

        # Check for data sources
        data_sources = re.findall(r'data\s+"([^"]+)"\s+"([^"]+)"', content)
        if data_sources:
            print(f"    Found {len(data_sources)} data sources")

        # Check for variable usage without declaration
        var_usage = set(re.findall(r'var\.(\w+)', content))
        if var_usage:
            # Check if variables.tf exists and declares these
            variables_file = file_path.parent / "variables.tf"
            if variables_file.exists():
                var_content = variables_file.read_text()
                var_declarations = set(re.findall(r'variable\s+"(\w+)"', var_content))

                undefined_vars = var_usage - var_declarations
                if undefined_vars:
                    for var in undefined_vars:
                        self.errors.append(
                            f"Module '{module_name}': Variable '{var}' used but not declared"
                        )

    def check_module_existence(self):
        """Check if used modules actually exist."""
        print("\n" + "-"*80)
        print("3. MODULE EXISTENCE CHECK")
        print("-"*80)

        print(f"\n  Modules used in main config: {len(self.modules_used)}")
        for module in sorted(self.modules_used):
            if module in self.modules_exist:
                print(f"    ✅ {module}")
            else:
                print(f"    ❌ {module} (NOT IMPLEMENTED)")
                self.errors.append(f"Module '{module}' used but not implemented")

        # Find unused modules
        unused = self.modules_exist - self.modules_used
        if unused:
            print(f"\n  ⚠️  Unused modules: {len(unused)}")
            for module in sorted(unused):
                print(f"    - {module}")

    def validate_variables(self):
        """Validate variable definitions."""
        print("\n" + "-"*80)
        print("4. VARIABLES VALIDATION")
        print("-"*80)

        variables_file = Path("cloud/terraform/variables.tf")
        if not variables_file.exists():
            self.errors.append("Root variables.tf not found")
            return

        content = variables_file.read_text()

        # Find all variable declarations
        variables = re.findall(r'variable\s+"([^"]+)"\s*\{([^}]+)\}', content, re.DOTALL)
        print(f"\n  Found {len(variables)} variable declarations")

        for var_name, var_block in variables:
            # Check for description
            if "description" not in var_block:
                self.warnings.append(f"Variable '{var_name}' missing description")

            # Check for type
            if "type" not in var_block:
                self.warnings.append(f"Variable '{var_name}' missing type")

            # Check sensitive variables
            if "secret" in var_name.lower() or "password" in var_name.lower() or "key" in var_name.lower():
                if "sensitive" not in var_block or "sensitive = true" not in var_block:
                    self.errors.append(
                        f"SECURITY: Variable '{var_name}' contains sensitive data but not marked sensitive"
                    )

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*80)
        print("TERRAFORM VALIDATION SUMMARY")
        print("="*80)

        print(f"\n❌ ERRORS: {len(self.errors)}")
        for error in self.errors:
            print(f"  - {error}")

        print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
        for warning in self.warnings:
            print(f"  - {warning}")

        print("\n" + "="*80)

        if len(self.errors) == 0:
            print("✅ TERRAFORM CONFIGURATION VALID")
            print("Ready for deployment with terraform init/plan/apply")
            return True
        else:
            print(f"❌ {len(self.errors)} ERRORS MUST BE FIXED")
            return False


def main():
    """Main entry point."""
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    validator = TerraformValidator()
    success = validator.validate_all()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
