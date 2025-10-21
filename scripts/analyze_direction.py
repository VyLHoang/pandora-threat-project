#!/usr/bin/env python3
"""Analyze attack direction to identify false positives"""
import sys
import os

# Add backend to path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(os.path.dirname(script_dir), 'backend')
sys.path.insert(0, backend_dir)

from database.database import SessionLocal
from models.attack import AttackLog
from datetime import datetime, timedelta

db = SessionLocal()

print("\n" + "="*70)
print("[ANALYZING] Attack Direction - False Positive Detection")
print("="*70)

# Get recent attacks
recent_attacks = db.query(AttackLog).order_by(AttackLog.detected_at.desc()).limit(20).all()

print(f"\n[ANALYZING] Last 20 attacks...")

outbound_count = 0
inbound_count = 0
unknown_count = 0

for i, attack in enumerate(recent_attacks, 1):
    source_ip = str(attack.source_ip)
    target_ip = str(attack.target_ip)
    
    # Determine if local IP
    is_source_local = (source_ip.startswith('192.168.') or 
                       source_ip.startswith('127.') or
                       source_ip.startswith('172.') or
                       source_ip.startswith('10.'))
    
    is_target_local = (target_ip.startswith('192.168.') or 
                       target_ip.startswith('127.') or
                       target_ip.startswith('172.') or
                       target_ip.startswith('10.'))
    
    if i <= 5:  # Print first 5 in detail
        print(f"\n[ATTACK #{i}]")
        print(f"  Time: {attack.detected_at}")
        print(f"  Source: {source_ip}:{attack.source_port}")
        print(f"  Target: {target_ip}:{attack.target_port}")
        print(f"  Type: {attack.attack_type}")
        print(f"  Direction: ", end="")
        
    if is_source_local and not is_target_local:
        if i <= 5:
            print("OUTBOUND (X) FALSE POSITIVE!")
        outbound_count += 1
    elif not is_source_local and is_target_local:
        if i <= 5:
            print("INBOUND (!) REAL ATTACK")
        inbound_count += 1
    else:
        if i <= 5:
            print("UNKNOWN")
        unknown_count += 1

print("\n" + "="*70)
print("[SUMMARY] Last 20 Attacks")
print("="*70)
print(f"  OUTBOUND (False Positives): {outbound_count} (X)")
print(f"  INBOUND (Real Attacks):     {inbound_count} (!)")
print(f"  UNKNOWN:                    {unknown_count}")

# Check all AWS attacks
print("\n" + "="*70)
print("[ANALYZING] All AWS Attacks Today")
print("="*70)

today = datetime.now().replace(hour=0, minute=0, second=0)
aws_attacks = db.query(AttackLog).filter(
    AttackLog.detected_at >= today,
    AttackLog.city == 'Ashburn'
).all()

aws_outbound = 0
aws_inbound = 0

for attack in aws_attacks:
    source_ip = str(attack.source_ip)
    target_ip = str(attack.target_ip)
    
    is_source_local = (source_ip.startswith('192.168.') or 
                       source_ip.startswith('127.') or
                       source_ip.startswith('172.') or
                       source_ip.startswith('10.'))
    
    is_target_local = (target_ip.startswith('192.168.') or 
                       target_ip.startswith('127.') or
                       target_ip.startswith('172.') or
                       target_ip.startswith('10.'))
    
    if is_source_local and not is_target_local:
        aws_outbound += 1
    elif not is_source_local and is_target_local:
        aws_inbound += 1

print(f"\n[AWS ATTACKS TODAY] Total: {len(aws_attacks)}")
print(f"  OUTBOUND (Your traffic to AWS): {aws_outbound} (X)")
print(f"  INBOUND (AWS scanning you):     {aws_inbound} (!)")

# Verdict
print("\n" + "="*70)
print("[VERDICT]")
print("="*70)

if outbound_count > inbound_count:
    print("\n[!] MAJORITY ARE FALSE POSITIVES!")
    print("   -> IDS is detecting YOUR outbound traffic as attacks")
    print("   -> This is NOT real attacks from outside")
    print("   -> IDS v2.1 should have filtered this")
    print("\n[ACTION REQUIRED]")
    print("   1. Restart IDS v2.1 to apply filters")
    print("   2. Verify local IPs are detected correctly")
    print("   3. Consider clearing false positive data")
else:
    print("\n[!] MAJORITY ARE REAL ATTACKS")
    print("   -> External IPs are scanning your machine")
    print("   -> This is normal automated bot scanning")
    print("   -> Ensure firewall is active")

print("\n" + "="*70 + "\n")

db.close()

