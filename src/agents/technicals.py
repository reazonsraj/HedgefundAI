import math

from langchain_core.messages import HumanMessage

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.api_key import get_api_key_from_state
import json
import pandas as pd
import numpy as np

from src.tools.api import get_prices, prices_to_df
from src.utils.progress import progress


def safe_float(value, default=0.0):
    """
    Safely convert a value to float, handling NaN cases
    
    Args:
        value: The value to convert (can be pandas scalar, numpy value, etc.)
        default: Default value to return if the input is NaN or invalid
    
    Returns:
        float: The converted value or default if NaN/invalid
    """
    try:
        if pd.isna(value) or np.isnan(value):
            return default
        return float(value)
    except (ValueError, TypeError, OverflowError):
        return default


##### Technical Analyst #####
def technical_analyst_agent(state: AgentState, agent_id: str = "technical_analyst_agent"):
    """
    Sophisticated technical analysis system that combines multiple trading strategies for multiple tickers:
    1. Trend Following
    2. Mean Reversion
    3. Momentum
    4. Volatility Analysis
    5. Statistical Arbitrage Signals
    """
    data = state["data"]
    start_date = data["start_date"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
    # Initialize analysis for each ticker
    technical_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Analyzing price data")

        # Get the historical price data
        prices = get_prices(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            api_key=api_key,
        )

        if not prices:
            progress.update_status(agent_id, ticker, "Failed: No price data found")
            continue

        # Convert prices to a DataFrame
        prices_df = prices_to_df(prices)

        progress.update_status(agent_id, ticker, "Calculating trend signals")
        trend_signals = calculate_trend_signals(prices_df)

        progress.update_status(agent_id, ticker, "Calculating mean reversion")
        mean_reversion_signals = calculate_mean_reversion_signals(prices_df)

        progress.update_status(agent_id, ticker, "Calculating momentum")
        momentum_signals = calculate_momentum_signals(prices_df)

        progress.update_status(agent_id, ticker, "Analyzing volatility")
        volatility_signals = calculate_volatility_signals(prices_df)

        progress.update_status(agent_id, ticker, "Statistical analysis")
        stat_arb_signals = calculate_stat_arb_signals(prices_df)

        progress.update_status(agent_id, ticker, "Calculating MACD signals")
        macd_signals = calculate_macd_signals(prices_df)

        # Combine all signals using a weighted ensemble approach
        # Weights: trend 20%, mean_reversion 18%, momentum 20%, volatility 12%, stat_arb 15%, macd 15%
        strategy_weights = {
            "trend": 0.20,
            "mean_reversion": 0.18,
            "momentum": 0.20,
            "volatility": 0.12,
            "stat_arb": 0.15,
            "macd": 0.15,
        }

        progress.update_status(agent_id, ticker, "Combining signals")
        combined_signal = weighted_signal_combination(
            {
                "trend": trend_signals,
                "mean_reversion": mean_reversion_signals,
                "momentum": momentum_signals,
                "volatility": volatility_signals,
                "stat_arb": stat_arb_signals,
                "macd": macd_signals,
            },
            strategy_weights,
        )

        # Generate detailed analysis report for this ticker
        technical_analysis[ticker] = {
            "signal": combined_signal["signal"],
            "confidence": round(combined_signal["confidence"] * 100),
            "reasoning": {
                "trend_following": {
                    "signal": trend_signals["signal"],
                    "confidence": round(trend_signals["confidence"] * 100),
                    "metrics": normalize_pandas(trend_signals["metrics"]),
                },
                "mean_reversion": {
                    "signal": mean_reversion_signals["signal"],
                    "confidence": round(mean_reversion_signals["confidence"] * 100),
                    "metrics": normalize_pandas(mean_reversion_signals["metrics"]),
                },
                "momentum": {
                    "signal": momentum_signals["signal"],
                    "confidence": round(momentum_signals["confidence"] * 100),
                    "metrics": normalize_pandas(momentum_signals["metrics"]),
                },
                "volatility": {
                    "signal": volatility_signals["signal"],
                    "confidence": round(volatility_signals["confidence"] * 100),
                    "metrics": normalize_pandas(volatility_signals["metrics"]),
                },
                "statistical_arbitrage": {
                    "signal": stat_arb_signals["signal"],
                    "confidence": round(stat_arb_signals["confidence"] * 100),
                    "metrics": normalize_pandas(stat_arb_signals["metrics"]),
                },
                "macd": {
                    "signal": macd_signals["signal"],
                    "confidence": round(macd_signals["confidence"] * 100),
                    "metrics": normalize_pandas(macd_signals["metrics"]),
                },
            },
        }
        progress.update_status(agent_id, ticker, "Done", analysis=json.dumps(technical_analysis, indent=4))

    # Create the technical analyst message
    message = HumanMessage(
        content=json.dumps(technical_analysis),
        name=agent_id,
    )

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(technical_analysis, "Technical Analyst")

    # Add the signal to the analyst_signals list
    state["data"]["analyst_signals"][agent_id] = technical_analysis

    progress.update_status(agent_id, None, "Done")

    return {
        "messages": state["messages"] + [message],
        "data": data,
    }


def calculate_trend_signals(prices_df):
    """
    Advanced trend following strategy using multiple timeframes and indicators.
    Includes volume-weighted price confirmation: price moves must be backed by
    above-average volume to receive full confidence.
    """
    # Calculate EMAs for multiple timeframes
    ema_8 = calculate_ema(prices_df, 8)
    ema_21 = calculate_ema(prices_df, 21)
    ema_55 = calculate_ema(prices_df, 55)

    # Calculate ADX for trend strength
    adx = calculate_adx(prices_df, 14)

    # Determine trend direction and strength
    short_trend = ema_8 > ema_21
    medium_trend = ema_21 > ema_55

    # Volume-weighted price confirmation (VWAP-like check)
    # Price move on above-average volume is considered confirmed
    vol_ma_20 = prices_df["volume"].rolling(window=20).mean()
    current_volume = prices_df["volume"].iloc[-1]
    avg_volume = vol_ma_20.iloc[-1]
    volume_confirmed = (current_volume > avg_volume) if (avg_volume > 0) else False
    volume_ratio = safe_float(current_volume / avg_volume) if (avg_volume > 0) else 1.0

    # Combine signals with confidence weighting
    trend_strength = adx["adx"].iloc[-1] / 100.0

    # Reduce confidence by 20 % when volume does not confirm the move
    volume_multiplier = 1.0 if volume_confirmed else 0.8

    if short_trend.iloc[-1] and medium_trend.iloc[-1]:
        signal = "bullish"
        confidence = trend_strength * volume_multiplier
    elif not short_trend.iloc[-1] and not medium_trend.iloc[-1]:
        signal = "bearish"
        confidence = trend_strength * volume_multiplier
    else:
        signal = "neutral"
        confidence = 0.5

    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "adx": safe_float(adx["adx"].iloc[-1]),
            "trend_strength": safe_float(trend_strength),
            "volume_ratio": safe_float(volume_ratio),
            "volume_confirmed": int(volume_confirmed),
        },
    }


def calculate_mean_reversion_signals(prices_df):
    """
    Mean reversion strategy using statistical measures, Bollinger Bands,
    and Stochastic RSI as an additional confirmation signal.
    """
    # Calculate z-score of price relative to moving average
    ma_50 = prices_df["close"].rolling(window=50).mean()
    std_50 = prices_df["close"].rolling(window=50).std()
    z_score = (prices_df["close"] - ma_50) / std_50

    # Calculate Bollinger Bands
    bb_upper, bb_lower = calculate_bollinger_bands(prices_df)

    # Calculate RSI with multiple timeframes
    rsi_14 = calculate_rsi(prices_df, 14)
    rsi_28 = calculate_rsi(prices_df, 28)

    # Stochastic RSI — additional confirmation signal
    stoch_rsi = calculate_stoch_rsi(prices_df, 14)
    stoch_rsi_val = safe_float(stoch_rsi.iloc[-1], default=0.5)

    # Mean reversion signals
    price_vs_bb = (prices_df["close"].iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])

    # Stoch RSI confirmation: oversold (<0.2) confirms bullish, overbought (>0.8) confirms bearish
    stoch_confirms_bullish = stoch_rsi_val < 0.2
    stoch_confirms_bearish = stoch_rsi_val > 0.8

    # Combine signals — Stoch RSI boosts confidence by up to 20 % when confirming
    if z_score.iloc[-1] < -2 and price_vs_bb < 0.2:
        signal = "bullish"
        base_conf = min(abs(z_score.iloc[-1]) / 4, 1.0)
        confidence = min(base_conf * (1.2 if stoch_confirms_bullish else 1.0), 1.0)
    elif z_score.iloc[-1] > 2 and price_vs_bb > 0.8:
        signal = "bearish"
        base_conf = min(abs(z_score.iloc[-1]) / 4, 1.0)
        confidence = min(base_conf * (1.2 if stoch_confirms_bearish else 1.0), 1.0)
    else:
        signal = "neutral"
        confidence = 0.5

    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "z_score": safe_float(z_score.iloc[-1]),
            "price_vs_bb": safe_float(price_vs_bb),
            "rsi_14": safe_float(rsi_14.iloc[-1]),
            "rsi_28": safe_float(rsi_28.iloc[-1]),
            "stoch_rsi": stoch_rsi_val,
        },
    }


def calculate_momentum_signals(prices_df):
    """
    Multi-factor momentum strategy.
    Includes Rate of Change (ROC) for 5-day and 10-day periods alongside
    the existing 1m / 3m / 6m rolling returns.
    """
    # Price momentum (rolling cumulative returns)
    returns = prices_df["close"].pct_change()
    mom_1m = returns.rolling(21).sum()
    mom_3m = returns.rolling(63).sum()
    mom_6m = returns.rolling(126).sum()

    # Short-term Rate of Change (ROC) — percentage change over N periods
    # ROC = (close_t / close_{t-n} - 1) * 100
    roc_5 = prices_df["close"].pct_change(periods=5) * 100
    roc_10 = prices_df["close"].pct_change(periods=10) * 100

    # Volume momentum
    volume_ma = prices_df["volume"].rolling(21).mean()
    volume_momentum = prices_df["volume"] / volume_ma

    # Relative strength
    # (would compare to market/sector in real implementation)

    # Calculate momentum score — ROC signals blend with longer-term momentum
    momentum_score = (
        0.3 * mom_1m
        + 0.25 * mom_3m
        + 0.25 * mom_6m
        + 0.1 * (roc_5 / 100)   # normalise ROC back to decimal
        + 0.1 * (roc_10 / 100)
    ).iloc[-1]

    # Volume confirmation
    volume_confirmation = volume_momentum.iloc[-1] > 1.0

    if momentum_score > 0.05 and volume_confirmation:
        signal = "bullish"
        confidence = min(abs(momentum_score) * 5, 1.0)
    elif momentum_score < -0.05 and volume_confirmation:
        signal = "bearish"
        confidence = min(abs(momentum_score) * 5, 1.0)
    else:
        signal = "neutral"
        confidence = 0.5

    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "momentum_1m": safe_float(mom_1m.iloc[-1]),
            "momentum_3m": safe_float(mom_3m.iloc[-1]),
            "momentum_6m": safe_float(mom_6m.iloc[-1]),
            "roc_5": safe_float(roc_5.iloc[-1]),
            "roc_10": safe_float(roc_10.iloc[-1]),
            "volume_momentum": safe_float(volume_momentum.iloc[-1]),
        },
    }


def calculate_volatility_signals(prices_df):
    """
    Volatility-based trading strategy
    """
    # Calculate various volatility metrics
    returns = prices_df["close"].pct_change()

    # Historical volatility
    hist_vol = returns.rolling(21).std() * math.sqrt(252)

    # Volatility regime detection
    vol_ma = hist_vol.rolling(63).mean()
    vol_regime = hist_vol / vol_ma

    # Volatility mean reversion
    vol_z_score = (hist_vol - vol_ma) / hist_vol.rolling(63).std()

    # ATR ratio
    atr = calculate_atr(prices_df)
    atr_ratio = atr / prices_df["close"]

    # Generate signal based on volatility regime
    current_vol_regime = vol_regime.iloc[-1]
    vol_z = vol_z_score.iloc[-1]

    if current_vol_regime < 0.8 and vol_z < -1:
        signal = "bullish"  # Low vol regime, potential for expansion
        confidence = min(abs(vol_z) / 3, 1.0)
    elif current_vol_regime > 1.2 and vol_z > 1:
        signal = "bearish"  # High vol regime, potential for contraction
        confidence = min(abs(vol_z) / 3, 1.0)
    else:
        signal = "neutral"
        confidence = 0.5

    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "historical_volatility": safe_float(hist_vol.iloc[-1]),
            "volatility_regime": safe_float(current_vol_regime),
            "volatility_z_score": safe_float(vol_z),
            "atr_ratio": safe_float(atr_ratio.iloc[-1]),
        },
    }


def calculate_stat_arb_signals(prices_df):
    """
    Statistical arbitrage signals based on price action analysis
    """
    # Calculate price distribution statistics
    returns = prices_df["close"].pct_change()

    # Skewness and kurtosis
    skew = returns.rolling(63).skew()
    kurt = returns.rolling(63).kurt()

    # Test for mean reversion using Hurst exponent
    hurst = calculate_hurst_exponent(prices_df["close"])

    # Correlation analysis
    # (would include correlation with related securities in real implementation)

    # Generate signal based on statistical properties
    if hurst < 0.4 and skew.iloc[-1] > 1:
        signal = "bullish"
        confidence = (0.5 - hurst) * 2
    elif hurst < 0.4 and skew.iloc[-1] < -1:
        signal = "bearish"
        confidence = (0.5 - hurst) * 2
    else:
        signal = "neutral"
        confidence = 0.5

    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "hurst_exponent": safe_float(hurst),
            "skewness": safe_float(skew.iloc[-1]),
            "kurtosis": safe_float(kurt.iloc[-1]),
        },
    }


def calculate_macd_signals(prices_df):
    """
    MACD strategy using the classic (12, 26, 9) parameters.

    Bullish when:  MACD line is above the signal line AND both are rising.
    Bearish when:  MACD line is below the signal line AND both are falling.
    Confidence is scaled by the absolute histogram magnitude relative to
    recent histogram range so that larger divergences carry higher confidence.
    """
    macd_data = calculate_macd(prices_df)
    macd_line = macd_data["macd"]
    signal_line = macd_data["signal_line"]
    histogram = macd_data["histogram"]

    # Current and previous values for "rising" check
    macd_cur = macd_line.iloc[-1]
    macd_prev = macd_line.iloc[-2] if len(macd_line) >= 2 else macd_cur
    sig_cur = signal_line.iloc[-1]
    sig_prev = signal_line.iloc[-2] if len(signal_line) >= 2 else sig_cur
    hist_cur = histogram.iloc[-1]

    macd_rising = macd_cur > macd_prev
    signal_rising = sig_cur > sig_prev
    macd_above_signal = macd_cur > sig_cur

    # Scale confidence by histogram magnitude vs recent 26-bar range
    hist_range = histogram.rolling(26).apply(lambda x: x.max() - x.min(), raw=True).iloc[-1]
    if hist_range and hist_range > 0:
        hist_magnitude = min(abs(hist_cur) / (hist_range / 2), 1.0)
    else:
        hist_magnitude = 0.5

    if macd_above_signal and macd_rising and signal_rising:
        signal = "bullish"
        confidence = hist_magnitude
    elif not macd_above_signal and not macd_rising and not signal_rising:
        signal = "bearish"
        confidence = hist_magnitude
    else:
        signal = "neutral"
        confidence = 0.5

    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "macd": safe_float(macd_cur),
            "macd_signal": safe_float(sig_cur),
            "macd_histogram": safe_float(hist_cur),
            "macd_rising": int(macd_rising),
            "signal_rising": int(signal_rising),
        },
    }


def weighted_signal_combination(signals, weights):
    """
    Combines multiple trading signals using a weighted approach
    """
    # Convert signals to numeric values
    signal_values = {"bullish": 1, "neutral": 0, "bearish": -1}

    weighted_sum = 0
    total_confidence = 0

    for strategy, signal in signals.items():
        numeric_signal = signal_values[signal["signal"]]
        weight = weights[strategy]
        confidence = signal["confidence"]

        weighted_sum += numeric_signal * weight * confidence
        total_confidence += weight * confidence

    # Normalize the weighted sum
    if total_confidence > 0:
        final_score = weighted_sum / total_confidence
    else:
        final_score = 0

    # Convert back to signal
    if final_score > 0.2:
        signal = "bullish"
    elif final_score < -0.2:
        signal = "bearish"
    else:
        signal = "neutral"

    return {"signal": signal, "confidence": abs(final_score)}


def normalize_pandas(obj):
    """Convert pandas Series/DataFrames to primitive Python types"""
    if isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict("records")
    elif isinstance(obj, dict):
        return {k: normalize_pandas(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [normalize_pandas(item) for item in obj]
    return obj


def calculate_rsi(prices_df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = prices_df["close"].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(prices_df: pd.DataFrame, window: int = 20) -> tuple[pd.Series, pd.Series]:
    sma = prices_df["close"].rolling(window).mean()
    std_dev = prices_df["close"].rolling(window).std()
    upper_band = sma + (std_dev * 2)
    lower_band = sma - (std_dev * 2)
    return upper_band, lower_band


def calculate_ema(df: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculate Exponential Moving Average

    Args:
        df: DataFrame with price data
        window: EMA period

    Returns:
        pd.Series: EMA values
    """
    return df["close"].ewm(span=window, adjust=False).mean()


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average Directional Index (ADX)

    Args:
        df: DataFrame with OHLC data
        period: Period for calculations

    Returns:
        DataFrame with ADX values
    """
    # Calculate True Range
    df["high_low"] = df["high"] - df["low"]
    df["high_close"] = abs(df["high"] - df["close"].shift())
    df["low_close"] = abs(df["low"] - df["close"].shift())
    df["tr"] = df[["high_low", "high_close", "low_close"]].max(axis=1)

    # Calculate Directional Movement
    df["up_move"] = df["high"] - df["high"].shift()
    df["down_move"] = df["low"].shift() - df["low"]

    df["plus_dm"] = np.where((df["up_move"] > df["down_move"]) & (df["up_move"] > 0), df["up_move"], 0)
    df["minus_dm"] = np.where((df["down_move"] > df["up_move"]) & (df["down_move"] > 0), df["down_move"], 0)

    # Calculate ADX
    df["+di"] = 100 * (df["plus_dm"].ewm(span=period).mean() / df["tr"].ewm(span=period).mean())
    df["-di"] = 100 * (df["minus_dm"].ewm(span=period).mean() / df["tr"].ewm(span=period).mean())
    df["dx"] = 100 * abs(df["+di"] - df["-di"]) / (df["+di"] + df["-di"])
    df["adx"] = df["dx"].ewm(span=period).mean()

    return df[["adx", "+di", "-di"]]


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range

    Args:
        df: DataFrame with OHLC data
        period: Period for ATR calculation

    Returns:
        pd.Series: ATR values
    """
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())

    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)

    return true_range.rolling(period).mean()


def calculate_macd(prices_df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        prices_df: DataFrame with close prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)

    Returns:
        dict with 'macd', 'signal_line', and 'histogram' as pd.Series
    """
    ema_fast = prices_df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = prices_df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal_line": signal_line, "histogram": histogram}


def calculate_stoch_rsi(prices_df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Stochastic RSI — RSI normalised to 0-1 over the last `period` bars.

    Args:
        prices_df: DataFrame with close prices
        period: Lookback period (default 14)

    Returns:
        pd.Series: Stochastic RSI values in [0, 1]
    """
    rsi = calculate_rsi(prices_df, period)
    rsi_min = rsi.rolling(window=period).min()
    rsi_max = rsi.rolling(window=period).max()
    denom = rsi_max - rsi_min
    stoch_rsi = (rsi - rsi_min) / denom.where(denom != 0, other=np.nan)
    return stoch_rsi.fillna(0.5)


def calculate_hurst_exponent(price_series: pd.Series, max_lag: int = 20) -> float:
    """
    Calculate Hurst Exponent using the R/S (rescaled range) method.
    H < 0.5: Mean reverting series
    H = 0.5: Random walk
    H > 0.5: Trending series

    Args:
        price_series: Array-like price data
        max_lag: Maximum lag for R/S calculation

    Returns:
        float: Hurst exponent
    """
    prices = np.array(price_series.dropna())
    if len(prices) < max_lag * 2:
        return 0.5  # default to random walk
    log_prices = np.log(prices)
    lags = range(2, max_lag)
    rs_values = []
    for lag in lags:
        segments = len(log_prices) // lag
        if segments < 1:
            continue
        rs_list = []
        for i in range(segments):
            segment = log_prices[i * lag:(i + 1) * lag]
            mean_adj = segment - np.mean(segment)
            cumdev = np.cumsum(mean_adj)
            r = np.max(cumdev) - np.min(cumdev)
            s = np.std(segment, ddof=1)
            if s > 0:
                rs_list.append(r / s)
        if rs_list:
            rs_values.append((np.log(lag), np.log(np.mean(rs_list))))
    if len(rs_values) < 2:
        return 0.5
    x, y = zip(*rs_values)
    slope, _ = np.polyfit(x, y, 1)
    return max(0.0, min(1.0, slope))
