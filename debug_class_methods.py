#!/usr/bin/env python3
"""Debug script to check what methods exist on ScalpingStrategy."""

import sys

# Add the project root to the path
sys.path.insert(0, '.')

from trading_bot.strategies.scalping_strategy import ScalpingStrategy


def debug_class_methods():
    """Debug what methods exist on ScalpingStrategy."""
    print("=== Debugging ScalpingStrategy Methods ===")
    
    strategy = ScalpingStrategy()
    
    print(f"ScalpingStrategy class: {ScalpingStrategy}")
    print(f"ScalpingStrategy instance: {strategy}")
    print(f"ScalpingStrategy file: {ScalpingStrategy.__module__}")
    
    print(f"\nAll attributes and methods:")
    for attr in dir(strategy):
        if not attr.startswith('__'):
            print(f"  {attr}: {type(getattr(strategy, attr))}")
    
    print(f"\nPrivate methods:")
    for attr in dir(strategy):
        if attr.startswith('_') and not attr.startswith('__'):
            print(f"  {attr}: {type(getattr(strategy, attr))}")
    
    # Check if the file content matches what we expect
    import inspect
    print(f"\nSource file location: {inspect.getfile(ScalpingStrategy)}")
    
    # Try to get the source code
    try:
        source = inspect.getsource(ScalpingStrategy)
        print(f"\nSource code length: {len(source)} characters")
        if '_update_state' in source:
            print("_update_state found in source code")
        else:
            print("_update_state NOT found in source code")
    except Exception as e:
        print(f"Could not get source: {e}")


if __name__ == "__main__":
    debug_class_methods()