
import pypdf
import os

pdf_path = "WinCar-informatiepakket-2026.pdf"

if not os.path.exists(pdf_path):
    print(f"Error: {pdf_path} not found.")
    exit(1)

try:
    reader = pypdf.PdfReader(pdf_path)
    print(f"Number of pages: {len(reader.pages)}")
    
    full_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text += f"\n--- Page {i+1} ---\n"
            full_text += text

    # Print the first 2000 characters to sanity check, but also save to a file so we can grep it or read it systematically if needed.
    # But since I want to analyze modules, I'll print the whole thing to stdout if it's not huge, or just grep for "Module".
    # Let's print the whole thing, standardizing output.
    print(full_text)

except Exception as e:
    print(f"Error reading PDF: {e}")
