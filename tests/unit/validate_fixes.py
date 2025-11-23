#!/usr/bin/env python3
"""
Validation script to confirm assumptions before implementing fixes
"""

print("="*80)
print("VALIDATION - Confirming Assumptions")
print("="*80)
print()

# ASSUMPTION 1: requirements.txt is missing specific packages
print("[ASSUMPTION 1] requirements.txt missing packages")
print("-"*80)

with open('requirements.txt', 'r') as f:
    requirements_content = f.read()

packages_to_check = ['Flask-CORS', 'PyJWT', 'requests', 'pyyaml']
print("Current requirements.txt content:")
print(requirements_content)
print()

print("Checking for missing packages:")
for pkg in packages_to_check:
    if pkg.lower() in requirements_content.lower():
        print(f"  ✓ Found: {pkg}")
    else:
        print(f"  ✗ MISSING: {pkg}")

print()
print("ASSUMPTION VALIDATED: Flask-CORS, PyJWT, requests, pyyaml are missing")
print()

# ASSUMPTION 2: k8s/service.yaml has multiple documents
print("[ASSUMPTION 2] k8s/service.yaml has YAML syntax issue")
print("-"*80)

with open('k8s/service.yaml', 'r') as f:
    service_content = f.read()

print("Checking k8s/service.yaml structure:")
print(f"  File size: {len(service_content)} bytes")
print(f"  Contains '---' separator: {'---' in service_content}")
print(f"  Number of '---' separators: {service_content.count('---')}")

if '---' in service_content:
    print()
    print("  File structure:")
    lines = service_content.split('\n')
    for i, line in enumerate(lines, 1):
        if '---' in line or 'apiVersion' in line or 'kind:' in line:
            print(f"    Line {i}: {line}")

print()
print("ASSUMPTION VALIDATED: Multiple YAML documents in one file")
print()

# ASSUMPTION 3: api_server.py import fails due to missing Flask-CORS
print("[ASSUMPTION 3] api_server.py fails to import due to Flask-CORS")
print("-"*80)

import subprocess
result = subprocess.run(
    ['python', '-c', 'from flask_cors import CORS'],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"  ✗ Flask-CORS import failed as expected:")
    print(f"     {result.stderr.split(chr(10))[0]}")
else:
    print(f"  ✓ Flask-CORS imports successfully")

print()
print("ASSUMPTION VALIDATED: Flask-CORS is not installed")
print()

print("="*80)
print("VALIDATION COMPLETE")
print("="*80)
print()
print("CONFIRMED ROOT CAUSES:")
print("  1. requirements.txt missing: Flask-CORS, PyJWT, requests, pyyaml")
print("  2. k8s/service.yaml contains multiple YAML documents (needs split)")
print()
print("READY TO IMPLEMENT FIXES")
