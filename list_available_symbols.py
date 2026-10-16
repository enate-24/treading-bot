"""
List all available symbols on your broker
"""
import MetaTrader5 as mt5

print("\n" + "=" * 60)
print("LISTING ALL AVAILABLE SYMBOLS ON YOUR BROKER")
print("=" * 60)

if not mt5.initialize():
    print("❌ Failed to initialize MT5")
    print("   Make sure MetaTrader 5 is running!")
    input("\nPress Enter to exit...")
    exit()

print("✅ Connected to MT5")
print(f"   Account: {mt5.account_info().login}")
print(f"   Server: {mt5.account_info().server}")

# Get all symbols
symbols = mt5.symbols_get()

if symbols is None or len(symbols) == 0:
    print("\n❌ No symbols found!")
    print("   This is unusual. Check your MT5 connection.")
else:
    print(f"\n✅ Found {len(symbols)} symbols on your broker")
    
    # Filter for forex and gold
    print("\n" + "=" * 60)
    print("FOREX PAIRS (Major)")
    print("=" * 60)
    
    forex_majors = []
    for s in symbols:
        name = s.name
        if any(pair in name.upper() for pair in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']):
            forex_majors.append(name)
            print(f"  {name}")
    
    print("\n" + "=" * 60)
    print("FOREX PAIRS (Cross)")
    print("=" * 60)
    
    forex_cross = []
    for s in symbols:
        name = s.name
        if any(pair in name.upper() for pair in ['EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'EURGBP', 'EURAUD']):
            forex_cross.append(name)
            print(f"  {name}")
    
    print("\n" + "=" * 60)
    print("GOLD / METALS")
    print("=" * 60)
    
    metals = []
    for s in symbols:
        name = s.name
        if any(metal in name.upper() for metal in ['XAU', 'GOLD', 'XAG', 'SILVER']):
            metals.append(name)
            print(f"  {name}")
    
    print("\n" + "=" * 60)
    print("RECOMMENDED SYMBOLS FOR YOUR BOT")
    print("=" * 60)
    
    recommended = forex_majors[:7] + forex_cross[:5]
    if metals:
        recommended.append(metals[0])  # Add first gold symbol
    
    print("\nAdd these to your config:")
    print('  "symbols": [')
    for i, sym in enumerate(recommended):
        comma = "," if i < len(recommended) - 1 else ""
        print(f'    "{sym}"{comma}')
    print('  ]')
    
    print("\n" + "=" * 60)
    print("WHAT TO DO NEXT")
    print("=" * 60)
    print("\n1. Copy the symbol names above")
    print("2. Update your config files with correct symbol names")
    print("3. Or I can create a fixed config for you")

mt5.shutdown()

print()
input("Press Enter to exit...")
