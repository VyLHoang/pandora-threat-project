#!/usr/bin/env python3
"""
Test Honeypot Logging
Test script to verify honeypot server is sending logs to central monitor
"""

import requests
import json
import time
from datetime import datetime

# Configuration
HONEYPOT_SERVER = "https://172.235.245.60"
CENTRAL_SERVER = "https://172.232.246.68"
API_KEY = "pandora-secret-key-2024"

def test_honeypot_paths():
    """Test various honeypot paths"""
    test_paths = [
        "/",
        "/admin",
        "/phpmyadmin",
        "/wp-admin",
        "/.env",
        "/config.php",
        "/api/v1/auth/login",
        "/api/v1/users",
        "/api/v1/config",
        "/login.php",
        "/admin.php",
        "/test.php",
        "/robots.txt",
        "/.git/",
        "/.htaccess"
    ]
    
    print("🔍 Testing Honeypot Paths...")
    print("=" * 50)
    
    for path in test_paths:
        try:
            url = f"{HONEYPOT_SERVER}{path}"
            print(f"Testing: {path}")
            
            # Test GET request
            response = requests.get(url, timeout=10, verify=False)
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            # Check if it's a fake response
            content = response.text.lower()
            if any(keyword in content for keyword in ['fake', 'error', 'not found', 'mysql_connect']):
                print(f"  ✓ Fake response detected")
            else:
                print(f"  ⚠ Real response (might be issue)")
            
            print()
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            print()

def test_central_monitor_logs():
    """Test if central monitor is receiving logs"""
    print("📊 Checking Central Monitor Logs...")
    print("=" * 50)
    
    try:
        # Test central monitor health
        health_url = f"{CENTRAL_SERVER}/health"
        response = requests.get(health_url, timeout=10, verify=False)
        print(f"Central Monitor Health: {response.status_code}")
        
        # Test admin dashboard access
        dashboard_url = f"{CENTRAL_SERVER}/admin-dashboard/"
        response = requests.get(dashboard_url, timeout=10, verify=False)
        print(f"Admin Dashboard: {response.status_code}")
        
        # Test user monitoring API
        api_url = f"{CENTRAL_SERVER}/api/admin/users/stats"
        headers = {"X-API-Key": API_KEY}
        response = requests.get(api_url, headers=headers, timeout=10, verify=False)
        print(f"User Stats API: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Total Users: {data.get('total_users', 'N/A')}")
            print(f"  Active Today: {data.get('active_users_today', 'N/A')}")
            print(f"  Total Scans: {data.get('total_scans', 'N/A')}")
        
    except Exception as e:
        print(f"✗ Error testing central monitor: {e}")

def test_nmap_simulation():
    """Simulate nmap scan to test IDS"""
    print("🔍 Simulating Nmap Scan...")
    print("=" * 50)
    
    # Test common ports
    test_ports = [80, 443, 22, 8001, 8002, 5000]
    
    for port in test_ports:
        try:
            if port in [80, 443]:
                # HTTP/HTTPS - test with requests
                protocol = "https" if port == 443 else "http"
                url = f"{protocol}://172.232.246.68"
                response = requests.get(url, timeout=5, verify=False)
                print(f"Port {port} ({protocol}): {response.status_code}")
            else:
                # Other ports - just test connection
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex(('172.232.246.68', port))
                sock.close()
                if result == 0:
                    print(f"Port {port}: Open")
                else:
                    print(f"Port {port}: Closed/Filtered")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Port {port}: Error - {e}")

def main():
    print("🚀 PANDORA HONEYPOT TESTING")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Honeypot Server: {HONEYPOT_SERVER}")
    print(f"Central Server: {CENTRAL_SERVER}")
    print("=" * 60)
    print()
    
    # Test 1: Honeypot paths
    test_honeypot_paths()
    
    print("\n" + "=" * 60)
    
    # Test 2: Central monitor
    test_central_monitor_logs()
    
    print("\n" + "=" * 60)
    
    # Test 3: Nmap simulation
    test_nmap_simulation()
    
    print("\n" + "=" * 60)
    print("✅ Testing Complete!")
    print()
    print("Next steps:")
    print("1. Check Central Monitor dashboard for new logs")
    print("2. Verify IDS detected the port scans")
    print("3. Check honeypot logs in Central Monitor")
    print("4. If no logs appear, check:")
    print("   - API key configuration")
    print("   - Network connectivity between servers")
    print("   - Service logs: sudo journalctl -u pandora-* -f")

if __name__ == "__main__":
    main()
