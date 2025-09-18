#!/usr/bin/env python3
"""
Test script for G2 browser automation in Docker
Run this to verify virtual display and browser setup
"""

import os
import sys
import subprocess

def test_virtual_display():
    """Test if virtual display is working"""
    print("🖥️ Testing virtual display...")
    
    display = os.environ.get('DISPLAY', ':99')
    server_mode = os.environ.get('SERVER_MODE', 'false').lower() == 'true'
    
    print(f"📺 DISPLAY: {display}")
    print(f"🔧 SERVER_MODE: {server_mode}")
    
    if server_mode:
        try:
            result = subprocess.run(['xdpyinfo', '-display', display], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Virtual display is working!")
                return True
            else:
                print(f"❌ Virtual display failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error testing display: {e}")
            return False
    else:
        print("🖥️ Local mode - skipping display test")
        return True

def test_chrome():
    """Test if Chrome/Chromium is installed and working"""
    print("\n🌐 Testing Chrome installation...")
    
    chrome_paths = [
        '/usr/bin/google-chrome',
        '/usr/bin/chromium',
        '/usr/bin/google-chrome-stable'
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            print(f"✅ Found Chrome at: {chrome_path}")
            
            try:
                result = subprocess.run([chrome_path, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                print(f"📋 Version: {result.stdout.strip()}")
                return chrome_path
            except Exception as e:
                print(f"⚠️ Chrome exists but failed to run: {e}")
                
    print("❌ No Chrome/Chromium found")
    return None

def test_botasaurus():
    """Test basic Botasaurus functionality"""
    print("\n🤖 Testing Botasaurus...")
    
    try:
        from botasaurus import browser
        from botasaurus_driver.user_agent import UserAgent
        from botasaurus_driver.window_size import WindowSize
        print("✅ Botasaurus imports successful")
        return True
    except ImportError as e:
        print(f"❌ Botasaurus import failed: {e}")
        return False

def test_browser_startup():
    """Test if browser can start with current configuration"""
    print("\n🚀 Testing browser startup...")
    
    try:
        from botasaurus import browser
        from botasaurus_driver import Driver
        from botasaurus_driver.user_agent import UserAgent
        from botasaurus_driver.window_size import WindowSize
        
        is_server = os.environ.get('SERVER_MODE', 'false').lower() == 'true'
        print(f"🔧 Server mode: {is_server}")
        
        # Test direct Driver creation
        driver_config = {
            'headless': False,
            'enable_xvfb_virtual_display': is_server,
            'user_agent': UserAgent.REAL,
            'window_size': WindowSize.RANDOM,
        }
        
        driver = Driver(**driver_config)
        
        print("🌐 Browser started successfully!")
        driver.get("https://httpbin.org/get")
        title = driver.title
        print(f"📄 Page title: {title}")
        
        driver.close()
        print("✅ Browser test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Browser startup failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 G2 Browser Docker Test Suite")
    print("=" * 50)
    
    tests = [
        ("Virtual Display", test_virtual_display),
        ("Chrome Installation", test_chrome),
        ("Botasaurus Import", test_botasaurus),
        ("Browser Startup", test_browser_startup),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("🎯 Test Results:")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! G2 scraping should work.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check Docker configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
