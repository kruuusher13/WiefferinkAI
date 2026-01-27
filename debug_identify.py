from tools import identify_customer, get_wincar_connection

print("🔍 Debugging identify_customer Tool")
print("-----------------------------------")

# 1. Direct SQL Check
print("1. Low-Level Verification:")
try:
    conn = get_wincar_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT KlantNaam, Telefoon FROM Communicatie_Relaties")
    rows = cursor.fetchall()
    print(f"   Found {len(rows)} rows in DB:")
    for row in rows:
        print(f"   - Name: '{row.KlantNaam}', Phone: '{row.Telefoon}'")
    conn.close()
except Exception as e:
    print(f"   ❌ Low-level DB Error: {e}")

# 2. Tool Logic Check
print("\n2. Tool Execution Test:")
input_numbers = ["0612345678", "06-12345678", "+31 6 12345678", "0687654321"]

for num in input_numbers:
    print(f"   Search for '{num}': ", end="")
    try:
        # Note: we call the function underneath the tool wrapper if possible,
        # but langchain tools are callable directly.
        result = identify_customer.invoke({"phone_number": num}) 
        print(f"Result -> {result}")
    except Exception as e:
        print(f"ERROR: {e}")
