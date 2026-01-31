#!/usr/bin/env python3
"""
Standalone Tool Testing Script
==============================
Run this script to quickly test individual tools without pytest.

Usage: python tests/test_tools_standalone.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    print("="*60)
    print("GarageAI Tool Testing")
    print("="*60)

    # Test 1: Database Connection
    print("\n[1/5] Testing Database Connection...")
    try:
        from app.tools import get_wincar_connection
        conn = get_wincar_connection()
        conn.close()
        print("   ✅ Database connection successful")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        print("   Hint: Run 'docker-compose up -d' to start SQL Server")
        return

    # Test 2: identify_customer
    print("\n[2/5] Testing identify_customer...")
    try:
        from app.tools import identify_customer
        result = identify_customer("0612345678")
        print(f"   Input: '0612345678'")
        print(f"   Output: {result}")
        print("   ✅ Tool executed successfully")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: check_werkorder_status
    print("\n[3/5] Testing check_werkorder_status...")
    try:
        from app.tools import check_werkorder_status
        result = check_werkorder_status("XX-99-XX")
        print(f"   Input: 'XX-99-XX'")
        print(f"   Output: {result}")
        print("   ✅ Tool executed successfully")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: check_part_stock
    print("\n[4/5] Testing check_part_stock...")
    try:
        from app.tools import check_part_stock
        result = check_part_stock("Remblokken")
        print(f"   Input: 'Remblokken'")
        print(f"   Output: {result}")
        print("   ✅ Tool executed successfully")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: generate_payment_link
    print("\n[5/5] Testing generate_payment_link...")
    try:
        from app.tools import generate_payment_link
        result = generate_payment_link("2024001")
        print(f"   Input: '2024001'")
        print(f"   Output: {result}")
        print("   ✅ Tool executed successfully")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "="*60)
    print("Testing Complete!")
    print("="*60)

if __name__ == "__main__":
    main()
