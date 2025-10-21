#!/usr/bin/env python3
"""Check attacks in database"""
import sys
import os

# Add backend to path (script is in scripts/, backend is in ../backend/)
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(os.path.dirname(script_dir), 'backend')
sys.path.insert(0, backend_dir)

from database.database import SessionLocal
from models.attack import AttackLog
from datetime import datetime, timedelta

db = SessionLocal()

total = db.query(AttackLog).count()
print(f'\n[TOTAL] {total} attacks in database')

if total > 0:
    # Latest attack
    recent = db.query(AttackLog).order_by(AttackLog.detected_at.desc()).first()
    print(f'\n[LATEST ATTACK]')
    print(f'  Time: {recent.detected_at}')
    print(f'  Type: {recent.attack_type}')
    print(f'  From: {recent.source_ip}:{recent.source_port}')
    print(f'  Tool: {recent.detected_tool}')
    print(f'  Severity: {recent.severity}')
    print(f'  Location: {recent.city}, {recent.country}')
    
    # Oldest attack
    oldest = db.query(AttackLog).order_by(AttackLog.detected_at).first()
    print(f'\n[OLDEST ATTACK]')
    print(f'  Time: {oldest.detected_at}')
    print(f'  Type: {oldest.attack_type}')
    
    # Today's attacks
    today = datetime.now().replace(hour=0, minute=0, second=0)
    today_count = db.query(AttackLog).filter(AttackLog.detected_at >= today).count()
    print(f'\n[TODAY] {today_count} attacks')
    
    # Last 5 attacks
    print(f'\n[LAST 5 ATTACKS]')
    last5 = db.query(AttackLog).order_by(AttackLog.detected_at.desc()).limit(5).all()
    for i, atk in enumerate(last5, 1):
        print(f'  {i}. {atk.detected_at} | {atk.source_ip} | {atk.attack_type}')
else:
    print('\n[INFO] No attacks in database')

db.close()

