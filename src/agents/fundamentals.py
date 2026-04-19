from langchain_core.messages import HumanMessage
from src.graph.state import AgentState, show_agent_reasoning
from src.utils.api_key import get_api_key_from_state
from src.utils.progress import progress
import json

from src.tools.api import get_financial_metrics


# ---------------------------------------------------------------------------
# Tiered scoring helpers
# ---------------------------------------------------------------------------

def _score_roe(v):
    """Return on Equity tiers (0-10)."""
    if v is None:
        return None
    if v < 0.05:   return 0
    if v < 0.10:   return 2
    if v < 0.15:   return 4
    if v < 0.25:   return 6
    if v < 0.40:   return 8
    return 10


def _score_net_margin(v):
    """Net margin tiers (0-10)."""
    if v is None:
        return None
    if v < 0:      return 0
    if v < 0.05:   return 2
    if v < 0.10:   return 4
    if v < 0.20:   return 6
    if v < 0.30:   return 8
    return 10


def _score_operating_margin(v):
    """Operating margin tiers (0-10) — same shape as net margin."""
    if v is None:
        return None
    if v < 0:      return 0
    if v < 0.05:   return 2
    if v < 0.10:   return 4
    if v < 0.20:   return 6
    if v < 0.30:   return 8
    return 10


def _score_roa(v):
    """Return on Assets tiers — shifted down vs ROE."""
    if v is None:
        return None
    if v < 0.02:   return 0
    if v < 0.05:   return 2
    if v < 0.08:   return 4
    if v < 0.12:   return 6
    if v < 0.20:   return 8
    return 10


def _score_roic(v):
    """Return on Invested Capital — same tiers as ROE."""
    return _score_roe(v)


def _score_fcf_yield(v):
    """Free cash flow yield tiers (0-10)."""
    if v is None:
        return None
    if v < 0:      return 0
    if v < 0.02:   return 2
    if v < 0.05:   return 4
    if v < 0.08:   return 6
    if v < 0.12:   return 8
    return 10


def _score_growth(v):
    """Generic growth metric tiers (revenue, earnings, etc.)."""
    if v is None:
        return None
    if v < 0:      return 0
    if v < 0.05:   return 2
    if v < 0.10:   return 4
    if v < 0.20:   return 6
    if v < 0.30:   return 8
    return 10


def _score_current_ratio(v):
    """Current ratio tiers (0-10)."""
    if v is None:
        return None
    if v < 0.5:    return 0
    if v < 1.0:    return 2
    if v < 1.5:    return 4
    if v < 2.0:    return 6
    if v < 3.0:    return 8
    return 10


def _score_debt_to_equity(v):
    """Debt / equity — lower is better (0-10)."""
    if v is None:
        return None
    if v > 3:      return 0
    if v > 2:      return 2
    if v > 1:      return 4
    if v > 0.5:    return 6
    if v > 0.2:    return 8
    return 10


def _score_pe(v):
    """P/E ratio tiers — lower is cheaper (0-10)."""
    if v is None:
        return None
    if v < 0:      return 0   # negative earnings
    if v > 50:     return 0
    if v > 30:     return 2
    if v > 20:     return 4
    if v > 15:     return 6
    if v > 10:     return 8
    return 10


def _score_pb(v):
    """P/B ratio tiers — lower is cheaper (0-10)."""
    if v is None:
        return None
    if v < 0:      return 0
    if v > 10:     return 0
    if v > 5:      return 2
    if v > 3:      return 4
    if v > 1.5:    return 6
    if v > 1:      return 8
    return 10


def _score_ps(v):
    """P/S ratio tiers — lower is cheaper (0-10)."""
    if v is None:
        return None
    if v < 0:      return 0
    if v > 10:     return 0
    if v > 5:      return 2
    if v > 3:      return 4
    if v > 1.5:    return 6
    if v > 0.5:    return 8
    return 10


def _avg(scores: list):
    """Average of non-None scores; returns None if no valid scores."""
    valid = [s for s in scores if s is not None]
    return sum(valid) / len(valid) if valid else None


def _trend_bonus(history: list, attr: str) -> int:
    """
    Given a list of FinancialMetrics (oldest → newest), compute whether the
    metric at `attr` is trending up (+1), down (-1), or flat (0).
    Requires at least 2 non-None data points.
    """
    values = [getattr(m, attr, None) for m in history]
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return 0
    # Simple linear regression slope sign
    n = len(values)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    numerator = sum((i - mean_x) * (values[i] - mean_y) for i in range(n))
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    if denominator == 0:
        return 0
    slope = numerator / denominator
    # Normalise slope relative to mean value to avoid scale distortion
    ref = abs(mean_y) if mean_y != 0 else 1e-9
    relative_slope = slope / ref
    if relative_slope > 0.02:
        return 1
    if relative_slope < -0.02:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Main agent
# ---------------------------------------------------------------------------

##### Fundamental Agent #####
def fundamentals_analyst_agent(state: AgentState, agent_id: str = "fundamentals_analyst_agent"):
    """Analyzes fundamental data and generates trading signals for multiple tickers."""
    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")

    fundamental_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Fetching financial metrics")

        # Fetch the last 4 quarters for trend analysis
        financial_metrics = get_financial_metrics(
            ticker=ticker,
            end_date=end_date,
            period="ttm",
            limit=4,
            api_key=api_key,
        )

        if not financial_metrics:
            progress.update_status(agent_id, ticker, "Failed: No financial metrics found")
            continue

        # Most recent quarter (index 0) + history ordered oldest → newest for trends
        metrics = financial_metrics[0]
        history = list(reversed(financial_metrics))  # oldest first

        reasoning = {}

        # ------------------------------------------------------------------
        # 1. PROFITABILITY  (weight 30%)
        # ------------------------------------------------------------------
        progress.update_status(agent_id, ticker, "Analyzing profitability")

        roe          = metrics.return_on_equity
        net_margin   = metrics.net_margin
        op_margin    = metrics.operating_margin
        roa          = metrics.return_on_assets
        roic         = metrics.return_on_invested_capital

        roe_score  = _score_roe(roe)
        nm_score   = _score_net_margin(net_margin)
        om_score   = _score_operating_margin(op_margin)
        roa_score  = _score_roa(roa)
        roic_score = _score_roic(roic)

        # Trend bonuses (clamp category score to 0-10 after bonus)
        roe_score  = None if roe_score  is None else max(0, min(10, roe_score  + _trend_bonus(history, "return_on_equity")))
        nm_score   = None if nm_score   is None else max(0, min(10, nm_score   + _trend_bonus(history, "net_margin")))
        om_score   = None if om_score   is None else max(0, min(10, om_score   + _trend_bonus(history, "operating_margin")))
        roa_score  = None if roa_score  is None else max(0, min(10, roa_score  + _trend_bonus(history, "return_on_assets")))
        roic_score = None if roic_score is None else max(0, min(10, roic_score + _trend_bonus(history, "return_on_invested_capital")))

        profitability_score = _avg([roe_score, nm_score, om_score, roa_score, roic_score])

        reasoning["profitability"] = {
            "score": round(profitability_score, 2) if profitability_score is not None else None,
            "metrics": {
                "roe":              {"value": f"{roe:.2%}"       if roe          is not None else "N/A", "score": roe_score},
                "net_margin":       {"value": f"{net_margin:.2%}" if net_margin  is not None else "N/A", "score": nm_score},
                "operating_margin": {"value": f"{op_margin:.2%}" if op_margin    is not None else "N/A", "score": om_score},
                "roa":              {"value": f"{roa:.2%}"       if roa          is not None else "N/A", "score": roa_score},
                "roic":             {"value": f"{roic:.2%}"      if roic         is not None else "N/A", "score": roic_score},
            },
        }

        # ------------------------------------------------------------------
        # 2. GROWTH  (weight 20%)
        # ------------------------------------------------------------------
        progress.update_status(agent_id, ticker, "Analyzing growth")

        rev_growth  = metrics.revenue_growth
        earn_growth = metrics.earnings_growth

        rev_score  = _score_growth(rev_growth)
        earn_score = _score_growth(earn_growth)

        rev_score  = None if rev_score  is None else max(0, min(10, rev_score  + _trend_bonus(history, "revenue_growth")))
        earn_score = None if earn_score is None else max(0, min(10, earn_score + _trend_bonus(history, "earnings_growth")))

        growth_score = _avg([rev_score, earn_score])

        reasoning["growth"] = {
            "score": round(growth_score, 2) if growth_score is not None else None,
            "metrics": {
                "revenue_growth":  {"value": f"{rev_growth:.2%}"  if rev_growth  is not None else "N/A", "score": rev_score},
                "earnings_growth": {"value": f"{earn_growth:.2%}" if earn_growth is not None else "N/A", "score": earn_score},
            },
        }

        # ------------------------------------------------------------------
        # 3. FINANCIAL HEALTH  (weight 20%)
        # ------------------------------------------------------------------
        progress.update_status(agent_id, ticker, "Analyzing financial health")

        current_ratio  = metrics.current_ratio
        debt_to_equity = metrics.debt_to_equity
        fcf_yield      = metrics.free_cash_flow_yield

        cr_score  = _score_current_ratio(current_ratio)
        de_score  = _score_debt_to_equity(debt_to_equity)
        fcf_score = _score_fcf_yield(fcf_yield)

        cr_score  = None if cr_score  is None else max(0, min(10, cr_score  + _trend_bonus(history, "current_ratio")))
        de_score  = None if de_score  is None else max(0, min(10, de_score  + _trend_bonus(history, "debt_to_equity")))
        fcf_score = None if fcf_score is None else max(0, min(10, fcf_score + _trend_bonus(history, "free_cash_flow_yield")))

        health_score = _avg([cr_score, de_score, fcf_score])

        reasoning["financial_health"] = {
            "score": round(health_score, 2) if health_score is not None else None,
            "metrics": {
                "current_ratio":  {"value": f"{current_ratio:.2f}"  if current_ratio  is not None else "N/A", "score": cr_score},
                "debt_to_equity": {"value": f"{debt_to_equity:.2f}" if debt_to_equity is not None else "N/A", "score": de_score},
                "fcf_yield":      {"value": f"{fcf_yield:.2%}"      if fcf_yield      is not None else "N/A", "score": fcf_score},
            },
        }

        # ------------------------------------------------------------------
        # 4. VALUATION  (weight 30%)
        # ------------------------------------------------------------------
        progress.update_status(agent_id, ticker, "Analyzing valuation ratios")

        pe_ratio = metrics.price_to_earnings_ratio
        pb_ratio = metrics.price_to_book_ratio
        ps_ratio = metrics.price_to_sales_ratio

        pe_score = _score_pe(pe_ratio)
        pb_score = _score_pb(pb_ratio)
        ps_score = _score_ps(ps_ratio)

        pe_score = None if pe_score is None else max(0, min(10, pe_score + _trend_bonus(history, "price_to_earnings_ratio")))
        pb_score = None if pb_score is None else max(0, min(10, pb_score + _trend_bonus(history, "price_to_book_ratio")))
        ps_score = None if ps_score is None else max(0, min(10, ps_score + _trend_bonus(history, "price_to_sales_ratio")))

        valuation_score = _avg([pe_score, pb_score, ps_score])

        reasoning["valuation"] = {
            "score": round(valuation_score, 2) if valuation_score is not None else None,
            "metrics": {
                "pe_ratio": {"value": f"{pe_ratio:.2f}" if pe_ratio is not None else "N/A", "score": pe_score},
                "pb_ratio": {"value": f"{pb_ratio:.2f}" if pb_ratio is not None else "N/A", "score": pb_score},
                "ps_ratio": {"value": f"{ps_ratio:.2f}" if ps_ratio is not None else "N/A", "score": ps_score},
            },
        }

        # ------------------------------------------------------------------
        # 5. WEIGHTED FINAL SCORE
        # ------------------------------------------------------------------
        progress.update_status(agent_id, ticker, "Calculating final signal")

        weights = {
            "profitability": (profitability_score, 0.30),
            "growth":        (growth_score,        0.20),
            "health":        (health_score,         0.20),
            "valuation":     (valuation_score,      0.30),
        }

        weighted_sum   = 0.0
        effective_weight = 0.0
        for name, (score, w) in weights.items():
            if score is not None:
                weighted_sum     += score * w
                effective_weight += w

        if effective_weight > 0:
            final_score = weighted_sum / effective_weight
        else:
            final_score = 5.0  # no data — neutral

        final_score = round(final_score, 2)

        # Signal thresholds
        if final_score > 6.5:
            overall_signal = "bullish"
        elif final_score < 3.5:
            overall_signal = "bearish"
        else:
            overall_signal = "neutral"

        # Confidence: distance from 5.0 (the midpoint), scaled to 0-100
        # Max distance is 5.0 (score 0 or 10), so we normalise by 5.0.
        distance_from_neutral = abs(final_score - 5.0)
        confidence = round(min(distance_from_neutral / 5.0, 1.0) * 100, 1)

        reasoning["summary"] = {
            "final_score":   final_score,
            "signal":        overall_signal,
            "confidence":    confidence,
            "quarters_used": len(financial_metrics),
        }

        fundamental_analysis[ticker] = {
            "signal":     overall_signal,
            "confidence": confidence,
            "reasoning":  reasoning,
        }

        progress.update_status(agent_id, ticker, "Done", analysis=json.dumps(reasoning, indent=4))

    # Create the fundamental analysis message
    message = HumanMessage(
        content=json.dumps(fundamental_analysis),
        name=agent_id,
    )

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(fundamental_analysis, "Fundamental Analysis Agent")

    state["data"]["analyst_signals"][agent_id] = fundamental_analysis

    progress.update_status(agent_id, None, "Done")

    return {
        "messages": [message],
        "data": data,
    }
