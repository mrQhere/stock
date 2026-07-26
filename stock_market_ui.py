import streamlit as st
import pandas as pd
import json
import os
import sqlite3
import plotly.graph_objects as go
from datetime import timedelta, datetime

st.set_page_config(page_title="Institutional Quant Terminal", layout="wide", initial_sidebar_state="expanded")

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

tab_term, tab_screen, tab_port = st.tabs(["🏦 Terminal", "🔎 Screener", "💼 Portfolio"])

with tab_term:
    col_a, col_b = st.columns(2)
    df_lb = get_query("SELECT * FROM leaderboard")
    if not df_lb.empty:
        with col_a.expander("🏆 MASTER LEADERBOARD", expanded=False):
            st.dataframe(df_lb.style.highlight_max(axis=0, subset=['Prob']), use_container_width=True, hide_index=True)

    df_pw = get_query("SELECT * FROM portfolio_weights")
    if not df_pw.empty:
        with col_b.expander("⚖️ RISK PARITY PORTFOLIO", expanded=False):
            st.dataframe(df_pw, use_container_width=True, hide_index=True)

    st.sidebar.header("Illustrative Macro Overlays")
    t_08 = st.sidebar.toggle("📉 2008 Crash (-40%)")
    t_oil = st.sidebar.toggle("🛢️ Oil Shock (-15%)")
    t_bub = st.sidebar.toggle("🫧 Bubble Burst (-25%)")
    t_pan = st.sidebar.toggle("🦠 Pandemic (-30%)")
    t_hyp = st.sidebar.toggle("💸 Hyperinflation (+50%)")
    t_tech = st.sidebar.toggle("🚀 Tech Boom (+30%)")

    df_assets = get_query("SELECT Ticker FROM predictions")
    if df_assets.empty:
        st.info("System is currently syncing and calculating initial predictions. Please check back in a few minutes.")
        st.stop()

    asset_list = df_assets['Ticker'].tolist()
    ticker = st.sidebar.selectbox("Select Asset to Analyze", asset_list)

    rep = get_json_blob(ticker)
    if not rep:
        st.error(f"Failed to load prediction JSON for {ticker}.")
        st.stop()

    df = get_query("SELECT * FROM historical_data WHERE Ticker = ?", params=(ticker,))
    if df.empty:
        st.error(f"Failed to load historical data for {ticker}.")
        st.stop()
    df['Date'] = pd.to_datetime(df['Date'])

    c_head1, c_head2 = st.columns([3, 1])
    c_head1.subheader(f"{ticker} | Mode: {rep.get('Market_Mode', 'CALCULATING...')}")
    c_head2.markdown(f"<div style='text-align: right; color: #8892b0;'>Last Update: {rep.get('Last_Updated', 'N/A')}</div>", unsafe_allow_html=True)

    sig_color = "#00e676" if "BUY" in rep['Signal'] else "#ff1744" if "SELL" in rep['Signal'] else "#ffea00"
    st.markdown(f"<div class='signal-box' style='background: {sig_color}; color: #111;'>{rep['Signal']}</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    sym = "" if ticker.endswith("=X") else "₹" if ticker.endswith(".NS") else "$"

    c1.metric("Current Price", f"{sym}{rep['Price']:,.2f}", delta=f"{rep.get('Error',0):.1f}% Error")
    c2.metric("Sharpe Ratio", f"{rep.get('Sharpe', 0):.2f}")
    c3.metric("Max Drawdown", f"{rep.get('MaxDD', 0):.2f}%")
    c4.metric("Win Probability", f"{rep.get('Prob',0)}%")
    c5.metric("GARCH Volatility", f"{rep.get('Vol',0)*100:.2f}%")

    if "Investing_Tools" in rep:
        st.markdown("### 🏛️ Long-Term Investing Metrics (Total Return)")
        inv_t = rep["Investing_Tools"]
        iv1, iv2, iv3, iv4, iv5 = st.columns(5)
        iv1.metric("5Y CAGR", f"{inv_t.get('CAGR', 0):.2f}%")
        iv2.metric("Sortino Ratio", f"{inv_t.get('Sortino', 0):.2f}")
        iv3.metric("Historical VaR (95%)", f"{inv_t.get('VaR_95', 0):.2f}%")
        iv4.metric("Trend (50/200 SMA)", inv_t.get('Golden_Cross', 'N/A'))
        iv5.metric("52W H/L Dist", f"H: {inv_t.get('Dist_52W_High', 0):.1f}%", delta=f"L: +{inv_t.get('Dist_52W_Low', 0):.1f}%", delta_color="off")

    if "Factors" in rep:
        st.markdown("### 📊 Fama-French Factor Exposures & Sentiment")
        fac = rep["Factors"]
        f1, f2, f3, f4 = st.columns(4)
        mc = fac.get('Size_MCap', 0)
        mc_str = f"{sym}{mc/1e12:,.2f}T" if mc > 1e12 else f"{sym}{mc/1e9:,.2f}B" if mc > 1e9 else f"{sym}{mc/1e6:,.2f}M" if mc > 1e6 else "N/A"
        f1.metric("Size (Market Cap)", mc_str)
        f2.metric("Value (P/B Ratio)", f"{fac.get('Value_PB', 0):.2f}" if fac.get('Value_PB', 0) > 0 else "N/A")
        f3.metric("Momentum (6M Return)", f"{fac.get('Momentum_6M', 0):.2f}%")
        sentiment = rep.get("Sentiment_Score", 0)
        sentiment_label = "Bullish 🟢" if sentiment > 0.05 else "Bearish 🔴" if sentiment < -0.05 else "Neutral ⚪"
        f4.metric("News Sentiment Score", f"{sentiment:.2f}", delta=sentiment_label, delta_color="off")

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

    fig.update_layout(
        template="plotly_dark", height=600, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False,
        dragmode='drawline'
    )
    # Enable Interactive Charting
    st.plotly_chart(fig, use_container_width=True, config={'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawcircle', 'drawrect', 'eraseshape']})

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
