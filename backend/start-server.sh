#!/bin/bash

# 🖥️ G2 Scraping: Start virtual display if in server mode
if [ "$SERVER_MODE" = "true" ]; then
    echo "🖥️ Starting virtual display for G2 scraping..."
    
    # Start Xvfb virtual display
    Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -dpi 96 &
    XVFB_PID=$!
    
    # Wait for display to be ready
    sleep 2
    
    # Verify display is working
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "✅ Virtual display :99 is ready"
    else
        echo "❌ Failed to start virtual display"
        exit 1
    fi
    
    # Set up cleanup on exit
    cleanup() {
        echo "🧹 Cleaning up virtual display..."
        kill $XVFB_PID 2>/dev/null || true
    }
    trap cleanup EXIT
    
else
    echo "🖥️ Local mode - using real display"
fi

# Start the application
echo "🚀 Starting application..."
exec "$@"
