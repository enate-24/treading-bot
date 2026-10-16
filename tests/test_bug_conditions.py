"""
Bug Condition Exploration Tests — HFT Bot Fixes
================================================
These tests are EXPECTED TO FAIL on unfixed code.
Failure of each test confirms the corresponding bug exists.

Bugs covered:
  Bug 1 — Inverted Risk/Reward in config (stop_loss > profit_target, min_risk_reward < 1.5)
  Bug 2 — Win/Loss tracking uses signal confidence instead of real MT5 P&L
  Bug 3 — ADX returns raw DX instead of Wilder-smoothed ADX
  Bug 4 — MACD signal_line = macd_line * 0.9 (hardcoded, not a true EMA)
  Bug 5 — Position sizing uses hardcoded pip_value=10 for all symbols including Gold
  Bug 6 — EURJPYm absent from Overlap session best_pairs → should_trade_symbol returns False
  Bug 7 — config/metatrader_config_enhanced.json contains plaintext "password" key
  Bug 8 — _calculate_adx is implemented in ≥ 2 Python files

Requirements validated: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2,
                        7.1, 7.2, 8.1, 8.2
"""

import ast
import glob
import json
import sys
import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path BEFORE any other imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Pre-mock MetaTrader5 before any project module is imported so that
# modules that do `import MetaTrader5 as mt5` at the top level don't fail.
_mt5_mock = MagicMock()
sys.modules.setdefault("MetaTrader5", _mt5_mock)


# ---------------------------------------------------------------------------
# Helper: compute Wilder-smoothed ADX externally (reference implementation)
# ---------------------------------------------------------------------------

def _wilder_ema(values, period):
    """Apply Wilder's exponential moving average to a list of values."""
    if len(values) < period:
        return None
    smoothed = sum(values[:period]) / period
    for v in values[period:]:
        smoothed = smoothed * (period - 1) / period + v / period
    return smoothed


def reference_adx(closes, highs, lows, period=14):
    """Correct Wilder-smoothed ADX.  Returns None when data is insufficient."""
    n = len(closes)
    if n < 2 * period + 1:
        return None

    tr_list, plus_dm_list, minus_dm_list = [], [], []
    for i in range(1, n):
        high_low   = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i - 1])
        low_close  = abs(lows[i]  - closes[i - 1])
        tr_list.append(max(high_low, high_close, low_close))

        up   = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm_list.append(up   if (up > down and up > 0)   else 0.0)
        minus_dm_list.append(down if (down > up and down > 0) else 0.0)

    # Build per-bar DX series for the second Wilder pass
    dx_list = []
    for i in range(period - 1, len(tr_list)):
        seg_tr  = _wilder_ema(tr_list[:i + 1],       period) or 0
        seg_pdm = _wilder_ema(plus_dm_list[:i + 1],  period) or 0
        seg_ndm = _wilder_ema(minus_dm_list[:i + 1], period) or 0
        if seg_tr == 0:
            dx_list.append(0.0)
            continue
        pdi   = 100 * seg_pdm / seg_tr
        ndi   = 100 * seg_ndm / seg_tr
        denom = pdi + ndi
        dx_list.append(100 * abs(pdi - ndi) / denom if denom else 0.0)

    return _wilder_ema(dx_list, period)


# ---------------------------------------------------------------------------
# Helper: standard EMA (2/(period+1) multiplier)
# ---------------------------------------------------------------------------

def _ema(prices, period):
    if len(prices) < period:
        return 0.0
    k = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema


# ---------------------------------------------------------------------------
# Helper: reference MACD signal (true 9-period EMA of MACD history)
# ---------------------------------------------------------------------------

def reference_macd_signal(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow + signal - 1:
        return None
    macd_history = [
        _ema(prices[:i + 1], fast) - _ema(prices[:i + 1], slow)
        for i in range(slow - 1, len(prices))
    ]
    if len(macd_history) < signal:
        return None
    return _ema(macd_history, signal)


# ---------------------------------------------------------------------------
# Deterministic 50-bar price series for indicator tests
# ---------------------------------------------------------------------------

def _make_trending_prices(n=50, start=1.3000, step=0.0010):
    """Uniform step series — suitable for MACD tests but NOT for ADX (too symmetric)."""
    return [start + i * step for i in range(n)]


def _make_ohlcv(closes):
    spread = 0.0005
    highs = [c + spread for c in closes]
    lows  = [c - spread for c in closes]
    return closes, highs, lows


def _make_noisy_trending_ohlcv(n=50, seed=42):
    """
    Deterministic noisy-trending OHLCV series.
    Uses seeded random so results are reproducible across machines.
    The noise ensures plus_dm and minus_dm alternate realistically,
    making raw DX visibly differ from Wilder-smoothed ADX.
    """
    import random
    rng = random.Random(seed)
    closes = [1.3000]
    for _ in range(1, n):
        step  = rng.uniform(0.0001, 0.0015)
        noise = rng.choice([-1, 1]) * rng.uniform(0.0, 0.0004)
        closes.append(closes[-1] + step + noise)
    rng2 = random.Random(seed + 100)
    highs = [c + rng2.uniform(0.0002, 0.0008) for c in closes]
    lows  = [c - rng2.uniform(0.0002, 0.0008) for c in closes]
    return closes, highs, lows


# ===========================================================================
# Test Cases
# ===========================================================================

class TestBugConditions(unittest.TestCase):
    """
    All eight tests MUST FAIL on unfixed code.
    Failure == bug confirmed.  Pass == bug already fixed (unexpected).
    """

    # -----------------------------------------------------------------------
    # Bug 1 — Inverted Risk/Reward Ratio
    # Validates: Requirements 1.1, 1.2
    # -----------------------------------------------------------------------
    def test_bug1_rr_config_inverted(self):
        """
        Bug 1: config has stop_loss=0.0003 > profit_target=0.0002 (0.67:1 R:R)
        and min_risk_reward=0.7 (< 1.5).

        Expected on UNFIXED code: FAIL
        Counterexample: profit_target=0.0002 < 1.5 * stop_loss=0.0003 (= 0.00045)
        """
        config_path = os.path.join(PROJECT_ROOT, "config", "metatrader_config_enhanced.json")
        with open(config_path, "r") as fh:
            cfg = json.load(fh)

        params = cfg["strategy_parameters"]["enhanced_hft"]
        profit_target   = params["profit_target"]
        stop_loss       = params["stop_loss"]
        min_risk_reward = params["min_risk_reward"]

        self.assertGreaterEqual(
            profit_target, 1.5 * stop_loss,
            f"BUG 1: profit_target={profit_target} < 1.5 * stop_loss={stop_loss} "
            f"({1.5 * stop_loss:.5f}).  R:R = {profit_target / stop_loss:.2f}:1"
        )
        self.assertGreaterEqual(
            min_risk_reward, 1.5,
            f"BUG 1: min_risk_reward={min_risk_reward} < 1.5"
        )

    # -----------------------------------------------------------------------
    # Bug 2 — Win/Loss tracking uses confidence not real P&L
    # Validates: Requirements 2.1, 2.2
    # -----------------------------------------------------------------------
    def test_bug2_win_loss_tracking_uses_confidence_not_pnl(self):
        """
        Bug 2: A high-confidence position (0.8) that was stopped out (profit=-50)
        is recorded as a WIN because the code tests confidence > 0.5.

        Expected on UNFIXED code: FAIL (win_count increments, not loss_count)
        Counterexample: confidence=0.8 → win_count += 1, but real profit=-50
        """
        # Import run_enhanced_bot directly (MetaTrader5 already mocked in sys.modules)
        import run_enhanced_bot as rmod

        bot = object.__new__(rmod.EnhancedBot)
        bot.win_count        = 0
        bot.loss_count       = 0
        bot.position_counter = {}

        pos_key  = "XAUUSDm_123456"
        pos_info = {
            "order_id":   99001,
            "symbol":     "XAUUSDm",
            "confidence": 0.8,           # high-confidence but actually a loss
            "timestamp":  datetime(2024, 1, 1, 12, 0, 0),
        }
        bot.open_positions = {pos_key: pos_info}

        # MT5 connector: no open positions (the trade was closed)
        mock_connector = MagicMock()
        mock_connector.get_positions.return_value = []
        bot.mt_connector = mock_connector

        # MT5 history returns a losing deal (profit = -50)
        mock_deal            = MagicMock()
        mock_deal.profit     = -50.0
        mock_deal.position_id = 99001
        rmod.mt5.history_deals_get = MagicMock(return_value=[mock_deal])

        bot.monitor_positions()

        # Fixed code: profit=-50 → loss_count should be 1
        # Unfixed code: confidence=0.8 > 0.5 → win_count=1, loss_count=0
        self.assertEqual(
            bot.loss_count, 1,
            f"BUG 2: loss_count={bot.loss_count}, win_count={bot.win_count}.  "
            "High-confidence stopped-out position was recorded as a WIN "
            "(code uses confidence proxy, not real P&L)."
        )
        self.assertEqual(
            bot.win_count, 0,
            f"BUG 2: win_count should be 0 (trade was a loss), got {bot.win_count}"
        )

    # -----------------------------------------------------------------------
    # Bug 3 — ADX returns raw DX instead of Wilder-smoothed ADX
    # Validates: Requirements 3.1, 3.2
    # -----------------------------------------------------------------------
    def test_bug3_adx_not_wilder_smoothed(self):
        """
        Bug 3: _calculate_adx returns the last single-period DX value directly.

        Expected on UNFIXED code: FAIL (raw DX differs from Wilder ADX by > 0.01)
        Counterexample: 50-bar noisy-trending series → raw DX ≈ 100, Wilder ADX ≈ 97
        """
        closes, highs, lows = _make_noisy_trending_ohlcv(n=50, seed=42)

        ref_adx = reference_adx(closes, highs, lows, period=14)
        self.assertIsNotNone(ref_adx, "Reference ADX could not be computed")

        # Import the strategy module directly (trading_bot.__init__ is already loaded)
        from trading_bot.strategies.enhanced_hft_strategy import EnhancedHFTStrategy
        strategy = EnhancedHFTStrategy.__new__(EnhancedHFTStrategy)
        actual_adx = strategy._calculate_adx(closes, highs, lows, period=14)

        self.assertAlmostEqual(
            actual_adx, ref_adx, delta=0.01,
            msg=(
                f"BUG 3: _calculate_adx returned {actual_adx:.4f} but "
                f"Wilder-smoothed ADX = {ref_adx:.4f}  (diff = {abs(actual_adx - ref_adx):.4f} > 0.01). "
                "Code returns raw DX, not Wilder EMA of DX."
            )
        )

    # -----------------------------------------------------------------------
    # Bug 4 — MACD signal_line is macd_line * 0.9 (hardcoded approximation)
    # Validates: Requirements 4.1, 4.2
    # -----------------------------------------------------------------------
    def test_bug4_macd_signal_is_hardcoded_multiplier(self):
        """
        Bug 4: DataHandler._calculate_macd computes signal_line = macd_line * 0.9.

        Expected on UNFIXED code: FAIL (signal_line == macd_line * 0.9)
        Counterexample: 50-bar series 100..149 → macd_line=6.71, signal=6.039=6.71*0.9
        """
        # Use prices with enough range so EMA values differ beyond rounding (100–149)
        prices = [100.0 + i * 1.0 for i in range(50)]

        from trading_bot.data_handler import DataHandler
        dh = DataHandler.__new__(DataHandler)
        dh._indicator_params = {
            "MACD": {"fast": 12, "slow": 26, "signal": 9}
        }

        macd_line, signal_line, _ = dh._calculate_macd(prices)
        broken_signal = round(macd_line * 0.9, 4)

        # If macd_line is 0.0 (e.g. flat series) we won't catch the bug;
        # assert it's nonzero first.
        self.assertNotEqual(
            macd_line, 0.0,
            "Test series produced MACD line of 0.0 — prices are too uniform to expose the bug"
        )

        self.assertNotEqual(
            round(signal_line, 4), broken_signal,
            (
                f"BUG 4: signal_line={signal_line:.6f} == macd_line * 0.9 "
                f"({broken_signal:.6f}).  "
                "Signal line must be a true 9-period EMA of MACD history, "
                "not a hardcoded 0.9 multiplier."
            )
        )

    # -----------------------------------------------------------------------
    # Bug 5 — Position sizing uses hardcoded pip_value=10 for all symbols
    # Validates: Requirements 5.1, 5.2
    # -----------------------------------------------------------------------
    def test_bug5_position_sizing_uses_hardcoded_pip_value(self):
        """
        Bug 5: calculate_position_size() uses pip_value=10 regardless of symbol.
        For XAUUSDm: contract_size=100, point=0.01 → correct pip_value = 1.0.

        Expected on UNFIXED code: FAIL (mt5.symbol_info is never called)
        Counterexample: XAUUSDm → correct pip_value=1.0, but code uses 10
        """
        import run_enhanced_bot as rmod

        # Set up symbol_info mock for XAUUSDm
        mock_symbol_info                    = MagicMock()
        mock_symbol_info.trade_contract_size = 100
        mock_symbol_info.point              = 0.01
        expected_pip_value                  = 100 * 0.01  # 1.0

        rmod.mt5.symbol_info = MagicMock(return_value=mock_symbol_info)

        bot = object.__new__(rmod.EnhancedBot)
        bot.mt_connector = MagicMock()
        bot.mt_connector.get_account_info.return_value = {"balance": 10000.0}
        bot.config = SimpleNamespace(
            risk_management=SimpleNamespace(risk_per_trade=0.01)
        )

        mock_signal          = MagicMock()
        mock_signal.confidence = 0.75
        mock_signal.metadata   = {"volatility": 0.0001, "stop_loss": 0.0002}

        # Call the actual (unfixed) method
        rmod.mt5.symbol_info.reset_mock()
        rmod.EnhancedBot.calculate_position_size(bot, "XAUUSDm", mock_signal)

        # On UNFIXED code: symbol_info is never called (pip_value=10 is hardcoded)
        # On FIXED code:   symbol_info is called and pip_value = contract_size * point
        called = rmod.mt5.symbol_info.called
        self.assertTrue(
            called,
            f"BUG 5: mt5.symbol_info('XAUUSDm') was NOT called.  "
            f"The code uses hardcoded pip_value=10 instead of "
            f"contract_size * point = {expected_pip_value}. "
            "Position size for Gold is therefore wrong."
        )

    # -----------------------------------------------------------------------
    # Bug 6 — EURJPYm missing from Overlap session best_pairs
    # Validates: Requirements 6.1, 6.2
    # -----------------------------------------------------------------------
    def test_bug6_eurjpym_not_in_overlap_session(self):
        """
        Bug 6: should_trade_symbol("EURJPYm") returns False during Overlap session
        because EURJPYm is absent from Overlap best_pairs.

        Expected on UNFIXED code: FAIL (returns False)
        Counterexample: Overlap best_pairs = [...no EURJPYm...] → False
        """
        from trading_bot.session_manager import SessionManager, TradingSession

        config = {
            "trading":  {"symbols": ["EURJPYm", "GBPJPYm", "XAUUSDm"]},
            "sessions": {
                "asian":    {"enabled": True},
                "london":   {"enabled": True},
                "overlap":  {"enabled": True},
                "new_york": {"enabled": True},
                "quiet":    {"enabled": False},
            },
        }

        sm = SessionManager(config)

        # Force session to OVERLAP with market open
        overlap_cfg           = sm.sessions[TradingSession.OVERLAP]
        sm.session_config     = overlap_cfg
        sm.current_session    = TradingSession.OVERLAP
        sm.is_market_open     = lambda: True

        result = sm.should_trade_symbol("EURJPYm")

        self.assertTrue(
            result,
            "BUG 6: should_trade_symbol('EURJPYm') returned False during Overlap session. "
            "EURJPYm is a configured trading symbol but is absent from Overlap best_pairs: "
            f"{overlap_cfg.best_pairs}"
        )

    # -----------------------------------------------------------------------
    # Bug 7 — Credentials exposed in config JSON
    # Validates: Requirements 7.1, 7.2
    # -----------------------------------------------------------------------
    def test_bug7_password_exposed_in_config(self):
        """
        Bug 7: metatrader_config_enhanced.json contains a non-empty "password" key.

        Expected on UNFIXED code: FAIL (password = "Amour@2456" is present)
        Counterexample: metatrader.password = "Amour@2456" → credential leak
        """
        config_path = os.path.join(PROJECT_ROOT, "config", "metatrader_config_enhanced.json")
        with open(config_path, "r") as fh:
            cfg = json.load(fh)

        mt5_cfg  = cfg.get("metatrader", {})
        password = mt5_cfg.get("password", "")

        self.assertFalse(
            bool(password),
            f"BUG 7: config/metatrader_config_enhanced.json contains a non-empty "
            f"'password' field. Credentials must be loaded from environment variables "
            f"(MT5_PASSWORD), not stored in version-controlled JSON files. "
            f"Found password value of length {len(str(password))}."
        )

    # -----------------------------------------------------------------------
    # Bug 8 — _calculate_adx is implemented in more than one Python file
    # Validates: Requirements 8.1, 8.2
    # -----------------------------------------------------------------------
    def test_bug8_duplicate_adx_implementations(self):
        """
        Bug 8: _calculate_adx exists in both run_enhanced_bot.py and
        trading_bot/strategies/enhanced_hft_strategy.py.

        Expected on UNFIXED code: FAIL (count >= 2)
        Counterexample: 2 definitions found → inconsistent indicator values
        """
        py_files = glob.glob(
            os.path.join(PROJECT_ROOT, "**", "*.py"), recursive=True
        )
        py_files = [
            f for f in py_files
            if "node_modules" not in f
            and ".git" not in f
            and os.path.basename(f) != "test_bug_conditions.py"
        ]

        files_with_adx = []
        for filepath in py_files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                    source = fh.read()
                tree = ast.parse(source, filename=filepath)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == "_calculate_adx":
                        rel_path = os.path.relpath(filepath, PROJECT_ROOT)
                        files_with_adx.append(rel_path)
                        break

        self.assertEqual(
            len(files_with_adx), 1,
            f"BUG 8: _calculate_adx is implemented in {len(files_with_adx)} file(s), "
            f"expected exactly 1 (in trading_bot/utils/indicators.py after fix). "
            f"Currently found in: {files_with_adx}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
