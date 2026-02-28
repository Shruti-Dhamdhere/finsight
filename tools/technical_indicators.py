import pandas as pd
import numpy as np
import config

def calculate_indicators(price_history: pd.DataFrame) -> dict:
    """
    Calculate technical indicators from price history.
    Uses same logic as FinRL academic trading framework.
    """
    print(f"  [Technical Agent] Calculating indicators...")
    
    try:
        df = price_history.copy()
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        # ─── RSI ──────────────────────────────────────────────
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(config.RSI_PERIOD).mean()
        loss = -delta.where(delta < 0, 0).rolling(config.RSI_PERIOD).mean()
        rs = gain / loss
        rsi = round(float(100 - (100 / (1 + rs.iloc[-1]))), 2)
        
        # ─── MACD ─────────────────────────────────────────────
        ema_fast = close.ewm(span=config.MACD_FAST).mean()
        ema_slow = close.ewm(span=config.MACD_SLOW).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=config.MACD_SIGNAL).mean()
        macd_histogram = macd_line - signal_line
        
        macd = round(float(macd_line.iloc[-1]), 4)
        macd_signal = round(float(signal_line.iloc[-1]), 4)
        macd_hist = round(float(macd_histogram.iloc[-1]), 4)
        
        # ─── Bollinger Bands ──────────────────────────────────
        bb_mid = close.rolling(config.BBANDS_PERIOD).mean()
        bb_std = close.rolling(config.BBANDS_PERIOD).std()
        bb_upper = bb_mid + (2 * bb_std)
        bb_lower = bb_mid - (2 * bb_std)
        
        current_price = close.iloc[-1]
        bb_position = round(float(
            (current_price - bb_lower.iloc[-1]) /
            (bb_upper.iloc[-1] - bb_lower.iloc[-1]) * 100
        ), 2)
        
        # ─── Moving Averages ──────────────────────────────────
        sma_20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
        sma_50 = round(float(close.rolling(50).mean().iloc[-1]), 2)
        sma_200 = round(float(close.rolling(200).mean().iloc[-1]), 2)
        ema_20 = round(float(close.ewm(span=20).mean().iloc[-1]), 2)
        
        # ─── Volume Analysis ──────────────────────────────────
        avg_volume_20 = volume.rolling(20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = round(float(current_volume / avg_volume_20), 2)
        
        # ─── Support & Resistance ─────────────────────────────
        recent_high = round(float(high.rolling(52).max().iloc[-1]), 2)
        recent_low = round(float(low.rolling(52).min().iloc[-1]), 2)
        
        # ─── Signal Interpretation ────────────────────────────
        signals = []
        
        # RSI signals
        if rsi < 30:
            signals.append({"indicator": "RSI", "signal": "BULLISH", 
                           "reason": f"Oversold at {rsi}"})
        elif rsi > 70:
            signals.append({"indicator": "RSI", "signal": "BEARISH", 
                           "reason": f"Overbought at {rsi}"})
        else:
            signals.append({"indicator": "RSI", "signal": "NEUTRAL", 
                           "reason": f"Neutral at {rsi}"})
        
        # MACD signals
        if macd_hist > 0 and macd > macd_signal:
            signals.append({"indicator": "MACD", "signal": "BULLISH",
                           "reason": "Positive histogram, MACD above signal"})
        elif macd_hist < 0 and macd < macd_signal:
            signals.append({"indicator": "MACD", "signal": "BEARISH",
                           "reason": "Negative histogram, MACD below signal"})
        else:
            signals.append({"indicator": "MACD", "signal": "NEUTRAL",
                           "reason": "Mixed MACD signals"})
        
        # Moving average signals
        if current_price > sma_200 and sma_50 > sma_200:
            signals.append({"indicator": "MA", "signal": "BULLISH",
                           "reason": "Price above 200 SMA, golden cross formation"})
        elif current_price < sma_200 and sma_50 < sma_200:
            signals.append({"indicator": "MA", "signal": "BEARISH",
                           "reason": "Price below 200 SMA, death cross formation"})
        else:
            signals.append({"indicator": "MA", "signal": "NEUTRAL",
                           "reason": "Mixed moving average signals"})
        
        # Bollinger Band signals
        if bb_position < 20:
            signals.append({"indicator": "BBANDS", "signal": "BULLISH",
                           "reason": f"Price near lower band ({bb_position}%)"})
        elif bb_position > 80:
            signals.append({"indicator": "BBANDS", "signal": "BEARISH",
                           "reason": f"Price near upper band ({bb_position}%)"})
        else:
            signals.append({"indicator": "BBANDS", "signal": "NEUTRAL",
                           "reason": f"Price mid-band ({bb_position}%)"})
        
        # ─── Overall Technical Score ──────────────────────────
        bullish_count = sum(1 for s in signals if s["signal"] == "BULLISH")
        bearish_count = sum(1 for s in signals if s["signal"] == "BEARISH")
        
        if bullish_count >= 3:
            overall_signal = "BULLISH"
        elif bearish_count >= 3:
            overall_signal = "BEARISH"
        else:
            overall_signal = "NEUTRAL"
        
        return {
            "rsi": rsi,
            "macd": {"macd": macd, "signal": macd_signal, "histogram": macd_hist},
            "bollinger_bands": {
                "upper": round(float(bb_upper.iloc[-1]), 2),
                "middle": round(float(bb_mid.iloc[-1]), 2),
                "lower": round(float(bb_lower.iloc[-1]), 2),
                "position_pct": bb_position
            },
            "moving_averages": {
                "sma_20": sma_20, "sma_50": sma_50,
                "sma_200": sma_200, "ema_20": ema_20
            },
            "volume": {
                "current": int(current_volume),
                "avg_20d": int(avg_volume_20),
                "ratio": volume_ratio
            },
            "support_resistance": {
                "52w_high": recent_high,
                "52w_low": recent_low
            },
            "signals": signals,
            "overall_signal": overall_signal,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "status": "success"
        }
        
    except Exception as e:
        return {"error": str(e), "status": "failed"}