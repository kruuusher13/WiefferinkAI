import os
import re

def verify_file_content(path, checks):
    if not os.path.exists(path):
        print(f"FAILED: {path} does not exist.")
        return False
    
    with open(path, 'r') as f:
        content = f.read()
    
    all_passed = True
    for check_name, regex in checks.items():
        if re.search(regex, content, re.MULTILINE | re.IGNORECASE):
            print(f"PASSED: {path} contains {check_name}")
        else:
            print(f"FAILED: {path} missing {check_name} (Pattern: {regex})")
            all_passed = False
    return all_passed

def verify_modules():
    print("\n--- Verifying System Prompt & Modules ---")
    graph_checks = {
        "Officiele Modules Header": r"OFFICIELE WINCAR MODULES:",
        "Werkplaats Module": r"WERKPLAATS:",
        "Magazijn Module": r"MAGAZIJN:",
        "Financieel Module": r"FINANCIEEL:",
        "Communicatie Module": r"COMMUNICATIE \(CRM\):",
        "Dutch Rule": r"Spreek ALTIJD en UITSLUITEND Nederlands",
        "Conciseness Rule": r"MAXIMAAL 2 zinnen",
        "Security Rule": r"Financiële acties .* vereisen .* bevestiging"
    }
    verify_file_content("graph.py", graph_checks)

    print("\n--- Verifying Tools ---")
    tools_checks = {
        "Communicatie Tool": r"WinCar Module: COMMUNICATIE",
        "Werkplaats Tool": r"WinCar Module: WERKPLAATS",
        "Magazijn Tool": r"WinCar Module: MAGAZIJN",
        "Financieel Tool": r"WinCar Module: FINANCIEEL"
    }
    verify_file_content("tools.py", tools_checks)

    print("\n--- Verifying Mock DB ---")
    sql_checks = {
        "Communicatie Table": r"CREATE TABLE Communicatie_Relaties",
        "Werkplaats Table": r"CREATE TABLE Werkplaats_Voertuigen",
        "Magazijn Table": r"CREATE TABLE Magazijn_Artikelen",
        "Financieel Table": r"CREATE TABLE Financieel_Facturen"
    }
    verify_file_content("mock_wincar_db.sql", sql_checks)

if __name__ == "__main__":
    verify_modules()
    
    # Syntax check
    print("\n--- Checking Syntax ---")
    import py_compile
    try:
        py_compile.compile("graph.py", doraise=True)
        print("PASSED: graph.py syntax")
        py_compile.compile("tools.py", doraise=True)
        print("PASSED: tools.py syntax")
        py_compile.compile("main.py", doraise=True)
        print("PASSED: main.py syntax")
    except Exception as e:
        print(f"FAILED: Syntax error: {e}")
