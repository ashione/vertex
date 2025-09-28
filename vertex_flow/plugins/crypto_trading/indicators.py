"""
Technical indicators calculation module for crypto trading
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class TechnicalIndicators:
    """Technical indicators calculator"""

    @staticmethod
    def prepare_dataframe(klines: List[List]) -> pd.DataFrame:
        """
        Convert klines data to pandas DataFrame

        Args:
            klines: List of kline data from exchange API

        Returns:
            DataFrame with OHLCV data
        """
        if not klines:
            return pd.DataFrame()

        # Handle different exchange formats
        # OKX: [timestamp, open, high, low, close, volume, volCcy, volCcyQuote, confirm]
        # Binance: [timestamp, open, high, low, close, volume, ...]

        # Extract only the first 6 columns we need: timestamp, open, high, low, close, volume
        processed_klines = []
        for kline in klines:
            if len(kline) >= 6:
                processed_klines.append(kline[:6])
            else:
                # Skip incomplete data
                continue

        if not processed_klines:
            return pd.DataFrame()

        df = pd.DataFrame(processed_klines, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        # Convert to numeric
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])

        return df.sort_index()

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line

        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Bollinger Bands"""
        sma = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()

        return {"upper": sma + (std * std_dev), "middle": sma, "lower": sma - (std * std_dev)}

    @staticmethod
    def stochastic(
        high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3
    ) -> Dict[str, pd.Series]:
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()

        return {"k": k_percent, "d": d_percent}

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()

    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        return -100 * ((highest_high - close) / (highest_high - lowest_low))

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Commodity Channel Index"""
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

        return (typical_price - sma_tp) / (0.015 * mean_deviation)

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]

        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i - 1]

        return obv

    @staticmethod
    def pivot_levels(high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, float]:
        """Calculate classic pivot point levels from the latest session"""
        if len(high) == 0:
            return {}

        recent_high = high.iloc[-1]
        recent_low = low.iloc[-1]
        recent_close = close.iloc[-1]

        pivot = (recent_high + recent_low + recent_close) / 3
        r1 = 2 * pivot - recent_low
        s1 = 2 * pivot - recent_high
        r2 = pivot + (recent_high - recent_low)
        s2 = pivot - (recent_high - recent_low)

        return {"pivot": pivot, "r1": r1, "r2": r2, "s1": s1, "s2": s2}

    @staticmethod
    def volume_profile_levels(df: pd.DataFrame, bins: int = 24) -> List[float]:
        """Approximate high-volume price levels using volume profile"""
        if df.empty or df["high"].max() == df["low"].min():
            return []

        price_min = df["low"].min()
        price_max = df["high"].max()
        bin_edges = np.linspace(price_min, price_max, bins + 1)
        volume_distribution = np.zeros(bins)

        for _, row in df.iterrows():
            typical_price = (row["high"] + row["low"] + row["close"]) / 3
            idx = np.searchsorted(bin_edges, typical_price, side="right") - 1
            idx = max(0, min(idx, bins - 1))
            volume_distribution[idx] += row["volume"]

        top_indices = volume_distribution.argsort()[::-1][:5]
        levels = []
        for idx in top_indices:
            level = (bin_edges[idx] + bin_edges[idx + 1]) / 2
            levels.append(level)

        return levels

    @classmethod
    def support_resistance(cls, df: pd.DataFrame, window: int = 20, bins: int = 24) -> Dict[str, List[float]]:
        """Combine multiple methods to find support and resistance levels"""
        if df.empty:
            return {"support": [], "resistance": []}

        closes = df["close"]
        highs = df["high"]
        lows = df["low"]

        rolling_resistance = []
        rolling_support = []
        if len(closes) >= window * 2:
            highs_roll = closes.rolling(window=window, center=True).max()
            lows_roll = closes.rolling(window=window, center=True).min()

            for i in range(window, len(closes) - window):
                if closes.iloc[i] == highs_roll.iloc[i]:
                    rolling_resistance.append(closes.iloc[i])
                if closes.iloc[i] == lows_roll.iloc[i]:
                    rolling_support.append(closes.iloc[i])

        pivot_data = cls.pivot_levels(highs, lows, closes)
        volume_nodes = cls.volume_profile_levels(df, bins)

        support_levels: List[float] = []
        resistance_levels: List[float] = []

        pivot_point = pivot_data.get("pivot") if pivot_data else None

        if pivot_data:
            support_levels.extend([pivot_data.get("s1"), pivot_data.get("s2")])
            resistance_levels.extend([pivot_data.get("r1"), pivot_data.get("r2")])

        support_levels.extend(rolling_support)
        resistance_levels.extend(rolling_resistance)

        # Split volume nodes around latest close
        if volume_nodes:
            last_close = closes.iloc[-1]
            for level in volume_nodes:
                if level <= last_close:
                    support_levels.append(level)
                else:
                    resistance_levels.append(level)

        support_clean = sorted({level for level in support_levels if level is not None})[:5]
        resistance_clean = sorted({level for level in resistance_levels if level is not None}, reverse=True)[:5]
        volume_clean = sorted({level for level in volume_nodes if level is not None})[:5]

        return {
            "support": support_clean,
            "resistance": resistance_clean,
            "pivot": pivot_point,
            "volume_nodes": volume_clean,
        }

    @classmethod
    def calculate_all_indicators(
        cls,
        klines: List[List],
        sr_window: int = 20,
        volume_bins: int = 24,
    ) -> Dict[str, Any]:
        """
        Calculate all technical indicators for given klines data

        Args:
            klines: List of kline data

        Returns:
            Dictionary containing all calculated indicators
        """
        if not klines:
            return {}

        df = cls.prepare_dataframe(klines)
        if df.empty:
            return {}

        indicators = {}

        try:
            # Helper function to safely get last value
            def safe_get_last(series_or_value):
                if hasattr(series_or_value, "iloc"):
                    return series_or_value.iloc[-1]
                return series_or_value

            # Moving Averages
            if len(df) >= 20:
                sma_20 = cls.sma(df["close"], 20)
                indicators["sma_20"] = safe_get_last(sma_20)
            else:
                indicators["sma_20"] = None

            if len(df) >= 50:
                sma_50 = cls.sma(df["close"], 50)
                indicators["sma_50"] = safe_get_last(sma_50)
            else:
                indicators["sma_50"] = None

            if len(df) >= 12:
                ema_12 = cls.ema(df["close"], 12)
                indicators["ema_12"] = safe_get_last(ema_12)
            else:
                indicators["ema_12"] = None

            if len(df) >= 26:
                ema_26 = cls.ema(df["close"], 26)
                indicators["ema_26"] = safe_get_last(ema_26)
            else:
                indicators["ema_26"] = None

            # RSI
            if len(df) >= 14:
                rsi_values = cls.rsi(df["close"], 14)
                indicators["rsi"] = safe_get_last(rsi_values)
            else:
                indicators["rsi"] = None

            # MACD
            if len(df) >= 26:
                macd_data = cls.macd(df["close"])
                indicators["macd"] = {
                    "macd": safe_get_last(macd_data["macd"]),
                    "signal": safe_get_last(macd_data["signal"]),
                    "histogram": safe_get_last(macd_data["histogram"]),
                }
            else:
                indicators["macd"] = None

            # Bollinger Bands
            if len(df) >= 20:
                bb_data = cls.bollinger_bands(df["close"])
                indicators["bollinger_bands"] = {
                    "upper": safe_get_last(bb_data["upper"]),
                    "middle": safe_get_last(bb_data["middle"]),
                    "lower": safe_get_last(bb_data["lower"]),
                }
            else:
                indicators["bollinger_bands"] = None

            # Stochastic
            if len(df) >= 14:
                stoch_data = cls.stochastic(df["high"], df["low"], df["close"])
                indicators["stochastic"] = {"k": safe_get_last(stoch_data["k"]), "d": safe_get_last(stoch_data["d"])}
            else:
                indicators["stochastic"] = None

            # ATR
            if len(df) >= 14:
                atr_values = cls.atr(df["high"], df["low"], df["close"])
                indicators["atr"] = safe_get_last(atr_values)
            else:
                indicators["atr"] = None

            # Williams %R
            if len(df) >= 14:
                williams_r_values = cls.williams_r(df["high"], df["low"], df["close"])
                indicators["williams_r"] = safe_get_last(williams_r_values)
            else:
                indicators["williams_r"] = None

            # Support and Resistance
            if len(df) >= sr_window * 2:
                sr_levels = cls.support_resistance(df, window=sr_window, bins=volume_bins)
                indicators["support_resistance"] = sr_levels
            else:
                indicators["support_resistance"] = None

            # Current price info
            indicators["current_price"] = safe_get_last(df["close"])
            indicators["volume"] = safe_get_last(df["volume"])
            indicators["high_24h"] = df["high"].max()
            indicators["low_24h"] = df["low"].min()

        except Exception as e:
            indicators["error"] = f"Error calculating indicators: {str(e)}"

        return indicators

    @classmethod
    def get_trading_signals(cls, indicators: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate trading signals based on technical indicators

        Args:
            indicators: Dictionary of calculated indicators

        Returns:
            Dictionary of trading signals
        """
        signals = {}

        try:
            # RSI signals
            if "rsi" in indicators and indicators["rsi"] is not None:
                rsi = indicators["rsi"]
                if rsi > 70:
                    signals["rsi"] = "SELL"
                elif rsi < 30:
                    signals["rsi"] = "BUY"
                else:
                    signals["rsi"] = "HOLD"

            # MACD signals
            if "macd" in indicators and indicators["macd"] is not None:
                macd_data = indicators["macd"]
                if macd_data["macd"] > macd_data["signal"]:
                    signals["macd"] = "BUY"
                else:
                    signals["macd"] = "SELL"

            # Bollinger Bands signals
            if "bollinger_bands" in indicators and "current_price" in indicators:
                bb = indicators["bollinger_bands"]
                price = indicators["current_price"]

                if price > bb["upper"]:
                    signals["bollinger_bands"] = "SELL"
                elif price < bb["lower"]:
                    signals["bollinger_bands"] = "BUY"
                else:
                    signals["bollinger_bands"] = "HOLD"

            # Stochastic signals
            if "stochastic" in indicators:
                stoch = indicators["stochastic"]
                if stoch["k"] > 80:
                    signals["stochastic"] = "SELL"
                elif stoch["k"] < 20:
                    signals["stochastic"] = "BUY"
                else:
                    signals["stochastic"] = "HOLD"

            # Overall signal (simple majority vote)
            buy_signals = sum(1 for signal in signals.values() if signal == "BUY")
            sell_signals = sum(1 for signal in signals.values() if signal == "SELL")

            if buy_signals > sell_signals:
                signals["overall"] = "BUY"
            elif sell_signals > buy_signals:
                signals["overall"] = "SELL"
            else:
                signals["overall"] = "HOLD"

        except Exception as e:
            signals["error"] = f"Error generating signals: {str(e)}"

        return signals
