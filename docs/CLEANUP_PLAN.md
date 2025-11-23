# Repository Cleanup Plan

**Current Status:** 107 files in root directory - MESSY!
**Target:** Clean, organized professional structure

## Problems Identified

1. **107 files in root directory** - way too many!
2. **27 markdown documentation files** scattered in root
3. **60+ Python files** mixed together (production + tests + demos)
4. **Duplicate documentation** (multiple READMEs, guides)
5. **Test/demo files** mixed with production code
6. **No clear separation** between core code, tests, docs, tools

## Target Structure

```
anc-with-ai/
├── README.md                    # Main project README
├── LICENSE
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── wsgi.py
│
├── docs/                        # ALL documentation
│   ├── README.md               # Documentation index
│   ├── architecture/           # Architecture docs
│   │   ├── PLATFORM_ARCHITECTURE.md
│   │   └── DATABASE_SCHEMA.md
│   ├── guides/                 # User guides
│   │   ├── QUICK_START_GUIDE.md
│   │   ├── LOCAL_EXECUTION_GUIDE.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   └── WEB_APP_GUIDE.md
│   ├── deployment/             # Deployment docs
│   │   └── PRODUCTION_DEPLOYMENT.md
│   └── verification/           # Verification/test docs
│       ├── ANTI_NOISE_VERIFICATION.md
│       ├── EMERGENCY_DETECTION_VERIFICATION.md
│       └── [other verification docs]
│
├── src/                        # ALL production source code
│   ├── __init__.py
│   ├── core/                   # Core ANC algorithms
│   │   ├── __init__.py
│   │   ├── advanced_anc_algorithms.py
│   │   ├── anti_noise_generator.py
│   │   ├── audio_processor.py
│   │   └── realtime_audio_engine.py
│   ├── api/                    # API servers
│   │   ├── __init__.py
│   │   ├── server.py           # Main Flask server
│   │   ├── api_server.py       # REST API
│   │   ├── websocket_server.py # WebSocket server
│   │   └── tasks.py            # Celery tasks
│   ├── ml/                     # Machine learning
│   │   ├── __init__.py
│   │   ├── feature_extraction.py
│   │   ├── noise_classifier_model.py
│   │   ├── emergency_noise_detector.py
│   │   └── frequent_noise_manager.py
│   ├── database/               # Database models
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── schema.py          # database_schema.py renamed
│   ├── web/                    # Web app
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── main.py
│   └── utils/                  # Utilities
│       ├── __init__.py
│       └── audio_capture.py
│
├── tests/                      # ALL test files
│   ├── __init__.py
│   ├── unit/                   # Unit tests
│   │   ├── test_audio_system.py
│   │   ├── test_noise_classifier.py
│   │   └── test_emergency_detection.py
│   ├── integration/            # Integration tests
│   │   ├── verify_integration.py
│   │   ├── verify_flask_app.py
│   │   └── verify_classifier_pipeline.py
│   └── demos/                  # Demo/verification scripts
│       ├── capture_demo.py
│       ├── playback_cancellation_demo.py
│       ├── simple_anti_noise_demo.py
│       ├── phase_inversion_test.py
│       └── [other demo files]
│
├── scripts/                    # Utility scripts
│   ├── training/               # ML training scripts
│   │   ├── train_classifier.py
│   │   ├── train_sklearn_demo.py
│   │   ├── collect_training_data.py
│   │   └── generate_synthetic_data.py
│   ├── database/               # Database scripts
│   │   ├── inspect_database.py
│   │   ├── list_tables.py
│   │   ├── query_latest_recording.py
│   │   └── query_sample_data.py
│   ├── diagnostics/            # Diagnostic scripts
│   │   ├── diagnostic_check.py
│   │   ├── check_audio_devices.py
│   │   └── setup_and_verify.py
│   └── analysis/               # Analysis scripts
│       ├── intensity_analysis.py
│       └── librosa_intensity_analysis.py
│
├── tools/                      # Hardware tools (keep as is)
│   ├── calibration_tool.py
│   ├── firmware_flasher.py
│   └── manufacturing_test.py
│
├── benchmarks/                 # Performance benchmarks (keep structure)
│   ├── README.md
│   ├── BENCHMARK_SUMMARY.md
│   ├── VALIDATED_PERFORMANCE_RESULTS.md
│   ├── nlms/
│   └── network/
│
├── cloud/                      # Cloud infrastructure (keep structure)
│   ├── README.md
│   ├── ARCHITECTURE_REFINEMENTS.md
│   ├── AWS_ARCHITECTURE.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── PERFORMANCE_BENCHMARKS.md
│   ├── terraform/
│   ├── lambda/
│   ├── lambda_edge/
│   └── webrtc/
│
├── config/                     # Configuration files
│   ├── __init__.py
│   ├── config.py              # Base config (move from root)
│   └── production.py
│
├── data/                       # Data files (already exists)
├── models/                     # ML model files (already exists)
├── static/                     # Static web assets (already exists)
├── templates/                  # HTML templates (already exists)
└── monitoring/                 # Monitoring configs (already exists)
```

## Migration Steps

1. ✅ Create new directory structure
2. ✅ Move documentation files to `docs/`
3. ✅ Move production code to `src/`
4. ✅ Move test/demo files to `tests/`
5. ✅ Move utility scripts to `scripts/`
6. ✅ Keep config files organized
7. ✅ Update imports in Python files
8. ✅ Create new clean README
9. ✅ Test that everything still works
10. ✅ Commit cleanup

## Files to Keep in Root

- README.md (main)
- LICENSE
- requirements.txt
- Dockerfile
- docker-compose.yml
- nginx.conf
- .env.example
- .gitignore
- wsgi.py
- openapi.yaml

**Total in root after cleanup: ~12 files** (vs 107 currently!)
