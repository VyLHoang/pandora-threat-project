#!/usr/bin/env python3
"""Clear old attacks from database (optional - for fresh testing)"""
import sys
import os

# Add backend to path (script is in scripts/, backend is in ../backend/)
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(os.path.dirname(script_dir), 'backend')
sys.path.insert(0, backend_dir)

from database.database import SessionLocal
from models.attack import AttackLog
from datetime import datetime, timedelta

print("\n" + "="*70)
print("[CLEAR] Old Attacks Data")
print("="*70)

db = SessionLocal()

total_before = db.query(AttackLog).count()
print(f"\n[BEFORE] {total_before} attacks in database")

if total_before > 0:
    choice = input("\n⚠️  Do you want to clear ALL old attacks? (yes/no): ")
    
    if choice.lower() in ['yes', 'y']:
        db.query(AttackLog).delete()
        db.commit()
        print("\n[OK] All attacks cleared!")
        print(f"[AFTER] {db.query(AttackLog).count()} attacks in database")
    else:
        print("\n[CANCELLED] No data was deleted")
else:
    print("\n[INFO] Database is already empty")

db.close()
print("\n" + "="*70)
print("[TIP] Now start IDS and test attacks from another machine!")
print("="*70 + "\n")

