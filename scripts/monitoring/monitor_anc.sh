#!/bin/bash
#
# Real-time ANC System Monitor
# Shows live statistics while system is running
#

echo "================================================================================"
echo "ANC SYSTEM MONITOR"
echo "================================================================================"
echo

# Check if system is running
if ! pgrep -f "python.*main.py" > /dev/null; then
    echo "Error: ANC system not running"
    echo
    echo "Start the system first:"
    echo "  python main.py --mode core"
    echo
    exit 1
fi

PID=$(pgrep -f "python.*main.py")
echo "Monitoring ANC system (PID: $PID)"
echo "Press Ctrl+C to stop monitoring (system will continue running)"
echo

# Function to get process info
get_cpu_usage() {
    ps -p "$PID" -o %cpu= 2>/dev/null | tr -d ' '
}

get_mem_usage() {
    ps -p "$PID" -o %mem= 2>/dev/null | tr -d ' '
}

get_mem_mb() {
    ps -p "$PID" -o rss= 2>/dev/null | awk '{print $1/1024}'
}

get_thread_count() {
    ps -T -p "$PID" 2>/dev/null | wc -l
}

get_runtime() {
    ps -p "$PID" -o etime= 2>/dev/null | tr -d ' '
}

# Monitor loop
echo "Time       CPU%   MEM%   MEM(MB)  Threads  Runtime"
echo "--------   ----   ----   -------  -------  -------"

while true; do
    # Check if process still running
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo
        echo "System stopped"
        exit 0
    fi

    # Get metrics
    TIME=$(date +%H:%M:%S)
    CPU=$(get_cpu_usage)
    MEM=$(get_mem_usage)
    MEM_MB=$(get_mem_mb)
    THREADS=$(get_thread_count)
    RUNTIME=$(get_runtime)

    # Display
    printf "%-10s %-6s %-6s %-8.1f %-8d %s\n" \
        "$TIME" "$CPU" "$MEM" "$MEM_MB" "$((THREADS-1))" "$RUNTIME"

    sleep 1
done
