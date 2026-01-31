#!/usr/bin/env python3
"""
GarageAI System Test Suite
===========================
Comprehensive tests for database, tools, and LangGraph agent.

Run with: pytest tests/test_garageai_system.py -v
Or standalone: python tests/test_garageai_system.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

class TestConfig:
    """Test configuration and expected values."""

    # Expected database tables
    EXPECTED_TABLES = [
        'Communicatie_Relaties',
        'Werkplaats_Voertuigen',
        'Werkplaats_Werkorders',
        'Magazijn_Artikelen',
        'Financieel_Facturen'
    ]

    # Sample test data
    TEST_PHONE = "0612345678"
    TEST_PLATE = "XX-99-XX"
    TEST_PART = "Remblokken"
    TEST_CUSTOMER_NAME = "Jan de Vries"


# ============================================================================
# PHASE 1: PREREQUISITES CHECK
# ============================================================================

def test_prerequisites():
    """Check that all prerequisites are met."""
    print("\n" + "="*60)
    print("PHASE 1: PREREQUISITES CHECK")
    print("="*60)

    results = {}

    # Check Python version
    import sys
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    results['python_version'] = py_version
    print(f"✅ Python version: {py_version}")

    # Check required packages
    required_packages = [
        'fastapi', 'langchain_core', 'langgraph',
        'langchain_google_genai', 'pyodbc', 'pydantic'
    ]

    for pkg in required_packages:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"✅ Package '{pkg}' installed")
            results[f'pkg_{pkg}'] = True
        except ImportError:
            print(f"❌ Package '{pkg}' NOT installed")
            results[f'pkg_{pkg}'] = False

    # Check environment variables
    env_vars = ['GOOGLE_API_KEY']
    for var in env_vars:
        val = os.getenv(var)
        if val:
            print(f"✅ Environment variable '{var}' is set")
            results[f'env_{var}'] = True
        else:
            print(f"⚠️  Environment variable '{var}' NOT set (some features may fail)")
            results[f'env_{var}'] = False

    return results


# ============================================================================
# PHASE 2: DATABASE TESTS
# ============================================================================

def test_database_connection():
    """Test database connectivity."""
    print("\n" + "="*60)
    print("PHASE 2: DATABASE TESTS")
    print("="*60)

    try:
        from app.tools import get_wincar_connection

        print("Testing database connection...")
        conn = get_wincar_connection()
        print("✅ Database connection successful")
        conn.close()
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Make sure Docker is running: docker-compose up -d")
        return False


def test_database_schema():
    """Verify all expected tables exist."""
    print("\nVerifying database schema...")

    try:
        from app.tools import get_wincar_connection

        conn = get_wincar_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)

        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        print(f"Found tables: {tables}")

        results = {}
        for expected_table in TestConfig.EXPECTED_TABLES:
            if expected_table in tables:
                print(f"✅ Table '{expected_table}' exists")
                results[expected_table] = True
            else:
                print(f"❌ Table '{expected_table}' MISSING")
                results[expected_table] = False

        return results
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return {}


def test_database_data():
    """Verify sample data exists in tables."""
    print("\nVerifying sample data...")

    try:
        from app.tools import get_wincar_connection

        conn = get_wincar_connection()
        cursor = conn.cursor()

        tables_to_check = [
            ('Communicatie_Relaties', 'Customers'),
            ('Werkplaats_Voertuigen', 'Vehicles'),
            ('Werkplaats_Werkorders', 'Work Orders'),
            ('Magazijn_Artikelen', 'Parts'),
        ]

        results = {}
        for table, display_name in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                status = "✅" if count > 0 else "⚠️"
                print(f"{status} {display_name} ({table}): {count} records")
                results[table] = count
            except Exception as e:
                print(f"❌ Error checking {table}: {e}")
                results[table] = -1

        conn.close()
        return results
    except Exception as e:
        print(f"❌ Data verification failed: {e}")
        return {}


def test_sample_queries():
    """Test sample queries that the tools use."""
    print("\nTesting sample queries...")

    try:
        from app.tools import get_wincar_connection

        conn = get_wincar_connection()
        cursor = conn.cursor()

        # Query 1: Customer lookup
        print("\n📋 Customer Lookup Query:")
        cursor.execute("""
            SELECT KlantNaam, KlantID, Telefoon
            FROM Communicatie_Relaties
            WHERE Telefoon LIKE ?
        """, f"%{TestConfig.TEST_PHONE}%")
        row = cursor.fetchone()
        if row:
            print(f"   ✅ Found: {row.KlantNaam} (ID: {row.KlantID})")
        else:
            print(f"   ⚠️ No customer found with phone {TestConfig.TEST_PHONE}")

        # Query 2: Werkorder status
        print("\n🔧 Werkorder Status Query:")
        cursor.execute("""
            SELECT TOP 1 w.WerkorderID, w.Status, w.Omschrijving
            FROM Werkplaats_Werkorders w
            JOIN Werkplaats_Voertuigen v ON w.VoertuigID = v.VoertuigID
            WHERE v.Kenteken LIKE ?
            ORDER BY w.AanmaakDatum DESC
        """, f"%{TestConfig.TEST_PLATE}%")
        row = cursor.fetchone()
        if row:
            print(f"   ✅ Found: Werkorder #{row.WerkorderID} - Status: {row.Status}")
        else:
            print(f"   ⚠️ No werkorder found for plate {TestConfig.TEST_PLATE}")

        # Query 3: Part stock
        print("\n📦 Part Stock Query:")
        cursor.execute("""
            SELECT Omschrijving, ArtikelCode, VoorraadAantal, Verkoopprijs
            FROM Magazijn_Artikelen
            WHERE Omschrijving LIKE ?
        """, f"%{TestConfig.TEST_PART}%")
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                stock_status = "op voorraad" if row.VoorraadAantal > 0 else "NIET op voorraad"
                print(f"   ✅ {row.Omschrijving} ({row.ArtikelCode}): {row.VoorraadAantal} {stock_status} - €{row.Verkoopprijs}")
        else:
            print(f"   ⚠️ No parts found matching '{TestConfig.TEST_PART}'")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        return False


# ============================================================================
# PHASE 3: TOOL TESTS
# ============================================================================

def test_tools():
    """Test each LangGraph tool."""
    print("\n" + "="*60)
    print("PHASE 3: TOOL TESTS")
    print("="*60)

    results = {}

    try:
        from app.tools import (
            identify_customer,
            check_werkorder_status,
            check_part_stock,
            generate_payment_link,
            # schedule_appointment,  # Skip write operation in tests
            # web_search  # Skip external API call
        )

        # Test 1: identify_customer
        print("\n🔍 Test: identify_customer")
        try:
            result = identify_customer(TestConfig.TEST_PHONE)
            print(f"   Input: '{TestConfig.TEST_PHONE}'")
            print(f"   Output: {result}")
            success = 'Klant' in result or 'Geen' in result or 'gevonden' in result
            print(f"   Status: {'✅ PASS' if success else '❌ FAIL'}")
            results['identify_customer'] = success
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results['identify_customer'] = False

        # Test 2: check_werkorder_status
        print("\n🔍 Test: check_werkorder_status")
        try:
            result = check_werkorder_status(TestConfig.TEST_PLATE)
            print(f"   Input: '{TestConfig.TEST_PLATE}'")
            print(f"   Output: {result}")
            success = 'Werkorder' in result or 'Geen' in result or 'werkorder' in result.lower()
            print(f"   Status: {'✅ PASS' if success else '❌ FAIL'}")
            results['check_werkorder_status'] = success
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results['check_werkorder_status'] = False

        # Test 3: check_part_stock
        print("\n🔍 Test: check_part_stock")
        try:
            result = check_part_stock(TestConfig.TEST_PART)
            print(f"   Input: '{TestConfig.TEST_PART}'")
            print(f"   Output: {result}")
            success = '€' in result or 'niet gevonden' in result.lower() or 'voorraad' in result.lower()
            print(f"   Status: {'✅ PASS' if success else '❌ FAIL'}")
            results['check_part_stock'] = success
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results['check_part_stock'] = False

        # Test 4: generate_payment_link
        print("\n🔍 Test: generate_payment_link")
        try:
            result = generate_payment_link("12345")
            print(f"   Input: '12345'")
            print(f"   Output: {result}")
            success = 'https://' in result or 'pay' in result.lower()
            print(f"   Status: {'✅ PASS' if success else '❌ FAIL'}")
            results['generate_payment_link'] = success
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results['generate_payment_link'] = False

        return results

    except ImportError as e:
        print(f"❌ Failed to import tools: {e}")
        return {}


# ============================================================================
# PHASE 4: LANGGRAPH AGENT TEST
# ============================================================================

def test_langgraph_agent():
    """Test the LangGraph agent (requires GOOGLE_API_KEY)."""
    print("\n" + "="*60)
    print("PHASE 4: LANGGRAPH AGENT TEST")
    print("="*60)

    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  GOOGLE_API_KEY not set - skipping agent test")
        print("   Set it with: export GOOGLE_API_KEY=your_key")
        return None

    try:
        from app.graph import app, get_initial_messages
        from langchain_core.messages import HumanMessage

        print("\n🤖 Testing LangGraph Agent...")

        # Test 1: Simple greeting
        print("\nTest 1: Simple greeting")
        config = {"configurable": {"thread_id": "test-greeting"}}

        inputs = {
            "messages": get_initial_messages() + [HumanMessage(content="Hallo")]
        }

        result = app.invoke(inputs, config=config)
        response = result['messages'][-1].content
        print(f"   Input: 'Hallo'")
        print(f"   Output: {response[:200]}...")
        print(f"   Status: ✅ PASS (got response)")

        # Test 2: Tool-calling scenario
        print("\nTest 2: Tool-calling (werkorder status)")
        config2 = {"configurable": {"thread_id": "test-tool-call"}}

        inputs2 = {
            "messages": get_initial_messages() + [
                HumanMessage(content=f"Wat is de status van kenteken {TestConfig.TEST_PLATE}?")
            ]
        }

        result2 = app.invoke(inputs2, config=config2)
        response2 = result2['messages'][-1].content
        print(f"   Input: 'Wat is de status van kenteken {TestConfig.TEST_PLATE}?'")
        print(f"   Output: {response2[:200]}...")

        # Check if tool was called (by looking at message history)
        tool_called = any(
            hasattr(msg, 'tool_calls') and msg.tool_calls
            for msg in result2['messages']
        )
        print(f"   Tool called: {'✅ Yes' if tool_called else '❌ No'}")

        return True

    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 5: LANGSMITH CONFIGURATION
# ============================================================================

def test_langsmith_config():
    """Check and display LangSmith configuration."""
    print("\n" + "="*60)
    print("PHASE 5: LANGSMITH CONFIGURATION")
    print("="*60)

    config = {
        'LANGCHAIN_TRACING_V2': os.getenv('LANGCHAIN_TRACING_V2'),
        'LANGCHAIN_API_KEY': os.getenv('LANGCHAIN_API_KEY'),
        'LANGCHAIN_PROJECT': os.getenv('LANGCHAIN_PROJECT', 'default'),
    }

    print("\nLangSmith Environment Variables:")
    print(f"  LANGCHAIN_TRACING_V2: {config['LANGCHAIN_TRACING_V2'] or '(not set)'}")
    print(f"  LANGCHAIN_API_KEY: {'***set***' if config['LANGCHAIN_API_KEY'] else '(not set)'}")
    print(f"  LANGCHAIN_PROJECT: {config['LANGCHAIN_PROJECT']}")

    if config['LANGCHAIN_TRACING_V2'] == 'true' and config['LANGCHAIN_API_KEY']:
        print("\n✅ LangSmith is configured!")
        print(f"   View traces at: https://smith.langchain.com/projects/{config['LANGCHAIN_PROJECT']}")
        return True
    else:
        print("\n⚠️  LangSmith is NOT fully configured.")
        print("   To enable tracing, run:")
        print("   export LANGCHAIN_TRACING_V2=true")
        print("   export LANGCHAIN_API_KEY=your_api_key")
        print("   export LANGCHAIN_PROJECT=GarageAI")
        return False


# ============================================================================
# TEST REPORT
# ============================================================================

def generate_report(results: dict):
    """Generate a summary test report."""
    print("\n" + "="*60)
    print("TEST REPORT SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    print(f"\n📊 Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"   Total: {len(results)} tests")

    if failed > 0:
        print("\n❌ Failed tests:")
        for name, result in results.items():
            if result is False:
                print(f"   - {name}")

    if skipped > 0:
        print("\n⚠️ Skipped tests:")
        for name, result in results.items():
            if result is None:
                print(f"   - {name}")

    print("\n" + "="*60)
    return passed, failed, skipped


# ============================================================================
# MAIN
# ============================================================================

def run_all_tests():
    """Run the complete test suite."""
    print("\n" + "🧪"*30)
    print("  GARAGEAI SYSTEM TEST SUITE")
    print("🧪"*30)

    all_results = {}

    # Phase 1: Prerequisites
    prereq_results = test_prerequisites()
    all_results['prerequisites'] = all(
        v for k, v in prereq_results.items()
        if k.startswith('pkg_')
    )

    # Phase 2: Database
    db_connected = test_database_connection()
    all_results['db_connection'] = db_connected

    if db_connected:
        schema_results = test_database_schema()
        all_results['db_schema'] = all(schema_results.values()) if schema_results else False

        data_results = test_database_data()
        all_results['db_data'] = all(v > 0 for v in data_results.values()) if data_results else False

        all_results['db_queries'] = test_sample_queries()
    else:
        all_results['db_schema'] = None
        all_results['db_data'] = None
        all_results['db_queries'] = None

    # Phase 3: Tools
    if db_connected:
        tool_results = test_tools()
        all_results['tools'] = all(tool_results.values()) if tool_results else False
    else:
        all_results['tools'] = None

    # Phase 4: Agent
    agent_result = test_langgraph_agent()
    all_results['agent'] = agent_result

    # Phase 5: LangSmith
    all_results['langsmith'] = test_langsmith_config()

    # Generate report
    generate_report(all_results)

    return all_results


if __name__ == "__main__":
    run_all_tests()
