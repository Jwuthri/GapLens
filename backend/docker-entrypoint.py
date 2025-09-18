#!/usr/bin/env python3
"""
Docker entrypoint script for G2-compatible browser automation
Handles virtual display startup and application launching
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

class DockerEntrypoint:
    def __init__(self):
        self.xvfb_process = None
        self.app_process = None
        self.display = os.environ.get('DISPLAY', ':99')
        self.server_mode = os.environ.get('SERVER_MODE', 'false').lower() == 'true'
        
    def log(self, message):
        """Simple logging"""
        print(f"🐳 {message}", flush=True)
        
    def start_virtual_display(self):
        """Start Xvfb virtual display"""
        if not self.server_mode:
            self.log("Local mode - skipping virtual display")
            return True
            
        self.log(f"Starting virtual display {self.display}...")
        
        try:
            # Start Xvfb
            cmd = [
                'Xvfb', self.display,
                '-screen', '0', '1920x1080x24',
                '-nolisten', 'tcp',
                '-dpi', '96'
            ]
            
            self.xvfb_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # Wait for display to be ready
            time.sleep(2)
            
            # Verify display is working
            result = subprocess.run(
                ['xdpyinfo', '-display', self.display],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.log(f"✅ Virtual display {self.display} is ready")
                return True
            else:
                self.log(f"❌ Virtual display verification failed: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            self.log(f"❌ Failed to start virtual display: {e}")
            return False
    
    def cleanup(self, signum=None, frame=None):
        """Cleanup processes on exit"""
        self.log("🧹 Cleaning up...")
        
        if self.app_process:
            self.log("Stopping application...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
        
        if self.xvfb_process:
            self.log("Stopping virtual display...")
            self.xvfb_process.terminate()
            try:
                self.xvfb_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.xvfb_process.kill()
                
        sys.exit(0)
    
    def start_application(self, cmd_args):
        """Start the main application"""
        self.log(f"🚀 Starting application: {' '.join(cmd_args)}")
        
        try:
            self.app_process = subprocess.Popen(cmd_args)
            return self.app_process.wait()
        except KeyboardInterrupt:
            self.log("Received interrupt signal")
            return 0
        except Exception as e:
            self.log(f"❌ Application failed: {e}")
            return 1
    
    def run(self, cmd_args):
        """Main entrypoint"""
        self.log("🖥️ Docker Entrypoint for G2 Browser Automation")
        self.log(f"📺 Display: {self.display}")
        self.log(f"🔧 Server Mode: {self.server_mode}")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.cleanup)
        signal.signal(signal.SIGINT, self.cleanup)
        
        # Start virtual display if needed
        if not self.start_virtual_display():
            self.log("❌ Virtual display setup failed")
            return 1
        
        # Start application
        try:
            return self.start_application(cmd_args)
        finally:
            self.cleanup()

def main():
    """Entry point"""
    if len(sys.argv) < 2:
        print("Usage: docker-entrypoint.py <command> [args...]")
        return 1
    
    entrypoint = DockerEntrypoint()
    return entrypoint.run(sys.argv[1:])

if __name__ == "__main__":
    sys.exit(main())
