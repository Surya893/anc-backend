#!/bin/bash
#
# Quick Start Script for ANC System
#

echo "================================================================================"
echo "ANC SYSTEM - QUICK START"
echo "================================================================================"
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
if ! command_exists python3 && ! command_exists python; then
    echo "Error: Python not found. Please install Python 3.7 or later."
    exit 1
fi

PYTHON_CMD=$(command_exists python3 && echo "python3" || echo "python")
echo "✓ Found Python: $PYTHON_CMD"

# Check pip
if ! command_exists pip3 && ! command_exists pip; then
    echo "Error: pip not found. Please install pip."
    exit 1
fi

PIP_CMD=$(command_exists pip3 && echo "pip3" || echo "pip")
echo "✓ Found pip: $PIP_CMD"

echo
echo "Select quick start option:"
echo "  1) Install dependencies only"
echo "  2) Train models (requires audio samples)"
echo "  3) Run ANC system (core mode - no web UI)"
echo "  4) Run ANC system with web UI"
echo "  5) Verify integration (test without hardware)"
echo

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo
        echo "[1/1] Installing dependencies..."
        $PIP_CMD install -r requirements.txt
        echo
        echo "✓ Dependencies installed"
        ;;

    2)
        echo
        echo "[1/2] Installing dependencies..."
        $PIP_CMD install -r requirements.txt
        echo
        echo "[2/2] Training models..."
        echo "This requires audio samples in the database."
        echo "Run 'python audio_capture.py' first if you haven't collected samples."
        read -p "Continue with training? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            $PYTHON_CMD train_sklearn_demo.py
        fi
        ;;

    3)
        echo
        echo "[1/3] Installing dependencies..."
        $PIP_CMD install -r requirements.txt
        echo
        echo "[2/3] Checking models..."
        if [ ! -f "models/noise_classifier_sklearn.joblib" ]; then
            echo "⚠ Models not found. Please train models first (option 2)."
            exit 1
        fi
        echo "✓ Models found"
        echo
        echo "[3/3] Starting ANC system (core mode)..."
        echo "Press Ctrl+C to stop"
        echo
        $PYTHON_CMD main.py --mode core
        ;;

    4)
        echo
        echo "[1/3] Installing dependencies..."
        $PIP_CMD install -r requirements.txt
        echo
        echo "[2/3] Checking models..."
        if [ ! -f "models/noise_classifier_sklearn.joblib" ]; then
            echo "⚠ Models not found. Please train models first (option 2)."
            echo "Continuing anyway - system will work without classification."
        fi
        echo
        echo "[3/3] Starting ANC system with web UI..."
        echo
        echo "Access the web interface at:"
        echo "  Desktop: http://localhost:5000"
        echo "  Mobile:  http://$(hostname -I | awk '{print $1}'):5000"
        echo
        echo "Press Ctrl+C to stop"
        echo
        $PYTHON_CMD main.py --mode web
        ;;

    5)
        echo
        echo "[1/2] Installing dependencies..."
        $PIP_CMD install -q numpy scikit-learn librosa Flask 2>/dev/null
        echo
        echo "[2/2] Running integration tests..."
        echo
        $PYTHON_CMD verify_integration.py
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo
echo "================================================================================"
