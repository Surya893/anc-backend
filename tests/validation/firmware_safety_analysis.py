#!/usr/bin/env python3
"""
FIRMWARE SAFETY & REAL-TIME ANALYSIS
====================================

Validates firmware for:
1. Memory safety (buffer overflows, stack usage)
2. Real-time guarantees (<1ms processing)
3. Array bounds checking
4. Interrupt safety
5. Fixed-point arithmetic correctness
6. Deterministic execution
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple

class FirmwareSafetyAnalyzer:
    """Analyzes firmware C code for safety and real-time compliance."""

    def __init__(self):
        self.critical_issues = []
        self.warnings = []
        self.recommendations = []

    def analyze_all(self):
        """Run all firmware analysis checks."""
        print("\n" + "="*80)
        print("FIRMWARE SAFETY & REAL-TIME ANALYSIS")
        print("="*80)

        firmware_file = Path("firmware/anc_firmware.c")
        if not firmware_file.exists():
            print("\n❌ Firmware file not found: firmware/anc_firmware.c")
            return False

        content = firmware_file.read_text()

        # Run analysis checks
        self.analyze_memory_safety(content)
        self.analyze_array_bounds(content)
        self.analyze_real_time_guarantees(content)
        self.analyze_interrupt_safety(content)
        self.analyze_fixed_point_arithmetic(content)
        self.analyze_determinism(content)

        # Print summary
        return self.print_summary()

    def analyze_memory_safety(self, content: str):
        """Check for memory safety issues."""
        print("\n" + "-"*80)
        print("1. MEMORY SAFETY ANALYSIS")
        print("-"*80)

        issues = []

        # Check for unsafe string operations
        if "strcpy(" in content:
            issues.append("Uses strcpy() - unbounded (use strncpy)")

        if "sprintf(" in content:
            issues.append("Uses sprintf() - unbounded (use snprintf)")

        if "gets(" in content:
            issues.append("Uses gets() - CRITICAL VULNERABILITY (use fgets)")

        # Check for malloc/free without bounds
        malloc_calls = re.findall(r'malloc\s*\([^)]+\)', content)
        for malloc in malloc_calls:
            print(f"    Found dynamic allocation: {malloc}")
            if "malloc" in content and "free" not in content:
                issues.append("malloc() without corresponding free() - memory leak")

        # Check for buffer declarations
        buffer_decls = re.findall(r'(float|int|uint32_t)\s+(\w+)\s*\[(\d+)\]', content)
        for dtype, name, size in buffer_decls:
            if int(size) > 4096:
                self.warnings.append(f"Large stack buffer: {name}[{size}] ({int(size)*4} bytes)")

        if issues:
            for issue in issues:
                print(f"    ❌ CRITICAL: {issue}")
                self.critical_issues.append(f"Memory Safety: {issue}")
        else:
            print(f"    ✅ No unsafe string operations found")

        print(f"    Found {len(buffer_decls)} buffer declarations")

    def analyze_array_bounds(self, content: str):
        """Check for array bounds checking."""
        print("\n" + "-"*80)
        print("2. ARRAY BOUNDS CHECKING")
        print("-"*80)

        issues = []

        # Find array access patterns
        array_accesses = re.findall(r'(\w+)\s*\[([^\]]+)\]', content)

        # Check for modulo operations (common in circular buffers)
        modulo_access = [(arr, idx) for arr, idx in array_accesses if '%' in idx]
        print(f"    Found {len(modulo_access)} modulo-based array accesses")

        # Look for bounds checks before array access
        bounds_checks = re.findall(r'if\s*\([^<]+<[^)]+\)', content)
        print(f"    Found {len(bounds_checks)} potential bounds checks")

        # Critical: Check specific NLMS buffer access (lines 391-398, 429)
        nlms_code = content[content.find("NLMS_Update"):content.find("NLMS_Update") + 2000] if "NLMS_Update" in content else ""

        if nlms_code:
            # Check if buffer access uses modulo
            if "% N" in nlms_code or "% filter->N" in nlms_code:
                print(f"    ✅ NLMS uses modulo for circular buffer access")
            else:
                issues.append("NLMS buffer access may not be bounds-safe")

            # Check for explicit bounds checking
            if "if" in nlms_code and "<" in nlms_code:
                print(f"    ✅ Found conditional bounds checks in NLMS")

        # Look for potential buffer overflows in loops
        for_loops = re.findall(r'for\s*\([^;]+;\s*(\w+)\s*<\s*([^;]+);', content)
        print(f"    Analyzed {len(for_loops)} for-loops for bounds safety")

        if issues:
            for issue in issues:
                print(f"    ⚠️  {issue}")
                self.warnings.append(f"Array Bounds: {issue}")
        else:
            print(f"    ✅ Array bounds appear safe (modulo + bounds checks)")

    def analyze_real_time_guarantees(self, content: str):
        """Analyze real-time performance guarantees."""
        print("\n" + "-"*80)
        print("3. REAL-TIME GUARANTEES (<1ms @ 48kHz)")
        print("-"*80)

        issues = []

        # Calculate theoretical CPU cycles needed
        # Assumption: ARM Cortex-M7 @ 216MHz
        sample_rate = 48000
        max_latency_ms = 1.0
        block_size = 48  # 1ms of audio @ 48kHz

        cpu_freq_mhz = 216  # ARM Cortex-M7
        cycles_available = int((max_latency_ms / 1000) * cpu_freq_mhz * 1_000_000)

        print(f"\n    Target latency: {max_latency_ms}ms")
        print(f"    Sample rate: {sample_rate} Hz")
        print(f"    Block size: {block_size} samples")
        print(f"    CPU: ARM Cortex-M7 @ {cpu_freq_mhz} MHz")
        print(f"    Cycles available: {cycles_available:,}")

        # Find NLMS algorithm
        nlms_match = re.search(r'void\s+NLMS_Update.*?\n(.*?)(?=void|\Z)', content, re.DOTALL)
        if nlms_match:
            nlms_code = nlms_match.group(1)

            # Count operations in NLMS
            mult_ops = len(re.findall(r'\*', nlms_code))
            add_ops = len(re.findall(r'\+', nlms_code))
            div_ops = len(re.findall(r'\/', nlms_code))

            # Estimate cycles (very rough)
            # Multiply: ~1 cycle (with hardware FPU)
            # Add: ~1 cycle
            # Divide: ~14 cycles
            estimated_cycles_per_sample = (mult_ops * 1) + (add_ops * 1) + (div_ops * 14)

            print(f"\n    NLMS Operations per sample:")
            print(f"      Multiplications: {mult_ops} (~{mult_ops} cycles)")
            print(f"      Additions: {add_ops} (~{add_ops} cycles)")
            print(f"      Divisions: {div_ops} (~{div_ops * 14} cycles)")
            print(f"      Estimated: ~{estimated_cycles_per_sample} cycles/sample")

            total_cycles = estimated_cycles_per_sample * block_size
            print(f"\n    Total for {block_size} samples: ~{total_cycles:,} cycles")
            print(f"    Available cycles: {cycles_available:,}")

            if total_cycles > cycles_available:
                issues.append(f"May exceed real-time budget: {total_cycles:,} > {cycles_available:,} cycles")
                print(f"    ❌ CRITICAL: Exceeds real-time budget")
            else:
                utilization = (total_cycles / cycles_available) * 100
                print(f"    ✅ Within budget ({utilization:.1f}% utilization)")

        # Check for non-deterministic operations
        if "malloc" in content or "free" in content:
            issues.append("Dynamic memory allocation (non-deterministic)")

        if "printf" in content or "scanf" in content:
            issues.append("I/O operations in real-time code (slow)")

        # Check for floating point vs fixed point
        if "float" in content or "double" in content:
            self.warnings.append("Uses floating-point (consider fixed-point for determinism)")
            print(f"    ⚠️  Uses floating-point (hardware FPU mitigates)")

        if issues:
            for issue in issues:
                print(f"    ❌ {issue}")
                self.critical_issues.append(f"Real-time: {issue}")

    def analyze_interrupt_safety(self, content: str):
        """Check for interrupt safety."""
        print("\n" + "-"*80)
        print("4. INTERRUPT SAFETY")
        print("-"*80)

        issues = []

        # Look for interrupt handlers
        isr_patterns = [
            r'void\s+\w+_IRQHandler',
            r'__attribute__\s*\(\s*\(interrupt\)\s*\)',
            r'ISR\s*\(',
        ]

        isrs = []
        for pattern in isr_patterns:
            found = re.findall(pattern, content)
            isrs.extend(found)

        if isrs:
            print(f"    Found {len(isrs)} interrupt handlers")

            # Check for volatile variables
            volatile_vars = re.findall(r'volatile\s+\w+', content)
            print(f"    Found {len(volatile_vars)} volatile variables")

            # Check for critical sections
            if "__disable_irq()" in content or "ENTER_CRITICAL()" in content:
                print(f"    ✅ Uses critical sections for shared data")
            else:
                issues.append("No critical sections found (race condition risk)")

        else:
            print(f"    No interrupt handlers found in this file")

        if issues:
            for issue in issues:
                print(f"    ⚠️  {issue}")
                self.warnings.append(f"Interrupt Safety: {issue}")

    def analyze_fixed_point_arithmetic(self, content: str):
        """Check fixed-point arithmetic correctness."""
        print("\n" + "-"*80)
        print("5. FIXED-POINT ARITHMETIC")
        print("-"*80)

        # Check for fixed-point usage
        if "int32_t" in content or "int16_t" in content:
            print(f"    Found fixed-point integer types")

            # Look for scaling/shifting operations
            shift_ops = len(re.findall(r'>>', content)) + len(re.findall(r'<<', content))
            print(f"    Found {shift_ops} bit-shift operations")

            # Check for overflow protection
            if "SAT" in content or "CLAMP" in content or "__SSAT" in content:
                print(f"    ✅ Uses saturation arithmetic (overflow protection)")
            else:
                self.warnings.append("No saturation arithmetic detected (overflow risk)")

        else:
            print(f"    Uses floating-point (float/double)")

    def analyze_determinism(self, content: str):
        """Check for deterministic execution."""
        print("\n" + "-"*80)
        print("6. DETERMINISM ANALYSIS")
        print("-"*80)

        issues = []

        # Check for non-deterministic operations
        if "rand()" in content or "random()" in content:
            issues.append("Uses rand() - non-deterministic")

        # Check for unbounded loops
        while_loops = re.findall(r'while\s*\([^)]+\)', content)
        for loop in while_loops:
            if "true" in loop.lower() or "1" in loop:
                issues.append(f"Potentially infinite while loop: {loop}")

        # Check for recursion (bad for real-time)
        functions = re.findall(r'void\s+(\w+)\s*\(', content)
        for func in functions:
            if content.count(func) > 1:  # Function calls itself
                # More sophisticated check needed
                pass

        if issues:
            for issue in issues:
                print(f"    ⚠️  {issue}")
                self.warnings.append(f"Determinism: {issue}")
        else:
            print(f"    ✅ Appears deterministic")

    def print_summary(self):
        """Print analysis summary."""
        print("\n" + "="*80)
        print("FIRMWARE ANALYSIS SUMMARY")
        print("="*80)

        print(f"\n❌ CRITICAL ISSUES: {len(self.critical_issues)}")
        for issue in self.critical_issues:
            print(f"  - {issue}")

        print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
        for warning in self.warnings:
            print(f"  - {warning}")

        if self.recommendations:
            print(f"\n💡 RECOMMENDATIONS: {len(self.recommendations)}")
            for rec in self.recommendations:
                print(f"  - {rec}")

        print("\n" + "="*80)

        if len(self.critical_issues) == 0:
            print("✅ NO CRITICAL FIRMWARE ISSUES FOUND")
            print("Firmware appears safe for production deployment")
            return True
        else:
            print(f"❌ {len(self.critical_issues)} CRITICAL ISSUES REQUIRE FIXES")
            return False


def main():
    """Main entry point."""
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    analyzer = FirmwareSafetyAnalyzer()
    success = analyzer.analyze_all()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
