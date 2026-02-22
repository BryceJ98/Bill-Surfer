import legiscan_client as lc

doc_ids = {
    "v1_introduced": 3103109,
    "v2_comm_sub_senate": 3129552,
    "v3_amended_senate": 3132087,
    "v4_comm_sub_house": 3181263,
    "v5_amended_house": 3356862,
}

sep = '=' * 60

for label, doc_id in doc_ids.items():
    print()
    print(sep)
    print(f"FETCHING: {label} (doc_id={doc_id})")
    print(sep)
    result = lc.get_bill_text(doc_id)
    if "error" in result:
        print(f"ERROR: {result}")
        continue
    text = result.get("text", "")
    print(f"Type: {result.get('type')}")
    print(f"Date: {result.get('date')}")
    print(f"Size: {len(text):,} chars")
    with open(f"sb197_{label}.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved to sb197_{label}.txt")
    print("--- PREVIEW ---")
    print(text[:500])
