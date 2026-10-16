"""
Fix MetaTrader 5 symbols - Add all trading symbols to Market Watch
"""
import MetaTrader5 as mt5
import time

def fix_symbols():
    """Add all required symbols to Market Watch."""
    print("\n" + "=" * 60)
    print("FIXING METATRADER 5 SYMBOLS")
    print("=" * 60)
    
    # Initialize MT5
    if not mt5.initialize():
        print("❌ Failed to initialize MT5")
        print("   Make sure MetaTrader 5 is running!")
        return False
    
    print("✅ Connected to MT5")
    
    # List of symbols to add
    symbols = [
        "EURUSD",
        "GBPUSD", 
        "USDJPY",
        "AUDUSD",
        "USDCAD",
        "EURJPY",
        "GBPJPY",
        "AUDJPY",
        "NZDJPY",
        "EURGBP",
        "XAUUSD"
    ]
    
    print(f"\nAdding {len(symbols)} symbols to Market Watch...\n")
    
    success_count = 0
    failed_symbols = []
    
    for symbol in symbols:
        # Check if symbol exists
        symbol_info = mt5.symbol_info(symbol)
        
        if symbol_info is None:
            print(f"❌ {symbol}: Not found on broker")
            failed_symbols.append(symbol)
            continue
        
        # Add to Market Watch if not visible
        if not symbol_info.visible:
            if mt5.symbol_select(symbol, True):
                print(f"✅ {symbol}: Added to Market Watch")
                success_count += 1
            else:
                print(f"❌ {symbol}: Failed to add")
                failed_symbols.append(symbol)
        else:
            print(f"✅ {symbol}: Already in Market Watch")
            success_count += 1
        
        # Small delay
        time.sleep(0.1)
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"✅ Successfully added: {success_count}/{len(symbols)}")
    
    if failed_symbols:
        print(f"❌ Failed symbols: {', '.join(failed_symbols)}")
        print("\nNote: Failed symbols may not be available on your broker.")
        print("      Check your broker's symbol list in MT5.")
    
    # Verify by getting tick data
    print("\n" + "=" * 60)
    print("VERIFICATION - Checking Tick Data")
    print("=" * 60)
    
    for symbol in symbols:
        if symbol in failed_symbols:
            continue
            
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            print(f"✅ {symbol}: Bid={tick.bid:.5f}, Ask={tick.ask:.5f}, Spread={tick.ask-tick.bid:.5f}")
        else:
            print(f"❌ {symbol}: No tick data")
    
    mt5.shutdown()
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
    
    if success_count == len(symbols):
        print("\n✅ All symbols are now available!")
        print("✅ Your bot should now be able to trade!")
        print("\nNext steps:")
        print("  1. Restart your bot")
        print("  2. Wait for signals (you're in the BEST session now!)")
    else:
        print(f"\n⚠️  {len(failed_symbols)} symbols are not available on your broker")
        print("   The bot will trade the available symbols only")
    
    return True

if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "FIX MT5 SYMBOLS" + " " * 28 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    print("This will add all trading symbols to MetaTrader 5 Market Watch")
    print()
    
    input("Press Enter to continue...")
    
    fix_symbols()
    
    print()
    input("Press Enter to exit...")
