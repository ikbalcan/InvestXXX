import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    try:
        return float(numerator) / float(denominator)
    except Exception:
        return None


def _last_value(series: pd.Series) -> Optional[float]:
    if series is None or len(series) == 0:
        return None
    try:
        return float(series.iloc[0])
    except Exception:
        return None


def _get_row_value(df: pd.DataFrame, candidates: list[str]) -> Optional[float]:
    if df is None or df.empty:
        return None
    for name in candidates:
        if name in df.index:
            return _last_value(df.loc[name])
    return None


def load_fundamentals(symbol: str) -> Dict[str, Any]:
    """Fetch fundamental data for a given ticker using yfinance.

    Returns a dictionary with:
      - info: basic company info
      - financials_annual, financials_quarterly
      - balance_annual, balance_quarterly
      - cashflow_annual, cashflow_quarterly
      - key_metrics: computed ratios
    """
    ticker = yf.Ticker(symbol)

    # Core statements
    financials_annual = ticker.financials if isinstance(ticker.financials, pd.DataFrame) else pd.DataFrame()
    financials_quarterly = ticker.quarterly_financials if isinstance(ticker.quarterly_financials, pd.DataFrame) else pd.DataFrame()

    balance_annual = ticker.balance_sheet if isinstance(ticker.balance_sheet, pd.DataFrame) else pd.DataFrame()
    balance_quarterly = ticker.quarterly_balance_sheet if isinstance(ticker.quarterly_balance_sheet, pd.DataFrame) else pd.DataFrame()

    cashflow_annual = ticker.cashflow if isinstance(ticker.cashflow, pd.DataFrame) else pd.DataFrame()
    cashflow_quarterly = ticker.quarterly_cashflow if isinstance(ticker.quarterly_cashflow, pd.DataFrame) else pd.DataFrame()

    info = ticker.info or {}

    # Compute key metrics (use annual where possible)
    income_df = financials_annual if not financials_annual.empty else financials_quarterly
    balance_df = balance_annual if not balance_annual.empty else balance_quarterly

    net_income = _get_row_value(income_df, [
        "Net Income",
        "Net Income Applicable To Common Shares",
        "Net Income Common Stockholders",
    ])
    total_revenue = _get_row_value(income_df, [
        "Total Revenue",
        "Revenue",
        "Operating Revenue",
    ])
    ebit = _get_row_value(income_df, [
        "Ebit",
        "EBIT",
        "Operating Income",
    ])

    total_equity = _get_row_value(balance_df, [
        "Total Stockholder Equity",
        "Total Stockholders Equity",
        "Total Stockholders' Equity",
        "Total Equity Gross Minority Interest",
        "Total Equity",
    ])
    total_assets = _get_row_value(balance_df, [
        "Total Assets",
        "Total Assets",
    ])
    total_liab = _get_row_value(balance_df, [
        "Total Liab",
        "Total Liabilities Net Minority Interest",
        "Total Liabilities",
    ])

    # Prices/market data from info
    market_cap = info.get("marketCap")
    trailing_pe = info.get("trailingPE")
    price_to_book = info.get("priceToBook")
    dividend_yield = info.get("dividendYield")  # already in ratio (e.g., 0.02)

    # Ratios
    roe = _safe_div(net_income, total_equity)
    roa = _safe_div(net_income, total_assets)
    net_margin = _safe_div(net_income, total_revenue)
    debt_to_equity = _safe_div(total_liab, total_equity)

    key_metrics = {
        "market_cap": market_cap,
        "trailing_pe": trailing_pe,
        "price_to_book": price_to_book,
        "dividend_yield": dividend_yield,
        "roe": roe,
        "roa": roa,
        "net_margin": net_margin,
        "debt_to_equity": debt_to_equity,
        "ebit": ebit,
        "revenue": total_revenue,
        "net_income": net_income,
        "equity": total_equity,
        "assets": total_assets,
        "liabilities": total_liab,
    }

    return {
        "info": info,
        "financials_annual": financials_annual,
        "financials_quarterly": financials_quarterly,
        "balance_annual": balance_annual,
        "balance_quarterly": balance_quarterly,
        "cashflow_annual": cashflow_annual,
        "cashflow_quarterly": cashflow_quarterly,
        "key_metrics": key_metrics,
    }


