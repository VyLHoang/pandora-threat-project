#!/usr/bin/env python3
"""
Kibana Dashboard Import Script
Automatically import Pandora dashboards, visualizations, and index patterns into Kibana
"""

import requests
import json
import time
import sys
from pathlib import Path

# Configuration
KIBANA_URL = "http://localhost:5601"
KIBANA_API_BASE = f"{KIBANA_URL}/api"
DASHBOARD_FILE = Path(__file__).parent / "kibana_dashboards.json"


def wait_for_kibana(max_retries=30, retry_delay=10):
    """Wait for Kibana to be ready"""
    print(f"[INFO] Waiting for Kibana to be ready at {KIBANA_URL}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(f"{KIBANA_URL}/api/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                # Kibana 8.x uses 'level' instead of 'state'
                overall_status = status.get('status', {}).get('overall', {})
                level = overall_status.get('level', 'unknown')
                
                if level in ['available', 'green']:
                    print("[SUCCESS] Kibana is ready!")
                    return True
                else:
                    print(f"[INFO] Kibana status: {level} (attempt {attempt}/{max_retries})")
        except requests.exceptions.RequestException as e:
            print(f"[INFO] Kibana not ready yet (attempt {attempt}/{max_retries}): {e}")
        
        if attempt < max_retries:
            time.sleep(retry_delay)
    
    print("[ERROR] Kibana did not become ready in time")
    return False


def import_dashboards():
    """Import dashboards from JSON file"""
    print("\n" + "="*70)
    print("Pandora Kibana Dashboard Importer")
    print("="*70 + "\n")
    
    # Check if dashboard file exists
    if not DASHBOARD_FILE.exists():
        print(f"[ERROR] Dashboard file not found: {DASHBOARD_FILE}")
        return False
    
    # Wait for Kibana
    if not wait_for_kibana():
        return False
    
    # Load dashboard configuration
    print(f"\n[INFO] Loading dashboard configuration from {DASHBOARD_FILE.name}...")
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            dashboard_config = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load dashboard file: {e}")
        return False
    
    # Import objects using Kibana Saved Objects API
    print("\n[INFO] Importing objects into Kibana...")
    
    headers = {
        'kbn-xsrf': 'true',
        'Content-Type': 'application/json'
    }
    
    try:
        # Use the import API with overwrite=true
        url = f"{KIBANA_API_BASE}/saved_objects/_import?overwrite=true"
        
        # Prepare the file upload (ndjson format)
        # Convert objects to ndjson format
        ndjson_data = ""
        for obj in dashboard_config['objects']:
            ndjson_data += json.dumps(obj) + "\n"
        
        files = {
            'file': ('export.ndjson', ndjson_data, 'application/ndjson')
        }
        
        response = requests.post(
            url,
            headers={'kbn-xsrf': 'true'},
            files=files,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("\n[SUCCESS] Dashboards imported successfully!")
            
            if result.get('success'):
                print(f"[INFO] Successfully imported {result.get('successCount', 0)} objects")
            
            if result.get('successResults'):
                print("\n[INFO] Imported objects:")
                for obj in result['successResults']:
                    obj_type = obj.get('type', 'unknown')
                    obj_id = obj.get('id', 'unknown')
                    print(f"  - {obj_type}: {obj_id}")
            
            if result.get('errors'):
                print("\n[WARNING] Some errors occurred:")
                for error in result['errors']:
                    print(f"  - {error.get('type')}: {error.get('error', {}).get('message', 'Unknown error')}")
            
            return True
        else:
            print(f"[ERROR] Failed to import dashboards: HTTP {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False


def print_access_info():
    """Print access information"""
    print("\n" + "="*70)
    print("Dashboard Access Information")
    print("="*70)
    print(f"\n[INFO] Kibana URL: {KIBANA_URL}")
    print("\n[INFO] Available Dashboards:")
    print("  1. Pandora IDS Attack Overview")
    print("     -> View at: {}/app/dashboards#/view/pandora-ids-dashboard".format(KIBANA_URL))
    print("\n  2. Pandora Honeypot Activity")
    print("     -> View at: {}/app/dashboards#/view/pandora-honeypot-dashboard".format(KIBANA_URL))
    print("\n[INFO] Index Patterns:")
    print("  - pandora-ids-attacks-*")
    print("  - pandora-honeypot-logs-*")
    print("\n" + "="*70 + "\n")


def main():
    """Main function"""
    success = import_dashboards()
    
    if success:
        print_access_info()
        print("[SUCCESS] Dashboard import completed successfully!")
        print("\n[TIP] Wait a few minutes for data to appear in dashboards")
        print("[TIP] Dashboards auto-refresh every 60 seconds")
        return 0
    else:
        print("\n[ERROR] Dashboard import failed")
        print("\n[TROUBLESHOOTING]")
        print("  1. Ensure Elasticsearch is running: curl http://localhost:9200")
        print("  2. Ensure Kibana is running: curl http://localhost:5601/api/status")
        print("  3. Check docker logs: docker logs pandora_kibana")
        return 1


if __name__ == '__main__':
    sys.exit(main())

