import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
import sqlite3
import plotly.graph_objects as go
from datetime import timedelta, datetime

st.set_page_config(page_title="Institutional Quant Terminal", layout="wide", initial_sidebar_state="expanded")

# --- MODE (set by boot script via APP_MODE env var) ---
_default_advanced = os.environ.get("APP_MODE", "investor") == "advanced"

# --- AUTHENTICATION GATE ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color: #ff3333;'>🔒 Institutional Access Required</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    pwd = c2.text_input("Enter Authorization Code:", type="password")
    if c2.button("Unlock Terminal", use_container_width=True):
        expected_pwd = None
        try:
            expected_pwd = st.secrets.get("APP_PASSWORD")
        except Exception:
            pass
        if not expected_pwd:
            expected_pwd = os.environ.get("APP_PASSWORD")
            
        if expected_pwd and pwd == expected_pwd:
            st.session_state.authenticated = True
            st.rerun()
        else:
            c2.error("AUTHORIZATION FAILED. INTRUSION LOGGED.")
    st.stop()

# --- GLOBALS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_lake")
DB_PATH = os.path.join(DATA_DIR, "quant.db")

@st.cache_data(ttl=60)
def get_query(query, params=()):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

def get_walk_accuracy(ticker: str) -> float | None:
    """Return the most recent Walk30_Accuracy for a ticker, or None."""
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            """SELECT Walk30_Accuracy FROM backtest_validation
               WHERE Ticker = ? AND Walk30_Accuracy IS NOT NULL
               ORDER BY Date DESC LIMIT 1""",
            (ticker,)
        ).fetchone()
        conn.close()
        return float(row[0]) if row else None
    except Exception:
        return None

def get_hermes_memory(ticker: str) -> list:
    """Read last 3 Hermes memory entries for a ticker from hermes_memory.json."""
    try:
        mem_path = os.path.join(DATA_DIR, "hermes_memory.json")
        if not os.path.exists(mem_path):
            return []
        with open(mem_path) as f:
            mem = json.load(f)
        return mem.get(ticker, [])[-3:]
    except Exception:
        return []

@st.cache_data(ttl=60)
def get_json_blob(ticker):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT JSON_Blob FROM predictions WHERE Ticker = ?", (ticker,))
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except:
        pass
    return None

@st.cache_data(ttl=3600)
def get_crash_windows():
    try:
        # Fetch NIFTY 50 index history back far enough to cover real crash windows
        nifty = yf.Ticker("^NSEI").history(period="max", auto_adjust=True)
        if nifty.empty: return {}
        nifty['Daily_Return'] = nifty['Close'].pct_change()
        
        # Real windows
        w_2008 = nifty.loc['2008-01-01':'2009-03-31']['Daily_Return'].dropna().values
        w_covid = nifty.loc['2020-02-01':'2020-03-31']['Daily_Return'].dropna().values
        w_rate = nifty.loc['2021-10-01':'2022-06-30']['Daily_Return'].dropna().values
        
        return {
            "2008": w_2008,
            "COVID": w_covid,
            "Rate": w_rate
        }
    except Exception:
        return {}

def run_block_bootstrap(hist_returns, start_price, n_paths=1000, days=252, block_size=5):
    if len(hist_returns) < block_size:
        return np.full((days, n_paths), start_price)
    
    n_blocks = days // block_size + 1
    paths = np.zeros((days, n_paths))
    
    for i in range(n_paths):
        prices = [start_price]
        for _ in range(n_blocks):
            start_idx = np.random.randint(0, len(hist_returns) - block_size)
            block = hist_returns[start_idx:start_idx + block_size]
            for r in block:
                prices.append(prices[-1] * (1 + r))
        paths[:, i] = prices[1:days+1]
    return paths

def execute_query(query, params=()):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(query, params)
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Error: {e}")

st.markdown("""
<style>
    .signal-box { padding: 20px; text-align: center; border-radius: 8px; font-weight: bold; font-size: 2em; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);} 
    .alert-box { padding: 15px; border-radius: 8px; background-color: #3b0000; color: #ffcccc; border: 1px solid #ff0000; margin-bottom: 20px; font-weight: 500;}
    .rationale-box { padding: 20px; border-left: 4px solid #00ffcc; background-color: #1a1e24; color: #d1d5db; font-size: 15px; margin-bottom: 20px; font-family: monospace; white-space: pre-wrap; line-height: 1.6;}
</style>
""", unsafe_allow_html=True)

if os.path.exists(os.path.join(DATA_DIR, ".sync_lock")):
    st.warning("🔄 System is currently syncing fresh market data. Please wait...")

st.title("🏦 Institutional Quant Terminal - Global")
st.markdown("---")

# --- LIVE PROGRESS BANNER ---
# Shows how many tickers have been processed so far this cycle.
try:
    _done = get_query("SELECT COUNT(*) AS n FROM predictions")['n'].iloc[0]
    _total = int(os.environ.get("TOTAL_TICKERS", 0))
    if _total > 0 and _done < _total:
        st.info(f"⏳ {_done}/{_total} assets processed — leaderboard updating automatically. Refresh in a moment.")
except Exception:
    pass

tab_term, tab_screen, tab_port = st.tabs(["🏦 Terminal", "🔎 Screener", "💼 Portfolio"])

with tab_term:
    # --- MODE TOGGLE ---
    st.sidebar.markdown("---")
    show_advanced = st.sidebar.toggle("⚙️ Advanced Mode", value=_default_advanced,
        help="OFF = Investor view (fundamentals + SIP calculator). ON = full quant terminal.")
    st.sidebar.markdown("---")

    col_a, col_b = st.columns(2)
    df_lb = get_query("SELECT * FROM leaderboard")
    if not df_lb.empty:
        with col_a.expander("🏆 MASTER LEADERBOARD", expanded=False):
            st.dataframe(df_lb.style.highlight_max(axis=0, subset=['Prob']), use_container_width=True, hide_index=True)

    df_pw = get_query("SELECT * FROM portfolio_weights")
    if not df_pw.empty and show_advanced:
        with col_b.expander("⚖️ RISK PARITY PORTFOLIO", expanded=False):
            st.dataframe(df_pw, use_container_width=True, hide_index=True)

    if show_advanced:
        st.sidebar.header("Illustrative Macro Overlays")
        t_08 = st.sidebar.toggle("📉 2008 GFC (Real Data)")
        t_covid = st.sidebar.toggle("🦠 2020 COVID (Real Data)")
        t_rate = st.sidebar.toggle("🏦 2022 Rate Hike (Real Data)")
        # These three use illustrative formula curves, not real historical windows,
        # because no named 'oil shock' or 'bubble burst' event window exists in ^NSEI data.
        t_oil = st.sidebar.toggle("🛢️ Oil Shock (-15% Formula)")
        t_bub = st.sidebar.toggle("🫧 Bubble Burst (-25% Formula)")
        t_hyp = st.sidebar.toggle("💸 Hyperinflation (+50% Formula)")
    else:
        t_08 = t_covid = t_rate = t_oil = t_bub = t_hyp = False

    df_assets = get_query("SELECT Ticker FROM predictions")
    if df_assets.empty:
        st.info("System is processing the first ticker — check back in a moment.")
        st.stop()

    asset_list = df_assets['Ticker'].tolist()
    ticker = st.sidebar.selectbox("Select Asset to Analyze", asset_list)

    rep = get_json_blob(ticker)
    if not rep:
        st.error(f"Failed to load prediction JSON for {ticker}.")
        st.stop()

    # Stale-data warning badge
    if rep.get("Stale"):
        st.warning(f"⚠ Data for **{ticker}** is from a previous cycle (fetch or compute timed out). Numbers may be outdated.")

    df = get_query("SELECT * FROM historical_data WHERE Ticker = ?", params=(ticker,))
    if df.empty:
        st.error(f"Failed to load historical data for {ticker}.")
        st.stop()
    df['Date'] = pd.to_datetime(df['Date'])

    c_head1, c_head2 = st.columns([3, 1])
    c_head1.subheader(f"{ticker} | Mode: {rep.get('Market_Mode', 'CALCULATING...')}")
    c_head2.markdown(f"<div style='text-align: right; color: #8892b0;'>Last Update: {rep.get('Last_Updated', 'N/A')}</div>", unsafe_allow_html=True)

    sym = "" if ticker.endswith("=X") else "₹" if ticker.endswith(".NS") else "$"

    # =========================================================
    # ALWAYS-VISIBLE: Price snapshot + investor fundamentals
    # =========================================================
    inv_t = rep.get("Investing_Tools", {})
    st.markdown("### 📈 Price Snapshot")
    ps1, ps2, ps3, ps4 = st.columns(4)
    ps1.metric("Current Price", f"{sym}{rep['Price']:,.2f}")
    # 1Y return: compare current price to 252 trading days ago
    if len(df) >= 252:
        price_1y_ago = float(df['Close'].iloc[-252])
        ret_1y = (rep['Price'] - price_1y_ago) / price_1y_ago * 100
        ps2.metric("1Y Return", f"{ret_1y:.1f}%")
    elif len(df) > 0:
        price_start = float(df['Close'].iloc[0])
        ret_all = (rep['Price'] - price_start) / price_start * 100
        ps2.metric("Return (since start)", f"{ret_all:.1f}%")
    else:
        ps2.metric("1Y Return", "N/A")
    ps3.metric("5Y CAGR", f"{inv_t.get('CAGR', 0):.2f}%")
    fnd = rep.get("Fundamentals", {})
    div_yield = fnd.get("div_yield", 0) or 0
    ps4.metric("Dividend Yield", f"{div_yield*100:.2f}%" if div_yield else "N/A")

    # --- Company Snapshot (renamed from Fama-French) ---
    if "Factors" in rep:
        st.markdown("### 📊 Company Snapshot & Sentiment")
        fac = rep["Factors"]
        f1, f2, f3, f4 = st.columns(4)
        mc = fac.get('Size_MCap', 0)
        mc_str = f"{sym}{mc/1e12:,.2f}T" if mc > 1e12 else f"{sym}{mc/1e9:,.2f}B" if mc > 1e9 else f"{sym}{mc/1e6:,.2f}M" if mc > 1e6 else "N/A"
        f1.metric("Market Cap", mc_str)
        f2.metric("Price/Book", f"{fac.get('Value_PB', 0):.2f}" if fac.get('Value_PB', 0) > 0 else "N/A")
        f3.metric("6M Price Momentum", f"{fac.get('Momentum_6M', 0):.2f}%")
        sentiment = rep.get("Sentiment_Score", 0)
        sentiment_label = "Bullish 🟢" if sentiment > 0.05 else "Bearish 🔴" if sentiment < -0.05 else "Neutral ⚪"
        f4.metric("News Sentiment Score", f"{sentiment:.2f}", delta=sentiment_label, delta_color="off")

    # --- Fundamentals panel (always visible, plain-English notes) ---
    if fnd:
        st.markdown("### 💼 Fundamentals")
        _NOTES = {
            "pe": "P/E ratio: price relative to trailing earnings. <15 cheap, >30 expensive for most sectors.",
            "forward_pe": "Forward P/E: based on next-year earnings estimates. Lower than trailing P/E = growth expected.",
            "pb": "Price/Book: market value vs. book value. <1 may signal undervaluation; very high = premium brand.",
            "roe": "Return on Equity: profit generated per rupee of shareholder equity. >15% is generally strong.",
            "debt_to_equity": "Debt/Equity: how much debt vs. equity. >2 is high leverage for most non-finance sectors.",
            "div_yield": "Dividend Yield: annual dividend as % of price. Higher = more income, but check payout ratio.",
            "payout_ratio": "Payout Ratio: % of earnings paid as dividends. >80% may be unsustainable.",
            "revenue_growth": "Revenue Growth (YoY): top-line expansion. >10% is healthy for most sectors.",
            "earnings_growth": "Earnings Growth (YoY): bottom-line expansion. Sustained growth drives long-term price.",
            "insider_holding": "Insider Holdings: % held by management. Higher = skin in the game.",
            "institutional_holding": "Institutional Holdings: % held by funds/FIIs. High = professional conviction.",
            "free_cashflow": "Free Cash Flow: cash left after capex. Positive FCF = company funds its own growth.",
        }
        _LABELS = {
            "pe": "Trailing P/E", "forward_pe": "Forward P/E", "pb": "P/B", "roe": "ROE",
            "debt_to_equity": "Debt/Equity", "div_yield": "Div Yield",
            "payout_ratio": "Payout Ratio", "revenue_growth": "Revenue Growth",
            "earnings_growth": "Earnings Growth", "insider_holding": "Insider %",
            "institutional_holding": "Institutional %", "free_cashflow": "Free Cash Flow",
        }
        rows = []
        for k, label in _LABELS.items():
            v = fnd.get(k, None)
            if v is None or v == 0:
                val_str = "N/A"
            elif k in ("div_yield", "payout_ratio", "roe", "revenue_growth",
                       "earnings_growth", "insider_holding", "institutional_holding"):
                val_str = f"{v*100:.2f}%"
            elif k == "free_cashflow":
                val_str = f"{sym}{v/1e9:,.2f}B" if abs(v) >= 1e9 else f"{sym}{v/1e6:,.2f}M"
            else:
                val_str = f"{v:.2f}"
            rows.append({"Metric": label, "Value": val_str, "What it means": _NOTES[k]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # --- Piotroski F-Score ---
    pio = rep.get("Piotroski_Score")
    st.markdown("### 🎓 Piotroski F-Score")
    if pio is None:
        st.info("Piotroski score unavailable — financial statements not returned by yfinance for this ticker (common for indices, ETFs, and some ADRs).")
    else:
        pio_color = "#00e676" if pio >= 7 else "#ffea00" if pio >= 4 else "#ff1744"
        pio_label = "Strong" if pio >= 7 else "Neutral" if pio >= 4 else "Weak"
        st.markdown(
            f"<div style='font-size:2em; font-weight:bold; color:{pio_color}'>{pio}/9 — {pio_label}</div>"
            "<p style='color:#8892b0; font-size:0.9em'>Scores 9 signals: profitability (3), leverage/liquidity (3), operating efficiency (3). "
            "≥7 = financially strong; ≤4 = weaknesses present. ETFs and indices return N/A.</p>",
            unsafe_allow_html=True
        )

    # --- SIP / Goal Calculator ---
    st.markdown("### 🯩 SIP & Goal Calculator")
    _cagr = inv_t.get('CAGR', 0)
    gc1, gc2, gc3 = st.columns(3)
    sip_amount = gc1.number_input("Monthly SIP Amount (₹)", min_value=500, value=5000, step=500)
    sip_years = gc2.number_input("Investment Horizon (years)", min_value=1, max_value=40, value=10)
    goal_amount = gc3.number_input("Target Corpus (₹)", min_value=10000, value=1000000, step=10000)

    if _cagr > 0:
        monthly_rate = (_cagr / 100) / 12
        n_months = sip_years * 12
        # Future value of SIP using compound formula
        fv_sip = sip_amount * (((1 + monthly_rate) ** n_months - 1) / monthly_rate) * (1 + monthly_rate)
        # Months needed to reach goal
        if monthly_rate > 0:
            import math
            months_needed = math.log(1 + (goal_amount * monthly_rate) / (sip_amount * (1 + monthly_rate))) / math.log(1 + monthly_rate)
            years_needed = months_needed / 12
        else:
            years_needed = goal_amount / (sip_amount * 12)
        sr1, sr2 = st.columns(2)
        sr1.metric(f"Projected corpus after {sip_years}Y", f"₹{fv_sip:,.0f}",
                   delta=f"Using {_cagr:.1f}% CAGR (this ticker's 5Y avg)")
        sr2.metric(f"Time to reach ₹{goal_amount:,.0f}", f"{years_needed:.1f} years",
                   delta=f"at ₹{sip_amount:,}/mo SIP")
    else:
        st.info("CAGR not available for this ticker — goal projections require at least 1 year of price history.")

    # =========================================================
    # ADVANCED MODE ONLY: Signal, metrics, MC, chart
    # =========================================================
    if show_advanced:
        sig_color = "#00e676" if "BUY" in rep['Signal'] else "#ff1744" if "SELL" in rep['Signal'] else "#ffea00"

        # Overfitting / accuracy warning badges
        overfit_flag   = rep.get("Overfit_Flag", False)
        accuracy_flag  = rep.get("Accuracy_Flag", False)
        ov_score       = rep.get("Overfit_Score", 1.0)
        walk_acc       = rep.get("Walk30_Accuracy", None)

        signal_display = rep['Signal']
        if overfit_flag or accuracy_flag:
            signal_display += "  \u26a0\ufe0f"

        st.markdown(f"<div class='signal-box' style='background: {sig_color}; color: #111;'>{signal_display}</div>", unsafe_allow_html=True)

        if overfit_flag:
            st.warning(f"\u26a0\ufe0f **Overfitting detected** on {ticker}: holdout/train R\u00b2 ratio = {ov_score:.2f} (threshold 0.4). Signal has been conservatively capped at HOLD.")
        if accuracy_flag and walk_acc is not None:
            st.warning(f"\u26a0\ufe0f **Low signal accuracy** on {ticker}: {walk_acc:.0%} over last 30 cycles (threshold 45%). Signal has been conservatively capped at HOLD.")

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Current Price", f"{sym}{rep['Price']:,.2f}", delta=f"{rep.get('Error',0):.1f}% Error")
        c2.metric("Sharpe Ratio", f"{rep.get('Sharpe', 0):.2f}")
        c3.metric("Max Drawdown", f"{rep.get('MaxDD', 0):.2f}%")
        c4.metric("Win Probability", f"{rep.get('Prob',0)}%")
        c5.metric("GARCH Volatility", f"{rep.get('Vol',0)*100:.2f}%")

        # Signal accuracy badge
        _live_acc = walk_acc if walk_acc is not None else get_walk_accuracy(ticker)
        if _live_acc is not None and _live_acc != 0.5:
            acc_pct   = _live_acc * 100
            acc_color = "#00e676" if acc_pct >= 55 else "#ff1744" if acc_pct < 45 else "#ffea00"
            c6.markdown(
                f"<div style='text-align:center; padding:8px; border-radius:6px; background:{acc_color}22; border:1px solid {acc_color}; color:{acc_color}; font-weight:bold; font-size:1.2em;'>"
                f"Signal Acc (30d)<br>{acc_pct:.0f}%</div>",
                unsafe_allow_html=True
            )
        else:
            c6.metric("Signal Acc (30d)", "Building...", delta="< 5 cycles")

        # ── Hermes Analysis Panel ──────────────────────────────────────────
        hermes_text = rep.get("Hermes_Analysis")
        if hermes_text:
            st.markdown("### \U0001f916 Hermes Agent Analysis")
            st.markdown(
                f"<div class='rationale-box'>\U0001f9e0 {hermes_text}</div>",
                unsafe_allow_html=True
            )
            # Show last 3 memory entries for this ticker
            mem_entries = get_hermes_memory(ticker)
            if mem_entries:
                with st.expander("\U0001f4c2 Hermes Memory (last 3 decisions)"):
                    for e in reversed(mem_entries):
                        outcome_str = e.get("outcome", "pending")
                        color = "#00e676" if "\u2713" in outcome_str else "#ff1744" if "\u2717" in outcome_str else "#8892b0"
                        st.markdown(
                            f"<span style='color:{color}; font-weight:bold;'>[{e.get('ts','?')}]</span> "
                            f"Signal=`{e.get('signal','?')}` | Outcome={outcome_str} | Sharpe={e.get('sharpe',0):.2f} | MaxDD={e.get('max_dd',0):.2f}%",
                            unsafe_allow_html=True
                        )
        else:
            with st.expander("\U0001f916 Hermes Agent (offline or first cycle)"):
                st.info("Hermes LLM is not running or this is the first cycle. "
                        "Install Ollama and run `ollama pull phi3:mini` then `ollama serve` to enable. "
                        "See Part 5 of the User Guide for step-by-step instructions.")

        if "Investing_Tools" in rep:
            st.markdown("### 🏑️ Long-Term Investing Metrics (Total Return)")
            iv1, iv2, iv3, iv4, iv5 = st.columns(5)
            iv1.metric("5Y CAGR", f"{inv_t.get('CAGR', 0):.2f}%")
            iv2.metric("Sortino Ratio", f"{inv_t.get('Sortino', 0):.2f}")
            iv3.metric("Historical VaR (95%)", f"{inv_t.get('VaR_95', 0):.2f}%")
            iv4.metric("Trend (50/200 SMA)", inv_t.get('Golden_Cross', 'N/A'))
            iv5.metric("52W H/L Dist", f"H: {inv_t.get('Dist_52W_High', 0):.1f}%", delta=f"L: +{inv_t.get('Dist_52W_Low', 0):.1f}%", delta_color="off")

        # Compute MC based on toggles (advanced mode only)
        crash_windows = get_crash_windows()
        active_returns = []
        active_macro_lines = {}

        lp = rep['Price']

        if t_08 and "2008" in crash_windows:
            active_returns.extend(crash_windows["2008"])
            cum = np.cumprod(1 + crash_windows["2008"][:252])
            active_macro_lines["2008 GFC"] = lp * cum
        if t_covid and "COVID" in crash_windows:
            active_returns.extend(crash_windows["COVID"])
            cum = np.cumprod(1 + crash_windows["COVID"][:252])
            active_macro_lines["2020 COVID"] = lp * cum
        if t_rate and "Rate" in crash_windows:
            active_returns.extend(crash_windows["Rate"])
            cum = np.cumprod(1 + crash_windows["Rate"][:252])
            active_macro_lines["2022 Rate Hike"] = lp * cum

        # Oil Shock / Bubble Burst / Hyperinflation use illustrative formula curves—no
        # named event window exists in ^NSEI history for these scenarios.
        if t_oil:
            active_macro_lines["Oil Shock"] = [lp*(1 - 0.15*(i/30)) for i in range(30)]
        if t_bub:
            active_macro_lines["Bubble Burst"] = [lp*(1 - 0.25*(i/30)**0.8) for i in range(30)]
        if t_hyp:
            active_macro_lines["Hyperinflation"] = [lp*(1 + 0.50*(i/30)**2) for i in range(30)]

        if len(active_returns) == 0:
            base_returns = df['Daily_Return'].dropna().values
        else:
            base_returns = np.array(active_returns)

        paths = run_block_bootstrap(base_returns, lp)

        st.markdown("### 🎲 Capital Deployment Scenarios (Monte Carlo)")
        def get_percentiles(d):
            return {
                "Extreme Bad (5%)": np.percentile(paths[d-1], 5),
                "Bad (25%)": np.percentile(paths[d-1], 25),
                "Most Likely (50%)": np.percentile(paths[d-1], 50),
                "Good (75%)": np.percentile(paths[d-1], 75),
                "Extreme Good (95%)": np.percentile(paths[d-1], 95)
            }

        scenarios = {
            "7_Day": get_percentiles(7),
            "1_Month": get_percentiles(30),
            "1_Year": get_percentiles(252)
        }

        sc_df = pd.DataFrame(scenarios).T
        for col in sc_df.columns:
            sc_df[col] = sc_df[col].apply(lambda x: f"{sym}{x:,.2f}")
        st.dataframe(sc_df, use_container_width=True)

        st.markdown("### 📈 Quantitative Vision (Interactive)")
        recent = df.tail(200)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=recent['Date'], open=recent['Open'], high=recent['High'], low=recent['Low'], close=recent['Close'], name='Price Action'))
        if 'SMA_50' in recent.columns:
            fig.add_trace(go.Scatter(x=recent['Date'], y=recent['SMA_50'], name='SMA 50', line=dict(color='#ff9900', width=1)))

        g_dates = [df['Date'].iloc[-1] + timedelta(days=i) for i in range(8)]
        fig.add_trace(go.Scatter(x=g_dates, y=[rep['Price']]+rep['Ghost'], name='XGBoost 7D Proj', line=dict(color='#00ffcc', dash='dash', width=3)))
        if 'LSTM_Ghost' in rep and rep['LSTM_Ghost']:
            fig.add_trace(go.Scatter(x=g_dates, y=[rep['Price']]+rep['LSTM_Ghost'], name='LSTM 7D Proj', line=dict(color='#ff00ff', dash='dash', width=3)))

        for name, line_data in active_macro_lines.items():
            m_dates = [df['Date'].iloc[-1] + timedelta(days=i) for i in range(len(line_data))]
            fig.add_trace(go.Scatter(x=m_dates, y=line_data, name=name, line=dict(dash='dot', width=2)))

        fig.update_layout(
            template="plotly_dark", height=600, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False,
            dragmode='drawline'
        )
        st.plotly_chart(fig, use_container_width=True, config={'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawcircle', 'drawrect', 'eraseshape']})

        # ── Backtest Equity Curve ──────────────────────────────────────────
        st.markdown("### 📊 Backtest: Strategy vs Buy-and-Hold")
        df_bt = get_query("SELECT Date, Hold_Equity, Strategy_Equity FROM backtests WHERE Ticker = ? ORDER BY Date", params=(ticker,))
        if not df_bt.empty:
            df_bt['Date'] = pd.to_datetime(df_bt['Date'])
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=df_bt['Date'], y=df_bt['Hold_Equity'],
                                        name='Buy & Hold', line=dict(color='#8892b0', width=2)))
            fig_bt.add_trace(go.Scatter(x=df_bt['Date'], y=df_bt['Strategy_Equity'],
                                        name='AI Strategy', line=dict(color='#00ffcc', width=2)))
            fig_bt.update_layout(
                template='plotly_dark', height=300,
                margin=dict(l=0, r=0, t=20, b=0),
                yaxis_title='Portfolio Value (₹)',
                legend=dict(orientation='h', y=1.1)
            )
            st.plotly_chart(fig_bt, use_container_width=True)
            # Accuracy context
            _acc_val = walk_acc if (walk_acc is not None and walk_acc != 0.5) else get_walk_accuracy(ticker)
            if _acc_val and _acc_val != 0.5:
                st.caption(f"🎯 Walk-forward signal accuracy (last 30 cycles): **{_acc_val:.0%}** "
                           f"| Holdout R²: **{rep.get('Compat',0):.1f}%** "
                           f"| Train R²: **{rep.get('Train_R2',0):.1f}%** "
                           f"| Overfit Score: **{rep.get('Overfit_Score',1):.2f}** (≥0.4 healthy)")
        else:
            st.info("Backtest data will appear after the first full backend cycle.")

        # ── Walk-Forward Validation History ───────────────────────────────
        df_wf = get_query(
            """SELECT Date, Signal, Price_At_Signal, Price_Next_Day, Was_Correct, Walk30_Accuracy
               FROM backtest_validation WHERE Ticker = ? ORDER BY Date DESC LIMIT 30""",
            params=(ticker,)
        )
        if not df_wf.empty:
            with st.expander("🗂️ Walk-Forward Signal Log (last 30 days)"):
                df_wf['Was_Correct'] = df_wf['Was_Correct'].map({1: '✅ Hit', 0: '❌ Miss', None: '⏳ Pending'})
                df_wf['Walk30_Accuracy'] = df_wf['Walk30_Accuracy'].apply(
                    lambda x: f"{x:.0%}" if x is not None else '—'
                )
                st.dataframe(df_wf, use_container_width=True, hide_index=True)

with tab_screen:
    st.header("🔎 Advanced Market Screener")
    st.write("Filter and screen all currently tracked assets in the terminal.")
    
    sc_c1, sc_c2 = st.columns(2)
    filter_sig = sc_c1.selectbox("Filter by AI Signal", ["ALL", "STRONG BUY 🟢", "BUY ↗️", "HOLD ➖", "SELL ↘️", "STRONG SELL 🔴"])
    filter_sent = sc_c2.selectbox("Filter by Sentiment", ["ALL", "Bullish", "Bearish"])
    
    screen_df = get_query("SELECT Ticker, Category, Price, Signal, Prob, Sharpe, Market_Mode FROM predictions")
    if not screen_df.empty:
        if filter_sig != "ALL":
            screen_df = screen_df[screen_df['Signal'].str.contains(filter_sig.replace("🟢","").replace("↗️","").replace("➖","").replace("↘️","").replace("🔴","").strip())]
        
        # Load JSON blobs for sentiment filtering
        if filter_sent != "ALL":
            valid_tickers = []
            for t in screen_df['Ticker']:
                b = get_json_blob(t)
                if b:
                    s = b.get("Sentiment_Score", 0)
                    if (filter_sent == "Bullish" and s > 0) or (filter_sent == "Bearish" and s < 0):
                        valid_tickers.append(t)
            screen_df = screen_df[screen_df['Ticker'].isin(valid_tickers)]
            
        st.dataframe(screen_df.sort_values(by="Prob", ascending=False), use_container_width=True, hide_index=True)

with tab_port:
    st.header("💼 Live Portfolio Tracker")
    st.write("Log your real or paper trades to track PnL against the AI's hypothetical metrics.")
    
    pc1, pc2, pc3 = st.columns([2, 1, 1])
    with pc1.form("trade_form"):
        st.subheader("Log New Trade")
        t_ticker = st.selectbox("Asset", asset_list)
        t_qty = st.number_input("Quantity", min_value=0.01, step=0.1)
        t_price = st.number_input("Buy Price (Avg)", min_value=0.01, step=1.0)
        t_date = st.date_input("Trade Date")
        
        if st.form_submit_button("Log Trade"):
            execute_query("INSERT INTO portfolio_trades (Ticker, Quantity, Buy_Price, Trade_Date) VALUES (?, ?, ?, ?)", (t_ticker, t_qty, t_price, str(t_date)))
            st.success("Trade Logged Successfully!")
            st.rerun()

    trades_df = get_query("SELECT * FROM portfolio_trades")
    if not trades_df.empty:
        st.subheader("Current Positions")
        # Calculate Live PnL
        live_data = []
        for _, row in trades_df.iterrows():
            t = row['Ticker']
            p_row = get_query("SELECT Price FROM predictions WHERE Ticker = ?", (t,))
            current_price = p_row['Price'].iloc[0] if not p_row.empty else row['Buy_Price']
            invested = row['Quantity'] * row['Buy_Price']
            current_val = row['Quantity'] * current_price
            pnl_pct = ((current_price - row['Buy_Price']) / row['Buy_Price']) * 100
            
            live_data.append({
                "ID": row['ID'], "Asset": t, "Qty": row['Quantity'], 
                "Avg Buy": f"{row['Buy_Price']:,.2f}", "Current Price": f"{current_price:,.2f}",
                "Invested": f"{invested:,.2f}", "Current Value": f"{current_val:,.2f}",
                "PnL %": pnl_pct
            })
            
        ldf = pd.DataFrame(live_data)
        st.dataframe(ldf.style.map(lambda x: "color: #00ffcc; font-weight: bold;" if isinstance(x, float) and x > 0 else "color: #ff3333; font-weight: bold;" if isinstance(x, float) and x < 0 else "", subset=["PnL %"]), use_container_width=True, hide_index=True)
        
        # Delete Trade
        del_id = st.number_input("Delete Trade ID", min_value=1, step=1)
        if st.button("Delete Selected Trade"):
            execute_query("DELETE FROM portfolio_trades WHERE ID = ?", (del_id,))
            st.rerun()
