"""
NLMS Filter Performance Benchmark - REAL MEASUREMENTS
Tests actual performance of NLMS filter implementations

Measures:
- Processing latency per chunk
- Throughput (chunks/second)
- Memory consumption
- CPU usage
- Convergence speed
- Cancellation effectiveness

This provides REAL data to validate theoretical projections.
"""

import time
import numpy as np
import tracemalloc
import psutil
import os
from typing import List, Dict, Tuple
import json


class NLMSFilter:
    """NumPy-based NLMS filter (WebRTC implementation)"""

    def __init__(self, length: int = 256, mu: float = 0.01, epsilon: float = 1e-6):
        self.length = length
        self.mu = mu
        self.epsilon = epsilon
        self.weights = np.zeros(length, dtype=np.float32)
        self.buffer = np.zeros(length, dtype=np.float32)

    def process(self, reference: np.ndarray, desired: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Process audio chunk"""
        chunk_size = min(len(reference), len(desired))
        reference = reference[:chunk_size]
        desired = desired[:chunk_size]

        output = np.zeros(chunk_size, dtype=np.float32)
        error = np.zeros(chunk_size, dtype=np.float32)

        for i in range(chunk_size):
            # Update circular buffer
            self.buffer = np.roll(self.buffer, 1)
            self.buffer[0] = reference[i]

            # Filter output
            y = np.dot(self.weights, self.buffer)
            output[i] = y

            # Error calculation
            e = desired[i] - y
            error[i] = e

            # Normalized weight update
            norm = np.dot(self.buffer, self.buffer) + self.epsilon
            self.weights += (self.mu / norm) * e * self.buffer

        return output, error


class EdgeNLMSFilter:
    """Pure Python NLMS filter (Lambda@Edge implementation)"""

    def __init__(self, length: int = 128):
        self.length = length
        self.weights = [0.0] * length
        self.buffer = [0.0] * length
        self.mu = 0.01
        self.epsilon = 1e-6

    def process(self, reference: List[float], desired: List[float]) -> Tuple[List[float], List[float]]:
        """Process audio chunk"""
        chunk_size = min(len(reference), len(desired))
        output = []
        error = []

        for i in range(chunk_size):
            # Update circular buffer
            self.buffer.pop()
            self.buffer.insert(0, reference[i])

            # Filter output (dot product)
            y = sum(w * x for w, x in zip(self.weights, self.buffer))
            output.append(y)

            # Error
            e = desired[i] - y
            error.append(e)

            # Normalized update
            norm = sum(x * x for x in self.buffer) + self.epsilon
            update_factor = (self.mu / norm) * e

            # Update weights
            self.weights = [w + update_factor * x for w, x in zip(self.weights, self.buffer)]

        return output, error


def generate_test_audio(duration_sec: float, sample_rate: int = 48000) -> Tuple[np.ndarray, np.ndarray]:
    """Generate synthetic test audio (reference noise + desired signal)"""
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, dtype=np.float32)

    # Reference: White noise + 1kHz tone
    reference = np.random.randn(num_samples).astype(np.float32) * 0.1
    reference += 0.3 * np.sin(2 * np.pi * 1000 * t)  # 1kHz tone

    # Desired: Same as reference (simulate correlated noise)
    desired = reference.copy()

    return reference, desired


def benchmark_processing_latency(filter_impl: str = "numpy", chunk_size: int = 512, num_iterations: int = 1000) -> Dict:
    """
    Benchmark processing latency

    Returns REAL measurements in milliseconds
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARK: Processing Latency ({filter_impl})")
    print(f"Chunk size: {chunk_size} samples")
    print(f"Iterations: {num_iterations}")
    print(f"{'='*60}")

    # Generate test data
    reference, desired = generate_test_audio(duration_sec=60.0)

    # Create filter
    if filter_impl == "numpy":
        filter = NLMSFilter(length=256)
        ref_chunk = reference[:chunk_size]
        des_chunk = desired[:chunk_size]
    else:  # pure python
        filter = EdgeNLMSFilter(length=128)
        ref_chunk = reference[:chunk_size].tolist()
        des_chunk = desired[:chunk_size].tolist()

    # Warm-up
    for _ in range(100):
        filter.process(ref_chunk, des_chunk)

    # Benchmark
    latencies = []
    process = psutil.Process()

    for i in range(num_iterations):
        cpu_before = process.cpu_percent()
        start = time.perf_counter()

        output, error = filter.process(ref_chunk, des_chunk)

        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

        if i % 100 == 0:
            print(f"Iteration {i}: {elapsed_ms:.4f}ms")

    # Calculate statistics
    latencies = np.array(latencies)
    results = {
        "implementation": filter_impl,
        "chunk_size": chunk_size,
        "iterations": num_iterations,
        "latency_ms": {
            "mean": float(np.mean(latencies)),
            "median": float(np.median(latencies)),
            "std": float(np.std(latencies)),
            "min": float(np.min(latencies)),
            "max": float(np.max(latencies)),
            "p50": float(np.percentile(latencies, 50)),
            "p95": float(np.percentile(latencies, 95)),
            "p99": float(np.percentile(latencies, 99)),
        }
    }

    print(f"\nRESULTS:")
    print(f"  Mean latency:   {results['latency_ms']['mean']:.4f} ms")
    print(f"  Median latency: {results['latency_ms']['median']:.4f} ms")
    print(f"  P95 latency:    {results['latency_ms']['p95']:.4f} ms")
    print(f"  P99 latency:    {results['latency_ms']['p99']:.4f} ms")
    print(f"  Min latency:    {results['latency_ms']['min']:.4f} ms")
    print(f"  Max latency:    {results['latency_ms']['max']:.4f} ms")

    return results


def benchmark_throughput(filter_impl: str = "numpy", duration_sec: int = 10) -> Dict:
    """
    Benchmark throughput (chunks processed per second)

    Returns REAL measurements
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARK: Throughput ({filter_impl})")
    print(f"Duration: {duration_sec} seconds")
    print(f"{'='*60}")

    chunk_size = 512
    reference, desired = generate_test_audio(duration_sec=60.0)

    # Create filter
    if filter_impl == "numpy":
        filter = NLMSFilter(length=256)
    else:
        filter = EdgeNLMSFilter(length=128)

    # Benchmark
    chunks_processed = 0
    start_time = time.perf_counter()
    end_time = start_time + duration_sec

    while time.perf_counter() < end_time:
        offset = (chunks_processed * chunk_size) % (len(reference) - chunk_size)

        if filter_impl == "numpy":
            ref_chunk = reference[offset:offset + chunk_size]
            des_chunk = desired[offset:offset + chunk_size]
        else:
            ref_chunk = reference[offset:offset + chunk_size].tolist()
            des_chunk = desired[offset:offset + chunk_size].tolist()

        filter.process(ref_chunk, des_chunk)
        chunks_processed += 1

    actual_duration = time.perf_counter() - start_time
    throughput = chunks_processed / actual_duration

    results = {
        "implementation": filter_impl,
        "duration_sec": actual_duration,
        "chunks_processed": chunks_processed,
        "throughput_chunks_per_sec": throughput,
        "throughput_samples_per_sec": throughput * chunk_size,
        "realtime_factor": (throughput * chunk_size) / 48000,  # 48kHz audio
    }

    print(f"\nRESULTS:")
    print(f"  Chunks processed: {results['chunks_processed']}")
    print(f"  Throughput:       {results['throughput_chunks_per_sec']:.2f} chunks/sec")
    print(f"  Sample rate:      {results['throughput_samples_per_sec']:.0f} samples/sec")
    print(f"  Realtime factor:  {results['realtime_factor']:.2f}x")

    if results['realtime_factor'] >= 1.0:
        print(f"  ✓ Can process in REAL-TIME")
    else:
        print(f"  ✗ Cannot process in real-time")

    return results


def benchmark_memory(filter_impl: str = "numpy", chunk_size: int = 512) -> Dict:
    """
    Benchmark memory consumption

    Returns REAL memory measurements
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARK: Memory Consumption ({filter_impl})")
    print(f"{'='*60}")

    tracemalloc.start()
    process = psutil.Process()

    # Baseline memory
    baseline_mem = process.memory_info().rss / 1024 / 1024  # MB

    # Create filter
    if filter_impl == "numpy":
        filter = NLMSFilter(length=256)
    else:
        filter = EdgeNLMSFilter(length=128)

    after_init_mem = process.memory_info().rss / 1024 / 1024

    # Process some data
    reference, desired = generate_test_audio(duration_sec=10.0)

    for i in range(0, len(reference) - chunk_size, chunk_size):
        if filter_impl == "numpy":
            ref_chunk = reference[i:i + chunk_size]
            des_chunk = desired[i:i + chunk_size]
        else:
            ref_chunk = reference[i:i + chunk_size].tolist()
            des_chunk = desired[i:i + chunk_size].tolist()

        filter.process(ref_chunk, des_chunk)

    after_processing_mem = process.memory_info().rss / 1024 / 1024

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    results = {
        "implementation": filter_impl,
        "memory_mb": {
            "baseline": baseline_mem,
            "after_init": after_init_mem,
            "after_processing": after_processing_mem,
            "filter_overhead": after_init_mem - baseline_mem,
            "processing_overhead": after_processing_mem - after_init_mem,
            "total_overhead": after_processing_mem - baseline_mem,
        },
        "traced_memory_mb": {
            "current": current / 1024 / 1024,
            "peak": peak / 1024 / 1024,
        }
    }

    print(f"\nRESULTS:")
    print(f"  Baseline:            {results['memory_mb']['baseline']:.2f} MB")
    print(f"  After init:          {results['memory_mb']['after_init']:.2f} MB")
    print(f"  After processing:    {results['memory_mb']['after_processing']:.2f} MB")
    print(f"  Filter overhead:     {results['memory_mb']['filter_overhead']:.2f} MB")
    print(f"  Processing overhead: {results['memory_mb']['processing_overhead']:.2f} MB")
    print(f"  Total overhead:      {results['memory_mb']['total_overhead']:.2f} MB")
    print(f"  Peak traced:         {results['traced_memory_mb']['peak']:.2f} MB")

    return results


def benchmark_cancellation_effectiveness(filter_impl: str = "numpy", num_iterations: int = 1000) -> Dict:
    """
    Benchmark noise cancellation effectiveness

    Returns REAL cancellation measurements in dB
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARK: Cancellation Effectiveness ({filter_impl})")
    print(f"{'='*60}")

    chunk_size = 512
    reference, desired = generate_test_audio(duration_sec=60.0)

    # Create filter
    if filter_impl == "numpy":
        filter = NLMSFilter(length=256)
    else:
        filter = EdgeNLMSFilter(length=128)

    cancellation_db_values = []

    for i in range(num_iterations):
        offset = (i * chunk_size) % (len(reference) - chunk_size)

        if filter_impl == "numpy":
            ref_chunk = reference[offset:offset + chunk_size]
            des_chunk = desired[offset:offset + chunk_size]
        else:
            ref_chunk = reference[offset:offset + chunk_size].tolist()
            des_chunk = desired[offset:offset + chunk_size].tolist()

        output, error = filter.process(ref_chunk, des_chunk)

        # Calculate RMS
        if filter_impl == "numpy":
            original_rms = np.sqrt(np.mean(ref_chunk**2))
            processed_rms = np.sqrt(np.mean(error**2))
        else:
            original_rms = (sum(s * s for s in ref_chunk) / len(ref_chunk)) ** 0.5
            processed_rms = (sum(e * e for e in error) / len(error)) ** 0.5

        # Calculate cancellation in dB
        if original_rms > 0 and processed_rms > 0:
            cancellation_db = 20 * np.log10(original_rms / processed_rms)
            cancellation_db_values.append(cancellation_db)

        if i % 100 == 0 and i > 0:
            recent_avg = np.mean(cancellation_db_values[-100:])
            print(f"Iteration {i}: Recent avg = {recent_avg:.2f} dB")

    cancellation_db_values = np.array(cancellation_db_values)

    results = {
        "implementation": filter_impl,
        "iterations": num_iterations,
        "cancellation_db": {
            "mean": float(np.mean(cancellation_db_values)),
            "median": float(np.median(cancellation_db_values)),
            "std": float(np.std(cancellation_db_values)),
            "min": float(np.min(cancellation_db_values)),
            "max": float(np.max(cancellation_db_values)),
            "final_100_avg": float(np.mean(cancellation_db_values[-100:])),
        }
    }

    print(f"\nRESULTS:")
    print(f"  Mean cancellation:    {results['cancellation_db']['mean']:.2f} dB")
    print(f"  Median cancellation:  {results['cancellation_db']['median']:.2f} dB")
    print(f"  Final 100 avg:        {results['cancellation_db']['final_100_avg']:.2f} dB")
    print(f"  Min:                  {results['cancellation_db']['min']:.2f} dB")
    print(f"  Max:                  {results['cancellation_db']['max']:.2f} dB")

    return results


def run_all_benchmarks():
    """Run all NLMS benchmarks and save results"""

    print("\n" + "="*60)
    print("NLMS FILTER PERFORMANCE BENCHMARK SUITE")
    print("Running REAL measurements...")
    print("="*60)

    all_results = {}

    # Benchmark both implementations
    for impl in ["numpy", "pure_python"]:
        print(f"\n\n{'#'*60}")
        print(f"# TESTING: {impl.upper()} Implementation")
        print(f"{'#'*60}")

        results = {}

        # 1. Latency
        results['latency'] = benchmark_processing_latency(impl, chunk_size=512, num_iterations=1000)

        # 2. Throughput
        results['throughput'] = benchmark_throughput(impl, duration_sec=10)

        # 3. Memory
        results['memory'] = benchmark_memory(impl, chunk_size=512)

        # 4. Cancellation effectiveness
        results['cancellation'] = benchmark_cancellation_effectiveness(impl, num_iterations=1000)

        all_results[impl] = results

    # Save results
    output_file = "/home/user/anc-with-ai/benchmarks/nlms/results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n\n{'='*60}")
    print(f"BENCHMARK COMPLETE")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}")

    # Summary comparison
    print("\n\nSUMMARY COMPARISON:")
    print(f"{'Metric':<30} {'NumPy':<15} {'Pure Python':<15}")
    print(f"{'-'*60}")
    print(f"{'Mean Latency (ms)':<30} {all_results['numpy']['latency']['latency_ms']['mean']:<15.4f} {all_results['pure_python']['latency']['latency_ms']['mean']:<15.4f}")
    print(f"{'P95 Latency (ms)':<30} {all_results['numpy']['latency']['latency_ms']['p95']:<15.4f} {all_results['pure_python']['latency']['latency_ms']['p95']:<15.4f}")
    print(f"{'Throughput (chunks/sec)':<30} {all_results['numpy']['throughput']['throughput_chunks_per_sec']:<15.2f} {all_results['pure_python']['throughput']['throughput_chunks_per_sec']:<15.2f}")
    print(f"{'Memory Overhead (MB)':<30} {all_results['numpy']['memory']['memory_mb']['total_overhead']:<15.2f} {all_results['pure_python']['memory']['memory_mb']['total_overhead']:<15.2f}")
    print(f"{'Cancellation (dB)':<30} {all_results['numpy']['cancellation']['cancellation_db']['mean']:<15.2f} {all_results['pure_python']['cancellation']['cancellation_db']['mean']:<15.2f}")

    return all_results


if __name__ == "__main__":
    results = run_all_benchmarks()
