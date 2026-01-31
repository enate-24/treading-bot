#!/usr/bin/env python3
"""Debug script to see the actual source code of ScalpingStrategy."""

import sys
import inspect

# Add the project root to the path
sys.path.insert(0, '.')

from trading_bot.strategies.scalping_strategy import ScalpingStrategy


def debug_actual_source():
    """Debug the actual source code of ScalpingStrategy."""
    print("=== Actual ScalpingStrategy Source Code ===")
    
    try:
        source = inspect.getsource(ScalpingStrategy)
        print(source)
    except Exception as e:
        print(f"Could not get source: {e}")


if __name__ == "__main__":
    debug_actual_source()