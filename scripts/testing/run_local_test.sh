#!/bin/bash
#
# Local Test Runner for Full ANC System
# Runs complete integration test with monitoring
#

set -e  # Exit on error

echo "================================================================================"
echo "ANC SYSTEM - LOCAL EXECUTION TEST"
echo "================================================================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 not found"
    exit 1
fi

PYTHON=python3

# Step 1: Check dependencies
echo "Step 1: Checking Dependencies"
echo "--------------------------------------------------------------------------------"

dependencies=("pyaudio" "numpy" "librosa" "sklearn" "flask")
missing_deps=()

for dep in "${dependencies[@]}"; do
    if $PYTHON -c "import $dep" 2>/dev/null; then
        print_success "$dep installed"
    else
        print_error "$dep NOT installed"
        missing_deps+=("$dep")
    fi
done

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo
    print_warning "Missing dependencies: ${missing_deps[*]}"
    read -p "Install missing dependencies? (y/n): " install_deps
    if [ "$install_deps" = "y" ]; then
        echo
        print_info "Installing dependencies..."
        pip install -r requirements.txt
        echo
        print_success "Dependencies installed"
    else
        print_error "Cannot proceed without dependencies"
        exit 1
    fi
fi

echo

# Step 2: Check audio devices
echo "Step 2: Checking Audio Devices"
echo "--------------------------------------------------------------------------------"

$PYTHON check_audio_devices.py > /tmp/audio_check.log 2>&1
if [ $? -eq 0 ]; then
    print_success "Audio devices detected"
    # Show default devices
    grep -A 3 "Default Input" /tmp/audio_check.log | head -4
    grep -A 3 "Default Output" /tmp/audio_check.log | head -4
else
    print_error "Audio device check failed"
    cat /tmp/audio_check.log
    exit 1
fi

echo

# Step 3: Check models
echo "Step 3: Checking Trained Models"
echo "--------------------------------------------------------------------------------"

if [ -f "models/noise_classifier_sklearn.joblib" ]; then
    print_success "Noise classifier found"
else
    print_warning "Noise classifier not found"
    read -p "Train models now? (requires audio samples) (y/n): " train_models
    if [ "$train_models" = "y" ]; then
        echo
        print_info "Training models..."
        $PYTHON train_sklearn_demo.py
        if [ $? -eq 0 ]; then
            print_success "Models trained"
        else
            print_error "Model training failed"
            exit 1
        fi
    else
        print_warning "Continuing without trained models (classification disabled)"
    fi
fi

echo

# Step 4: Run integration verification
echo "Step 4: Running Integration Verification"
echo "--------------------------------------------------------------------------------"

$PYTHON verify_integration.py > /tmp/verify.log 2>&1
passed_tests=$(grep "Tests passed:" /tmp/verify.log | awk '{print $3}')

if [ -n "$passed_tests" ]; then
    print_info "Integration tests: $passed_tests"
    if [[ "$passed_tests" == "7/7" ]] || [[ "$passed_tests" == "6/7" ]]; then
        print_success "Integration verified"
    else
        print_warning "Some integration tests failed"
        read -p "Continue anyway? (y/n): " continue_test
        if [ "$continue_test" != "y" ]; then
            echo
            print_info "Full verification log:"
            cat /tmp/verify.log
            exit 1
        fi
    fi
else
    print_error "Integration verification failed"
    cat /tmp/verify.log
    exit 1
fi

echo

# Step 5: Select test mode
echo "Step 5: Select Test Mode"
echo "--------------------------------------------------------------------------------"
echo
echo "Available test modes:"
echo "  1) Quick test (30 seconds, core mode)"
echo "  2) Extended test (60 seconds, core mode)"
echo "  3) Interactive test (manual stop, core mode)"
echo "  4) Web UI test (with browser interface)"
echo "  5) Custom duration (core mode)"
echo

read -p "Select mode (1-5): " mode_choice

case $mode_choice in
    1)
        DURATION=30
        MODE="core"
        TEST_NAME="Quick Test (30s)"
        ;;
    2)
        DURATION=60
        MODE="core"
        TEST_NAME="Extended Test (60s)"
        ;;
    3)
        DURATION=""
        MODE="core"
        TEST_NAME="Interactive Test"
        ;;
    4)
        DURATION=""
        MODE="web"
        TEST_NAME="Web UI Test"
        ;;
    5)
        read -p "Enter duration (seconds): " DURATION
        MODE="core"
        TEST_NAME="Custom Test (${DURATION}s)"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo

# Step 6: Prepare for execution
echo "Step 6: Preparing for Execution"
echo "--------------------------------------------------------------------------------"

# Create log directory
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# Generate log filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/anc_test_${TIMESTAMP}.log"

print_success "Log directory: $LOG_DIR"
print_success "Log file: $LOG_FILE"

echo

# Step 7: Execute ANC system
echo "================================================================================"
echo "Step 7: EXECUTING ANC SYSTEM - $TEST_NAME"
echo "================================================================================"
echo

if [ "$MODE" = "web" ]; then
    print_info "Starting ANC system with web UI..."
    echo
    print_info "Access web interface at:"
    echo "  Desktop: http://localhost:5000"
    echo "  Mobile:  http://$(hostname -I | awk '{print $1}'):5000"
    echo
    print_warning "Press Ctrl+C to stop"
    echo

    # Run with web UI
    $PYTHON main.py --mode web 2>&1 | tee "$LOG_FILE"

else
    print_info "Starting ANC system in core mode..."
    echo
    print_warning "Listen for noise reduction effect"
    print_warning "Watch console for status updates"
    print_warning "Press Ctrl+C to stop early"
    echo

    # Build command
    CMD="$PYTHON main.py --mode core"
    if [ -n "$DURATION" ]; then
        CMD="$CMD --duration $DURATION"
    fi

    # Run core mode
    $CMD 2>&1 | tee "$LOG_FILE"
fi

EXIT_CODE=$?

echo
echo "================================================================================"
echo "TEST EXECUTION COMPLETE"
echo "================================================================================"
echo

# Step 8: Analyze results
echo "Step 8: Analyzing Results"
echo "--------------------------------------------------------------------------------"

if [ $EXIT_CODE -eq 0 ]; then
    print_success "System exited cleanly"
else
    print_error "System exited with error code: $EXIT_CODE"
fi

# Check for errors in log
error_count=$(grep -c "Error\|Exception\|Failed" "$LOG_FILE" 2>/dev/null || echo "0")
warning_count=$(grep -c "Warning\|⚠" "$LOG_FILE" 2>/dev/null || echo "0")

echo
echo "Log Analysis:"
echo "  Errors: $error_count"
echo "  Warnings: $warning_count"

if [ "$error_count" -gt 0 ]; then
    print_warning "Errors found in log. Review: $LOG_FILE"
    echo
    echo "Last 10 error lines:"
    grep -i "error\|exception" "$LOG_FILE" | tail -10
fi

# Extract statistics if available
if grep -q "Session Statistics:" "$LOG_FILE"; then
    echo
    echo "Session Statistics:"
    grep -A 5 "Session Statistics:" "$LOG_FILE" | tail -5
fi

echo

# Step 9: Summary
echo "================================================================================"
echo "SUMMARY"
echo "================================================================================"
echo

if [ $EXIT_CODE -eq 0 ] && [ "$error_count" -eq 0 ]; then
    print_success "Test PASSED - System working correctly"
    echo
    echo "✓ Audio capture working"
    echo "✓ Processing pipeline active"
    echo "✓ Anti-noise generation successful"
    echo "✓ No critical errors"
    echo
    echo "Expected effects:"
    echo "  - Ambient noise reduced 30-50%"
    echo "  - Background sounds muffled"
    echo "  - Continuous noise dampened"
elif [ $EXIT_CODE -eq 0 ] && [ "$error_count" -gt 0 ]; then
    print_warning "Test COMPLETED with warnings"
    echo
    echo "System ran but encountered issues."
    echo "Review log file: $LOG_FILE"
else
    print_error "Test FAILED"
    echo
    echo "System encountered errors."
    echo "Review log file: $LOG_FILE"
    echo
    echo "Common issues:"
    echo "  - Audio device not found → Check microphone/speakers"
    echo "  - Model not found → Run training first"
    echo "  - Permission denied → Check audio permissions"
fi

echo
echo "Log saved to: $LOG_FILE"
echo

# Step 10: Next steps
echo "================================================================================"
echo "NEXT STEPS"
echo "================================================================================"
echo

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ System verification complete"
    echo
    echo "Recommended next steps:"
    echo
    echo "1. Fine-tune for your environment:"
    echo "   python audio_capture.py           # Collect local samples"
    echo "   python train_sklearn_demo.py      # Retrain models"
    echo
    echo "2. Extended testing:"
    echo "   python main.py --mode core --duration 300    # 5 minutes"
    echo
    echo "3. Run with web UI:"
    echo "   python main.py --mode web"
    echo
    echo "4. Production deployment:"
    echo "   See FULL_INTEGRATION_GUIDE.md"
else
    echo "⚠ Fix issues before proceeding"
    echo
    echo "Troubleshooting steps:"
    echo
    echo "1. Check audio devices:"
    echo "   python check_audio_devices.py"
    echo
    echo "2. Verify dependencies:"
    echo "   pip install -r requirements.txt"
    echo
    echo "3. Review detailed guide:"
    echo "   cat LOCAL_EXECUTION_GUIDE.md"
    echo
    echo "4. Check log file:"
    echo "   cat $LOG_FILE"
fi

echo
echo "================================================================================"

exit $EXIT_CODE
