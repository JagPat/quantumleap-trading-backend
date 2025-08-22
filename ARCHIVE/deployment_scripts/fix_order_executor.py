#!/usr/bin/env python3
"""
Fix the corrupted order_executor.py file
"""

def fix_order_executor():
    """Clean up the corrupted order_executor.py file"""
    
    # Read the file
    with open("app/trading_engine/order_executor.py", "r") as f:
        lines = f.readlines()
    
    # Find the line with "# Global executor instance"
    global_executor_line = None
    for i, line in enumerate(lines):
        if "# Global executor instance" in line:
            global_executor_line = i
            break
    
    if global_executor_line is not None:
        # Keep everything up to and including the global executor line + 1
        clean_lines = lines[:global_executor_line + 2]  # +2 to include the executor line
        
        # Write the cleaned file
        with open("app/trading_engine/order_executor.py", "w") as f:
            f.writelines(clean_lines)
        
        print(f"✅ Cleaned order_executor.py - kept {len(clean_lines)} lines")
        print(f"   Removed {len(lines) - len(clean_lines)} orphaned lines")
        return True
    else:
        print("❌ Could not find global executor instance line")
        return False

if __name__ == "__main__":
    fix_order_executor()