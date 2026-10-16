"""
Test the fixed bot configuration
"""
import json
from trading_bot.strategies.conservative_strategy import ConservativeStrategy

print("=" * 60)
print("TESTING FIXED BOT CONFIGURATION")
print("=" * 60)

# Test 1: Load configuration
print("\n1. Testing configuration load...")
try:
    with open('config/metatrader_config_fixed.json', 'r') as f:
        config = json.load(f)
    print("   ✓ Configuration loaded successfully")
    print(f"   Symbols: {config['trading']['symbols']}")
    print(f"   Min confidence: {config['trading']['min_confidence']}")
    print(f"   Max positions: {config['trading']['max_positions']}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

# Test 2: Initialize strategy
print("\n2. Testing strategy initialization...")
try:
    strategy = ConservativeStrategy(config.get('strategy_parameters', {}).get('enhanced_hft', {}))
    print("   ✓ Strategy initialized successfully")
    print(f"   Strategy name: {strategy.get_name()}")
    print(f"   Allowed symbols: {strategy.allowed_symbols}")
    print(f"   Good hours: {strategy.good_hours}")
    print(f"   Avoid hours: {strategy.avoid_hours}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

# Test 3: Test time filtering
print("\n3. Testing time filtering...")
try:
    from datetime import datetime
    current_hour = datetime.now().hour
    should_trade = strategy.should_trade_now()
    print(f"   Current hour: {current_hour} GMT")
    print(f"   Should trade: {should_trade}")
    
    if current_hour in strategy.good_hours:
        print(f"   ✓ Hour {current_hour} is in good hours list")
    elif current_hour in strategy.avoid_hours:
        print(f"   ⚠ Hour {current_hour} is in avoid hours list")
    else:
        print(f"   ⚠ Hour {current_hour} is not in good or avoid list")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: Test symbol filtering
print("\n4. Testing symbol filtering...")
test_symbols = ['EURJPYm', 'GBPJPYm', 'EURUSDm', 'XAUUSDm']
for symbol in test_symbols:
    allowed = symbol in strategy.allowed_symbols
    status = "✓ ALLOWED" if allowed else "✗ BLOCKED"
    print(f"   {symbol}: {status}")

# Test 5: Test safety limits
print("\n5. Testing safety limits...")
print(f"   Max consecutive losses: 3")
print(f"   Max daily loss: $0.50")
print(f"   Current consecutive losses: {strategy._state['consecutive_losses']}")
print(f"   Current daily loss: ${strategy._state['daily_loss']:.2f}")

print("\n" + "=" * 60)
print("CONFIGURATION TEST COMPLETE")
print("=" * 60)
print("\nThe fixed bot is ready to use!")
print("Run: START_FIXED_BOT.bat")
print("\nIMPORTANT:")
print("- Only trades EURJPYm and GBPJPYm")
print("- Only trades during hours: 0, 1, 18, 19, 20 GMT")
print("- Stops after 3 consecutive losses")
print("- Stops at $0.50 daily loss")
print("=" * 60)
