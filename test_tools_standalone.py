from tools import identify_customer, web_search

print("--- Testing Identify Customer (Aggressive Normalization) ---")
# Test with spaces and Country Code
phone_input = "0 6 1 2 3 4 5 6 7 8" 
print(f"Input: '{phone_input}'")
result = identify_customer.invoke({"phone_number": phone_input})
print(f"Result: {result}")

phone_input_2 = "+31 6 12345678"
print(f"\nInput: '{phone_input_2}'")
result_2 = identify_customer.invoke({"phone_number": phone_input_2})
print(f"Result: {result_2}")

print("\n--- Testing Web Search ---")
try:
    search_result = web_search.invoke({"query": "What does a check engine light mean?"})
    print(f"Search Result: {search_result[:200]}...") # Print first 200 chars
except Exception as e:
    print(f"Search failed: {e}")
