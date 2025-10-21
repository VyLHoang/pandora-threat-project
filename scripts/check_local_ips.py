#!/usr/bin/env python3
"""Check local IPs that will be detected by IDS"""
import socket

print("\n" + "="*70)
print("[LOCAL IPs] Detection Test")
print("="*70)

local_ips = set()

# Add localhost
local_ips.add('127.0.0.1')
local_ips.add('::1')

try:
    # Get hostname IP
    hostname = socket.gethostname()
    print(f"\n[HOSTNAME] {hostname}")
    
    host_ip = socket.gethostbyname(hostname)
    local_ips.add(host_ip)
    print(f"[HOST IP] {host_ip}")
    
    # Try to get all IPs by connecting to external
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    primary_ip = s.getsockname()[0]
    local_ips.add(primary_ip)
    s.close()
    print(f"[PRIMARY IP] {primary_ip}")
    
    # Also try gethostbyname_ex for all IPs
    hostname_info = socket.gethostbyname_ex(hostname)
    print(f"\n[ALL IPs from gethostbyname_ex]")
    for ip in hostname_info[2]:
        local_ips.add(ip)
        print(f"  • {ip}")
        
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "="*70)
print("[DETECTED LOCAL IPs]")
print("="*70)
for ip in sorted(local_ips):
    print(f"  + {ip}")

print(f"\n[TOTAL] {len(local_ips)} local IPs detected")

print("\n" + "="*70)
print("[IDS BEHAVIOR]")
print("="*70)
print("\nTraffic FROM these IPs -> IGNORED (outbound)")
print("Traffic TO these IPs FROM external -> DETECTED (inbound)\n")
print("="*70 + "\n")

