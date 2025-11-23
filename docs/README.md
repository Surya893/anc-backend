# ANC Platform Documentation

Complete documentation for the Active Noise Cancellation (ANC) Platform.

## Quick Links

- [Main README](../README.md) - Project overview and quick start
- [CHANGELOG](../CHANGELOG.md) - Version history and changes

## Architecture Documentation

Detailed technical architecture and system design:

- [Platform Architecture](architecture/PLATFORM_ARCHITECTURE.md) - Complete system architecture overview
- [Database Schema](architecture/DATABASE_SCHEMA.md) - Database design and schema

## User Guides

Step-by-step guides for users and developers:

- [Quick Start Guide](guides/QUICK_START_GUIDE.md) - Get started quickly
- [Local Execution Guide](guides/LOCAL_EXECUTION_GUIDE.md) - Run locally for development
- [Deployment Guide](guides/DEPLOYMENT_GUIDE.md) - Deploy to production
- [Web App Guide](guides/WEB_APP_GUIDE.md) - Web application usage
- [Playback Testing Guide](guides/PLAYBACK_TESTING_GUIDE.md) - Test audio playback
- [Realtime Anti-Noise Guide](guides/REALTIME_ANTI_NOISE_GUIDE.md) - Real-time processing guide
- [Full Integration Guide](guides/FULL_INTEGRATION_GUIDE.md) - Complete integration walkthrough
- [Local Playback Instructions](guides/LOCAL_PLAYBACK_INSTRUCTIONS.md) - Local playback setup
- [Local Testing README](guides/README_LOCAL_TESTING.md) - Local testing procedures

## Deployment Documentation

Production deployment guides:

- [Production Deployment](deployment/PRODUCTION_DEPLOYMENT.md) - Production deployment procedures
- [Hardware/Software Integration](deployment/HARDWARE_SOFTWARE_INTEGRATION.md) - Hardware integration guide

## Verification & Testing

Verification procedures and test documentation:

- [Anti-Noise Verification](verification/ANTI_NOISE_VERIFICATION.md) - Verify anti-noise generation
- [Emergency Detection Verification](verification/EMERGENCY_DETECTION_VERIFICATION.md) - Verify emergency detection
- [Intensity Verification](verification/INTENSITY_VERIFICATION.md) - Audio intensity verification
- [Librosa Intensity Verification](verification/LIBROSA_INTENSITY_VERIFICATION.md) - Librosa-based verification
- [NumPy Counter Wave Verification](verification/NUMPY_COUNTER_WAVE_VERIFICATION.md) - Counter-wave verification
- [Phase Inversion Verification](verification/PHASE_INVERSION_VERIFICATION.md) - Phase inversion testing

## Component Documentation

Documentation for specific components:

- [Audio Capture README](AUDIO_CAPTURE_README.md) - Audio capture system
- [Backend README](BACKEND_README.md) - Backend services
- [Noise Classifier README](NOISE_CLASSIFIER_README.md) - ML classifier documentation
- [Training Results](TRAINING_RESULTS.md) - ML training results and metrics

## Project Documentation

Project management and meta-documentation:

- [Execution Summary](EXECUTION_SUMMARY.md) - Project execution summary
- [Integration Summary](INTEGRATION_SUMMARY.md) - Integration summary
- [Repository Cleanup Summary](REPOSITORY_CLEANUP_SUMMARY.md) - Repository organization
- [Cleanup Plan](CLEANUP_PLAN.md) - Detailed cleanup planning
- [Final Report](final_report.md) - Project final report
- [Platform Summary](PLATFORM_SUMMARY.txt) - Platform overview (text format)
- [Quick Start Playback](QUICK_START_PLAYBACK.txt) - Quick playback guide (text format)

## Cloud & Infrastructure

Cloud architecture and infrastructure documentation (separate section):

- [Cloud Documentation](../cloud/README.md) - Cloud infrastructure overview
- [AWS Architecture](../cloud/AWS_ARCHITECTURE.md) - AWS infrastructure design
- [Architecture Refinements](../cloud/ARCHITECTURE_REFINEMENTS.md) - Cloud architecture improvements
- [Performance Benchmarks](../cloud/PERFORMANCE_BENCHMARKS.md) - Performance projections and testing

## Benchmarks

Performance benchmarking documentation (separate section):

- [Benchmark Documentation](../benchmarks/README.md) - Benchmark overview
- [Benchmark Summary](../benchmarks/BENCHMARK_SUMMARY.md) - Executive summary
- [Validated Performance Results](../benchmarks/VALIDATED_PERFORMANCE_RESULTS.md) - Real measured results

## Hardware Tools

Hardware-specific documentation (separate section):

- [Tools Documentation](../tools/README.md) - Hardware tools overview

---

## Documentation Organization

```
docs/
├── README.md                           # This file (documentation index)
├── architecture/                       # System architecture
│   ├── PLATFORM_ARCHITECTURE.md
│   └── DATABASE_SCHEMA.md
├── guides/                             # User and developer guides
│   ├── QUICK_START_GUIDE.md
│   ├── LOCAL_EXECUTION_GUIDE.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── WEB_APP_GUIDE.md
│   └── [other guides...]
├── deployment/                         # Production deployment
│   ├── PRODUCTION_DEPLOYMENT.md
│   └── HARDWARE_SOFTWARE_INTEGRATION.md
└── verification/                       # Testing and verification
    ├── ANTI_NOISE_VERIFICATION.md
    ├── EMERGENCY_DETECTION_VERIFICATION.md
    └── [other verification docs...]
```

## External Documentation

- [GitHub Repository](https://github.com/Surya893/anc-with-ai)
- API Documentation: See [OpenAPI Spec](../openapi.yaml)

---

**Last Updated:** 2025-11-16
**Maintained by:** ANC Platform Team
