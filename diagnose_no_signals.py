"""
Diagnostic script to check why bot is not generating signals.
"""
import MetaTrader5 as mt5
from datetime import datetime, time
import json

def check_mt5_connection():
    """Check MetaTrader 5 connection."""
    print("=" * 60)
    print("CHECKING METATRADER 5 CONNECTION")
    print("=" * 60)
    
    if not mt5.initialize():
        print("❌ Failed to initialize MT5")
        return False
    
    account_info = mt5.account_info()
    if account_info is None:
        print("❌ Failed to get account info")
        return False
    
    print(f"✅ Connected to MT5")
    print(f"   Account: {account_info.login}")
    print(f"   Balance: ${account_info.balance:.2f}")
    print(f"   Server: {account_info.server}")
    print()
    return True

def check_current_session():
    """Check current trading session."""
    print("=" * 60)
    print("CHECKING CURRENT SESSION")
    print("=" * 60)
    
    now = datetime.utcnow()
    current_time = now.time()
    
    print(f"Current UTC Time: {current_time.strftime('%H:%M:%S')}")
    
    if time(0, 0) <= current_time < time(8, 0):
        session = "Asian Session"
        min_conf = 0.35
    elif time(8, 0) <= current_time < time(13, 0):
        session = "London Session"
        min_conf = 0.20
    elif time(13, 0) <= current_time < time(17, 0):
        session = "London/NY Overlap"
        min_conf = 0.15
    elif time(17, 0) <= current_time < time(22, 0):
        session = "New York Session"
        min_conf = 0.20
    else:
        session = "Quiet Period"
        min_conf = 0.40
    
    print(f"Current Session: {session}")
    print(f"Min Confidence Required: {min_conf * 100}%")
    print()

def check_market_data(symbol="EURUSD"):
    """Check if market data is available."""
    print("=" * 60)
    print(f"CHECKING MARKET DATA FOR {symbol}")
    print("=" * 60)
    
    # Get tick data
    ticks = mt5.copy_ticks_from(symbol, datetime.utcnow(), 10, mt5.COPY_TICKS_ALL)
    
    if ticks is None or len(ticks) == 0:
        print(f"❌ No tick data available for {symbol}")
        print("   Possible reasons:")
        print("   - Market is closed")
        print("   - Symbol not available")
        print("   - No trading activity")
        return False
    
    print(f"✅ Tick data available: {len(ticks)} ticks")
    print(f"   Last tick time: {datetime.fromtimestamp(ticks[-1]['time'])}")
    print(f"   Last bid: {ticks[-1]['bid']:.5f}")
    print(f"   Last ask: {ticks[-1]['ask']:.5f}")
    print(f"   Spread: {(ticks[-1]['ask'] - ticks[-1]['bid']):.5f}")
    
    # Get OHLC data
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 10)
    
    if rates is None or len(rates) == 0:
        print(f"❌ No OHLC data available for {symbol}")
        return False
    
    print(f"✅ OHLC data available: {len(rates)} bars")
    print(f"   Last bar time: {datetime.fromtimestamp(rates[-1]['time'])}")
    print(f"   Last close: {rates[-1]['close']:.5f}")
    print(f"   Last volume: {rates[-1]['tick_volume']}")
    print()
    return True

def check_all_symbols():
    """Check all configured symbols."""
    print("=" * 60)
    print("CHECKING ALL SYMBOLS")
    print("=" * 60)
    
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD"]
    
    for symbol in symbols:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ {symbol}: Not available")
            continue
        
        if not symbol_info.visible:
            print(f"⚠️  {symbol}: Not visible (adding to Market Watch...)")
            mt5.symbol_select(symbol, True)
        
        # Get last tick
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"❌ {symbol}: No tick data")
            continue
        
        spread = tick.ask - tick.bid
        print(f"✅ {symbol}: Bid={tick.bid:.5f}, Ask={tick.ask:.5f}, Spread={spread:.5f}")
    
    print()

def check_hft_parameters():
    """Check HFT strategy parameters."""
    print("=" * 60)
    print("CHECKING HFT PARAMETERS")
    print("=" * 60)
    
    try:
        with open('config/metatrader_config_session_based.json', 'r') as f:
            config = json.load(f)
        
        print("Configuration loaded successfully")
        print(f"Strategy: {config['trading']['strategy']}")
        print(f"Session-based: {config['trading']['session_based']}")
        print(f"Symbols: {', '.join(config['trading']['symbols'])}")
        print()
        
        print("Session Settings:")
        for session_name, session_config in config.get('sessions', {}).items():
            enabled = session_config.get('enabled', True)
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"  {session_name}: {status}")
        print()
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        print()

def main():
    """Run all diagnostics."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "BOT SIGNAL DIAGNOSTIC TOOL" + " " * 22 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # Run checks
    if not check_mt5_connection():
        print("\n❌ Cannot proceed without MT5 connection")
        mt5.shutdown()
        input("\nPress Enter to exit...")
        return
    
    check_current_session()
    check_hft_parameters()
    check_all_symbols()
    
    # Check specific symbol in detail
    check_market_data("EURUSD")
    check_market_data("GBPUSD")
    
    print("=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)
    print()
    print("POSSIBLE REASONS FOR NO SIGNALS:")
    print()
    print("1. Market conditions don't meet HFT criteria")
    print("   - Not enough price movement")
    print("   - Not enough volume")
    print("   - Spread too wide")
    print()
    print("2. Confidence threshold too high")
    print("   - Current session requires certain confidence level")
    print("   - Market volatility might be too low")
    print()
    print("3. All positions already open")
    print("   - Check if max positions reached")
    print()
    print("4. Symbol restrictions")
    print("   - Current session might prefer different pairs")
    print()
    print("RECOMMENDATION:")
    print("- Wait for London/NY Overlap (13:00-17:00 GMT)")
    print("- This is the BEST session with most opportunities")
    print("- Or use relaxed configuration: FIX_NO_TRADES.bat")
    print()
    
    mt5.shutdown()
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
