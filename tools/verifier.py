
import asyncio
import os
import sys
from typing import Optional

# Ensure src is in pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.server import analyze_codebase, get_callers, get_callees, detect_cycles, get_orphan_functions

def run_verification():
    print("=== Starting LegacyGraph-MCP Verification ===")
    
    # 1. Load Data
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "legacy_project")
    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found at {data_dir}")
        return

    print(f"Reading files from: {data_dir}")
    full_code = ""
    for f in os.listdir(data_dir):
        if f.endswith(".cpp") or f.endswith(".h"):
            with open(os.path.join(data_dir, f), "r") as file:
                full_code += file.read() + "\n"
    
    print(f"Total Code Size: {len(full_code)} bytes")

    # --- Ground Truth Definition ---
    EXPECTED_NODES = {
        "main", "main_loop", "process_client", 
        "log_transaction", "calculate_interest", "update_balance", 
        "db_connect", "hidden_backdoor"
    }
    
    EXPECTED_EDGES = [
        ("main", "main_loop"),
        ("main_loop", "process_client"),
        ("main_loop", "main_loop"), # Recursion
        ("process_client", "log_transaction"),
        ("process_client", "calculate_interest"),
        ("process_client", "update_balance"),
        ("log_transaction", "db_connect"),
        ("update_balance", "db_connect"),
        ("update_balance", "log_transaction"),
        ("hidden_backdoor", "db_connect")
    ]
    
    EXPECTED_ORPHANS = {"hidden_backdoor"} # technically 'main' is often an entry point, not orphan.
    
    print("\n--- Step 1: Analyze Codebase ---")
    result = analyze_codebase(full_code)
    print(result)
    
    if "Error" in result:
        print("FAILED: Analysis step failed.")
        sys.exit(1)

    print("\n--- Step 2: Accuracy Verification ---")
    
    # Check Nodes
    # We can't easily get *all* nodes from the simple tools exposed unless we parse manually or infer from edges + orphans.
    # But analyze_codebase typically returns a count.
    # Let's verify Edges extensively as that covers nodes.
    
    found_edges = 0
    total_edges = len(EXPECTED_EDGES)
    
    print(f"Checking {total_edges} expected dependencies...")
    
    for caller, callee in EXPECTED_EDGES:
        callees = get_callees(caller)
        if callee in callees:
            print(f"  [OK] {caller} -> {callee}")
            found_edges += 1
        else:
            print(f"  [MISSING] {caller} -> {callee}")
            
    edge_accuracy = (found_edges / total_edges) * 100
    print(f"\nDependency Detection Accuracy: {edge_accuracy:.2f}%")
    
    # Check Cycles
    print("\nChecking Cycle Detection...")
    cycles = detect_cycles()
    # Expect main_loop recursion
    # Note: detect_cycles returns a formatted string like "Circular dependencies detected:\n- main_loop -> main_loop"
    has_recursion = "main_loop -> main_loop" in cycles
    if has_recursion:
        print("  [OK] Detected 'main_loop' recursion.")
    else:
        print("  [FAIL] Failed to detect 'main_loop' recursion.")

    # Check Orphans
    print("\nChecking Orphan Detection...")
    orphans = get_orphan_functions()
    # Note: 'main' might be listed as orphan if nothing calls it.
    actual_orphans = set(orphans.replace("Orphan functions (never called): ", "").split(", "))
    
    orphan_hit = 0
    for exp in EXPECTED_ORPHANS:
        if exp in actual_orphans:
            print(f"  [OK] Found expected orphan '{exp}'")
            orphan_hit += 1
        else:
            print(f"  [MISSING] Expected orphan '{exp}' not found.")
            
    final_score = (found_edges + orphan_hit + (1 if has_recursion else 0)) / (total_edges + len(EXPECTED_ORPHANS) + 1) * 100
    print(f"\n=== Final System Accuracy: {final_score:.2f}% ===")
    
    if final_score < 100:
        sys.exit(1)


if __name__ == "__main__":
    run_verification()
