"""
Technical indicators calculation module for crypto trading
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple


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
        
        df = pd.DataFrame(processed_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
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
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Bollinger Bands"""
        sma = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                   k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }
    
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
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )
        
        return (typical_price - sma_tp) / (0.015 * mean_deviation)
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    @staticmethod
    def support_resistance(data: pd.Series, window: int = 20) -> Dict[str, List[float]]:
        """Find support and resistance levels"""
        highs = data.rolling(window=window, center=True).max()
        lows = data.rolling(window=window, center=True).min()
        
        resistance_levels = []
        support_levels = []
        
        for i in range(window, len(data) - window):
            if data.iloc[i] == highs.iloc[i]:
                resistance_levels.append(data.iloc[i])
            if data.iloc[i] == lows.iloc[i]:
                support_levels.append(data.iloc[i])
        
        return {
            'resistance': sorted(list(set(resistance_levels)), reverse=True)[:5],
            'support': sorted(list(set(support_levels)))[:5]
        }
    
    @classmethod
    def calculate_all_indicators(cls, klines: List[List]) -> Dict[str, Any]:
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
            # Moving Averages
            indicators['sma_20'] = cls.sma(df['close'], 20).iloc[-1] if len(df) >= 20 else None
            indicators['sma_50'] = cls.sma(df['close'], 50).iloc[-1] if len(df) >= 50 else None
            indicators['ema_12'] = cls.ema(df['close'], 12).iloc[-1] if len(df) >= 12 else None
            indicators['ema_26'] = cls.ema(df['close'], 26).iloc[-1] if len(df) >= 26 else None
            
            # RSI
            if len(df) >= 14:
                rsi_values = cls.rsi(df['close'], 14)
                indicators['rsi'] = rsi_values.iloc[-1]
            
            # MACD
            if len(df) >= 26:
                macd_data = cls.macd(df['close'])
                indicators['macd'] = {
                    'macd': macd_data['macd'].iloc[-1],
                    'signal': macd_data['signal'].iloc[-1],
                    'histogram': macd_data['histogram'].iloc[-1]
                }
            
            # Bollinger Bands
            if len(df) >= 20:
                bb_data = cls.bollinger_bands(df['close'])
                indicators['bollinger_bands'] = {
                    'upper': bb_data['upper'].iloc[-1],
                    'middle': bb_data['middle'].iloc[-1],
                    'lower': bb_data['lower'].iloc[-1]
                }
            
            # Stochastic
            if len(df) >= 14:
                stoch_data = cls.stochastic(df['high'], df['low'], df['close'])
                indicators['stochastic'] = {
                    'k': stoch_data['k'].iloc[-1],
                    'd': stoch_data['d'].iloc[-1]
                }
            
            # ATR
            if len(df) >= 14:
                atr_values = cls.atr(df['high'], df['low'], df['close'])
                indicators['atr'] = atr_values.iloc[-1]
            
            # Williams %R
            if len(df) >= 14:
                williams_r_values = cls.williams_r(df['high'], df['low'], df['close'])
                indicators['williams_r'] = williams_r_values.iloc[-1]
            
            # Support and Resistance
            if len(df) >= 40:
                sr_levels = cls.support_resistance(df['close'])
                indicators['support_resistance'] = sr_levels
            
            # Current price info
            indicators['current_price'] = df['close'].iloc[-1]
            indicators['volume'] = df['volume'].iloc[-1]
            indicators['high_24h'] = df['high'].max()
            indicators['low_24h'] = df['low'].min()
            
        except Exception as e:
            indicators['error'] = f"Error calculating indicators: {str(e)}"
        
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
            if 'rsi' in indicators and indicators['rsi'] is not None:
                rsi = indicators['rsi']
                if rsi > 70:
                    signals['rsi'] = 'SELL'
                elif rsi < 30:
                    signals['rsi'] = 'BUY'
                else:
                    signals['rsi'] = 'HOLD'
            
            # MACD signals
            if 'macd' in indicators and indicators['macd'] is not None:
                macd_data = indicators['macd']
                if macd_data['macd'] > macd_data['signal']:
                    signals['macd'] = 'BUY'
                else:
                    signals['macd'] = 'SELL'
            
            # Bollinger Bands signals
            if 'bollinger_bands' in indicators and 'current_price' in indicators:
                bb = indicators['bollinger_bands']
                price = indicators['current_price']
                
                if price > bb['upper']:
                    signals['bollinger_bands'] = 'SELL'
                elif price < bb['lower']:
                    signals['bollinger_bands'] = 'BUY'
                else:
                    signals['bollinger_bands'] = 'HOLD'
            
            # Stochastic signals
            if 'stochastic' in indicators:
                stoch = indicators['stochastic']
                if stoch['k'] > 80:
                    signals['stochastic'] = 'SELL'
                elif stoch['k'] < 20:
                    signals['stochastic'] = 'BUY'
                else:
                    signals['stochastic'] = 'HOLD'
            
            # Overall signal (simple majority vote)
            buy_signals = sum(1 for signal in signals.values() if signal == 'BUY')
            sell_signals = sum(1 for signal in signals.values() if signal == 'SELL')
            
            if buy_signals > sell_signals:
                signals['overall'] = 'BUY'
            elif sell_signals > buy_signals:
                signals['overall'] = 'SELL'
            else:
                signals['overall'] = 'HOLD'
                
        except Exception as e:
            signals['error'] = f"Error generating signals: {str(e)}"
        
        return signals