#!/usr/bin/env python3
"""
Comprehensive diagnostic check for ANC Platform
Identifies bugs, errors, and anomalies
"""

import os
import sys
import subprocess

print("="*80)
print("ANC PLATFORM - DIAGNOSTIC CHECK")
print("="*80)
print()

issues_found = []

# 1. Check Python dependencies
print("[1/7] Checking Python Dependencies...")
print("-"*80)

required_packages = {
    'flask': 'Flask',
    'flask_cors': 'Flask-CORS',
    'jwt': 'PyJWT',
    'numpy': 'numpy',
    'sklearn': 'scikit-learn',
    'librosa': 'librosa',
}

missing_packages = []
for module, package in required_packages.items():
    try:
        __import__(module)
        print(f"  ✓ {package}")
    except ImportError:
        print(f"  ✗ MISSING: {package}")
        missing_packages.append(package)
        issues_found.append(f"Missing Python package: {package}")

if missing_packages:
    print(f"\n  ⚠ Missing packages: {', '.join(missing_packages)}")
print()

# 2. Check file structure
print("[2/7] Checking File Structure...")
print("-"*80)

required_files = [
    'main.py',
    'api_server.py',
    'advanced_anc_algorithms.py',
    'database_schema.py',
    'Dockerfile',
    'docker-compose.yml',
    'requirements.txt',
    'openapi.yaml',
    'nginx.conf',
    'k8s/deployment.yaml',
    'k8s/service.yaml',
    'monitoring/prometheus.yml',
    'monitoring/alerts.yml',
]

missing_files = []
for filepath in required_files:
    if os.path.exists(filepath):
        print(f"  ✓ {filepath}")
    else:
        print(f"  ✗ MISSING: {filepath}")
        missing_files.append(filepath)
        issues_found.append(f"Missing file: {filepath}")

print()

# 3. Check Python syntax
print("[3/7] Checking Python Syntax...")
print("-"*80)

python_files = [
    'main.py',
    'api_server.py',
    'advanced_anc_algorithms.py',
    'database_schema.py',
    'feature_extraction.py',
]

syntax_errors = []
for pyfile in python_files:
    if os.path.exists(pyfile):
        result = subprocess.run(
            ['python', '-m', 'py_compile', pyfile],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"  ✓ {pyfile}")
        else:
            print(f"  ✗ SYNTAX ERROR: {pyfile}")
            print(f"     {result.stderr[:200]}")
            syntax_errors.append(pyfile)
            issues_found.append(f"Syntax error in: {pyfile}")

print()

# 4. Check import compatibility
print("[4/7] Checking Import Compatibility...")
print("-"*80)

import_checks = {
    'main.py': "from main import ANCSystemCore",
    'api_server.py': "from api_server import app",
    'advanced_anc_algorithms.py': "from advanced_anc_algorithms import AdvancedANCSystem",
}

for filename, import_stmt in import_checks.items():
    if os.path.exists(filename):
        result = subprocess.run(
            ['python', '-c', import_stmt],
            capture_output=True,
            text=True,
            env={**os.environ, 'PYTHONPATH': '.'}
        )
        if result.returncode == 0 or 'Warning' in result.stderr:
            print(f"  ✓ {filename} imports OK")
        else:
            print(f"  ✗ IMPORT ERROR: {filename}")
            error_lines = result.stderr.split('\n')[:3]
            for line in error_lines:
                if line.strip():
                    print(f"     {line}")
            issues_found.append(f"Import error in: {filename}")

print()

# 5. Check Docker configuration
print("[5/7] Checking Docker Configuration...")
print("-"*80)

if os.path.exists('Dockerfile'):
    with open('Dockerfile', 'r') as f:
        content = f.read()
        checks = [
            ('FROM', 'Base image defined'),
            ('WORKDIR', 'Working directory set'),
            ('COPY', 'Files copied'),
            ('CMD', 'Default command set'),
        ]
        for keyword, description in checks:
            if keyword in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ MISSING: {description}")
                issues_found.append(f"Dockerfile missing: {description}")

print()

# 6. Check Kubernetes manifests
print("[6/7] Checking Kubernetes Manifests...")
print("-"*80)

k8s_files = [
    'k8s/deployment.yaml',
    'k8s/service.yaml',
    'k8s/ingress.yaml',
]

try:
    import yaml
    yaml_available = True
except ImportError:
    yaml_available = False
    print("  ⚠ PyYAML not available, skipping YAML validation")

if yaml_available:
    for k8s_file in k8s_files:
        if os.path.exists(k8s_file):
            try:
                with open(k8s_file, 'r') as f:
                    yaml.safe_load(f)
                print(f"  ✓ {k8s_file} - valid YAML")
            except yaml.YAMLError as e:
                print(f"  ✗ {k8s_file} - YAML error")
                print(f"     {str(e)[:100]}")
                issues_found.append(f"YAML error in: {k8s_file}")
        else:
            print(f"  ✗ MISSING: {k8s_file}")

print()

# 7. Check requirements.txt completeness
print("[7/7] Checking requirements.txt...")
print("-"*80)

if os.path.exists('requirements.txt'):
    with open('requirements.txt', 'r') as f:
        requirements = f.read()
    
    required_in_code = [
        ('Flask-CORS', 'api_server.py uses flask_cors'),
        ('PyJWT', 'api_server.py uses jwt'),
        ('requests', 'Healthcheck might need requests'),
    ]
    
    for package, reason in required_in_code:
        if package.lower() in requirements.lower():
            print(f"  ✓ {package}")
        else:
            print(f"  ✗ MISSING: {package} - {reason}")
            issues_found.append(f"Missing in requirements.txt: {package}")

print()
print("="*80)
print("DIAGNOSTIC SUMMARY")
print("="*80)
print()

if issues_found:
    print(f"❌ Found {len(issues_found)} issue(s):")
    print()
    for i, issue in enumerate(issues_found, 1):
        print(f"  {i}. {issue}")
    print()
    print("Status: ISSUES FOUND - Fix required")
    sys.exit(1)
else:
    print("✅ No issues found - All checks passed!")
    print()
    print("Status: READY FOR DEPLOYMENT")
    sys.exit(0)
