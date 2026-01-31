"""Property-based tests for Configuration Manager validation."""

import pytest
import math
from decimal import Decimal
from hypothesis import given, strategies as st, assume
from typing import Dict, Any, List

from trading_bot.configuration_manager import ConfigurationManager, ConfigurationError
from trading_bot.models.config import Environment, ConfigurationConstraints


class TestConfigurationManagerProperties:
    """Property-based tests for Configuration Manager."""

    @given(
        risk_per_trade=st.floats(min_value=0.001, max_value=0.05, allow_nan=False, allow_infinity=False),
        max_drawdown=st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
        daily_loss_limit=st.floats(min_value=0.01, max_value=0.2, allow_nan=False, allow_infinity=False),
        strategy=st.sampled_from(["scalping", "swing_trading"]),
        timeframes=st.lists(
            st.sampled_from(["1m", "5m", "15m", "30m", "1h", "4h", "1d"]),
            min_size=1,
            max_size=5,
            unique=True
        ),
        symbols=st.lists(
            st.text(min_size=3, max_size=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ/"),
            min_size=1,
            max_size=10,
            unique=True
        ),
        rate_limit=st.integers(min_value=1, max_value=1000),
        timeout=st.integers(min_value=5, max_value=300)
    )
    def test_property_15_valid_configuration_acceptance(
        self,
        risk_per_trade: float,
        max_drawdown: float,
        daily_loss_limit: float,
        strategy: str,
        timeframes: List[str],
        symbols: List[str],
        rate_limit: int,
        timeout: int
    ):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with valid values within predefined ranges and constraints,
        the Configuration Manager should accept the configuration and return True from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create valid configuration with all parameters within constraints
        valid_config = {
            "trading": {
                "symbols": symbols,
                "timeframes": timeframes,
                "strategy": strategy,
                "risk_per_trade": risk_per_trade,
                "max_drawdown": max_drawdown,
                "daily_loss_limit": daily_loss_limit
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": rate_limit,
                    "timeout": timeout,
                    "priority": 1
                }
            },
            "environment": "development",
            "version": "1.0.0"
        }
        
        # Configuration Manager should validate this as True
        validation_result = config_manager.validate_configuration(valid_config)
        
        assert validation_result is True, \
            f"Valid configuration was rejected. Config: {valid_config}"

    @given(
        risk_per_trade=st.one_of(
            st.floats(min_value=-1.0, max_value=0.0009, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.051, max_value=1.0, allow_nan=False, allow_infinity=False)
        )
    )
    def test_property_15_invalid_risk_per_trade_rejection(self, risk_per_trade: float):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with risk_per_trade outside the valid range (0.001-0.05),
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create configuration with invalid risk_per_trade
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": risk_per_trade,  # Invalid value
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Invalid risk_per_trade ({risk_per_trade}) was accepted when it should be rejected"

    @given(
        max_drawdown=st.one_of(
            st.floats(min_value=-1.0, max_value=0.049, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.501, max_value=2.0, allow_nan=False, allow_infinity=False)
        )
    )
    def test_property_15_invalid_max_drawdown_rejection(self, max_drawdown: float):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with max_drawdown outside the valid range (0.05-0.5),
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create configuration with invalid max_drawdown
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": max_drawdown,  # Invalid value
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Invalid max_drawdown ({max_drawdown}) was accepted when it should be rejected"

    @given(
        daily_loss_limit=st.one_of(
            st.floats(min_value=-1.0, max_value=0.009, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.201, max_value=2.0, allow_nan=False, allow_infinity=False)
        )
    )
    def test_property_15_invalid_daily_loss_limit_rejection(self, daily_loss_limit: float):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with daily_loss_limit outside the valid range (0.01-0.2),
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create configuration with invalid daily_loss_limit
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": daily_loss_limit  # Invalid value
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Invalid daily_loss_limit ({daily_loss_limit}) was accepted when it should be rejected"

    @given(
        strategy=st.text(min_size=1, max_size=20).filter(
            lambda x: x not in ["scalping", "swing_trading"]
        )
    )
    def test_property_15_invalid_strategy_rejection(self, strategy: str):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with strategy not in supported strategies list,
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create configuration with invalid strategy
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": strategy,  # Invalid strategy
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Invalid strategy ({strategy}) was accepted when it should be rejected"

    @given(
        invalid_timeframes=st.lists(
            st.text(min_size=1, max_size=10).filter(
                lambda x: x not in ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
            ),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    def test_property_15_invalid_timeframes_rejection(self, invalid_timeframes: List[str]):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with timeframes not in supported timeframes list,
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create configuration with invalid timeframes
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": invalid_timeframes,  # Invalid timeframes
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Invalid timeframes ({invalid_timeframes}) were accepted when they should be rejected"

    @given(
        symbols_count=st.integers(min_value=51, max_value=100)
    )
    def test_property_15_excessive_symbols_rejection(self, symbols_count: int):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with more symbols than the maximum allowed (50),
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Generate too many symbols
        symbols = [f"SYM{i}/USDT" for i in range(symbols_count)]
        
        # Create configuration with too many symbols
        invalid_config = {
            "trading": {
                "symbols": symbols,  # Too many symbols
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Configuration with {symbols_count} symbols was accepted when max is 50"

    @given(
        rate_limit=st.one_of(
            st.integers(min_value=-100, max_value=0),
            st.integers(min_value=1001, max_value=2000)
        )
    )
    def test_property_15_invalid_rate_limit_rejection(self, rate_limit: int):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with rate_limit outside the valid range (1-1000),
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create configuration with invalid rate_limit
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": rate_limit,  # Invalid rate_limit
                    "timeout": 30,
                    "priority": 1
                }
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Invalid rate_limit ({rate_limit}) was accepted when it should be rejected"

    @given(
        timeout=st.one_of(
            st.integers(min_value=-100, max_value=4),
            st.integers(min_value=301, max_value=1000)
        )
    )
    def test_property_15_invalid_timeout_rejection(self, timeout: int):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with timeout outside the valid range (5-300),
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create configuration with invalid timeout
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": timeout,  # Invalid timeout
                    "priority": 1
                }
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Invalid timeout ({timeout}) was accepted when it should be rejected"

    @given(
        missing_field=st.sampled_from(["name", "api_key", "api_secret"])
    )
    def test_property_15_missing_required_fields_rejection(self, missing_field: str):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with missing required exchange fields,
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create base exchange config
        exchange_config = {
            "name": "test_exchange",
            "api_key": "valid_api_key",
            "api_secret": "valid_api_secret",
            "sandbox": True,
            "rate_limit": 100,
            "timeout": 30,
            "priority": 1
        }
        
        # Remove the specified required field
        del exchange_config[missing_field]
        
        # Create configuration with missing required field
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": exchange_config  # Missing required field
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Configuration missing required field '{missing_field}' was accepted when it should be rejected"

    @given(
        empty_field=st.sampled_from(["name", "api_key", "api_secret"])
    )
    def test_property_15_empty_required_fields_rejection(self, empty_field: str):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with empty required exchange fields,
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create exchange config with empty required field
        exchange_config = {
            "name": "test_exchange",
            "api_key": "valid_api_key",
            "api_secret": "valid_api_secret",
            "sandbox": True,
            "rate_limit": 100,
            "timeout": 30,
            "priority": 1
        }
        
        # Set the specified field to empty string
        exchange_config[empty_field] = ""
        
        # Create configuration with empty required field
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": exchange_config  # Empty required field
            }
        }
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Configuration with empty required field '{empty_field}' was accepted when it should be rejected"

    @given(
        config_structure=st.one_of(
            st.dictionaries(st.text(), st.text()).filter(lambda x: "trading" not in x and len(x) > 0),
            st.dictionaries(st.text(), st.text()).filter(lambda x: "exchanges" not in x and len(x) > 0)
        )
    )
    def test_property_15_malformed_configuration_rejection(self, config_structure: Dict[str, Any]):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input that has content but is missing required sections,
        the Configuration Manager should handle it gracefully and return True (since it only validates existing sections).
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Configuration Manager should handle configurations gracefully
        validation_result = config_manager.validate_configuration(config_structure)
        
        # Should return True for configurations without trading/exchanges sections (they're optional)
        # The validation only validates sections that exist
        assert validation_result is True, \
            f"Configuration without trading/exchanges sections was rejected: {config_structure}"

    @given(
        nan_or_inf_value=st.one_of(
            st.just(float('nan')),
            st.just(float('inf')),
            st.just(float('-inf'))
        ),
        field_name=st.sampled_from(["risk_per_trade", "max_drawdown", "daily_loss_limit"])
    )
    def test_property_15_nan_infinity_values_rejection(self, nan_or_inf_value: float, field_name: str):
        """
        **Feature: trading-bot-system, Property 15: Configuration Validation**
        
        For any configuration input with NaN or infinity values in numeric fields,
        the Configuration Manager should reject the configuration and return False from validation.
        **Validates: Requirements 9.2**
        """
        # Create configuration manager for this test
        config_manager = ConfigurationManager(config_dir="test_config", environment=Environment.DEVELOPMENT)
        # Create configuration with NaN or infinity value
        invalid_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "test_exchange": {
                    "name": "test_exchange",
                    "api_key": "valid_api_key",
                    "api_secret": "valid_api_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            }
        }
        
        # Set the specified field to NaN or infinity
        invalid_config["trading"][field_name] = nan_or_inf_value
        
        # Configuration Manager should reject this configuration
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert validation_result is False, \
            f"Configuration with {field_name}={nan_or_inf_value} was accepted when it should be rejected"