import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import timedelta

st.set_page_config(page_title="Institutional Quant Terminal", layout="wide", initial_sidebar_state="expanded")

# --- AUTHENTICATION GATE ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color: #ff3333;'>🔒 Institutional Access Required</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    pwd = c2.text_input("Enter Authorization Code:", type="password")
    if c2.button("Unlock Terminal", use_container_width=True):
        if pwd == "stark":
            st.session_state.authenticated = True
            st.rerun()
        else:
            c2.error("AUTHORIZATION FAILED. INTRUSION LOGGED.")
    st.stop()

# --- MAIN DASHBOARD ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_lake")
ASSET_FILE = os.path.join(BASE_DIR, "assets.json")

@st.cache_data(ttl=300)
def get_csv(path, **kwargs):
    return pd.read_csv(path, **kwargs)

st.markdown("""
<style>
    .signal-box { padding: 20px; text-align: center; border-radius: 8px; font-weight: bold; font-size: 2em; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);} 
    .alert-box { padding: 15px; border-radius: 8px; background-color: #3b0000; color: #ffcccc; border: 1px solid #ff0000; margin-bottom: 20px; font-weight: 500;}
    .rationale-box { padding: 20px; border-left: 4px solid #00ffcc; background-color: #1a1e24; color: #d1d5db; font-size: 15px; margin-bottom: 20px; font-family: monospace; white-space: pre-wrap; line-height: 1.6;}
    .metric-val { font-size: 1.8rem; font-weight: 600; color: #fff;}
    .metric-label { font-size: 0.9rem; color: #8892b0; text-transform: uppercase; letter-spacing: 1px;}
    div[data-testid="metric-container"] { background-color: #1a1e24; padding: 15px; border-radius: 8px; border: 1px solid #2d333b; }
</style>
""", unsafe_allow_html=True)

st.title("🏦 Institutional Quant Terminal - India")
st.markdown("---")

col_a, col_b = st.columns(2)
if os.path.exists(os.path.join(DATA_DIR, "lb.csv")):
    with col_a.expander("🏆 MASTER LEADERBOARD", expanded=False):
        df_lb = get_csv(os.path.join(DATA_DIR, "lb.csv"))
        st.dataframe(df_lb.style.highlight_max(axis=0, subset=['Prob']), use_container_width=True, hide_index=True)

if os.path.exists(os.path.join(DATA_DIR, "portfolio_weights.csv")):
    with col_b.expander("⚖️ RISK PARITY PORTFOLIO", expanded=False):
        df_pw = get_csv(os.path.join(DATA_DIR, "portfolio_weights.csv"))
        st.dataframe(df_pw, use_container_width=True, hide_index=True)

if os.path.exists(os.path.join(DATA_DIR, "correlation_matrix.csv")):
    with st.expander("🕸️ ASSET CORRELATION MATRIX", expanded=False):
        df_corr = get_csv(os.path.join(DATA_DIR, "correlation_matrix.csv"), index_col=0)
        st.dataframe(df_corr.style.background_gradient(cmap='coolwarm', axis=None).format("{:.2f}"), use_container_width=True)

st.sidebar.header("Black Swan Stress Tests")
t_08 = st.sidebar.toggle("📉 2008 Crash (-40%)")
t_oil = st.sidebar.toggle("🛢️ Oil Shock (-15%)")
t_bub = st.sidebar.toggle("🫧 Bubble Burst (-25%)")
t_pan = st.sidebar.toggle("🦠 Pandemic (-30%)")
t_hyp = st.sidebar.toggle("💸 Hyperinflation (+50%)")
t_tech = st.sidebar.toggle("🚀 Tech Boom (+30%)")

try:
    with open(ASSET_FILE) as f: assets = json.load(f)
    
    # Flatten assets for selection and keep track of paths
    asset_paths = {}
    for asset_type, subcats in assets.items():
        for subcat, tickers in subcats.items():
            for tk in tickers:
                folder_name = tk.replace("^", "IDX_")
                asset_paths[tk] = os.path.join(DATA_DIR, asset_type, folder_name)
    
    ticker = st.sidebar.selectbox("Select Asset to Analyze", list(asset_paths.keys()))
except Exception as e:
    st.error(f"Failed to load assets: {e}")
    st.stop()

dp = asset_paths[ticker]

if os.path.exists(os.path.join(dp, "pred.json")):
    with open(os.path.join(dp, "pred.json")) as f: rep = json.load(f)
    
    try:
        df = get_csv(os.path.join(dp, "hist.csv"))
        df['Date'] = pd.to_datetime(df['Date'])
    except Exception as e:
        st.error(f"Failed to load historical data: {e}")
        st.stop()

    if rep['Error'] > 3.0: 
        st.markdown(f"<div class='alert-box'>⚠️ HIGH DEVIATION DETECTED: {rep['Error']:.2f}%. Model predictions may be unstable.</div>", unsafe_allow_html=True)
    
    c_head1, c_head2 = st.columns([3, 1])
    c_head1.subheader(f"{ticker} | Mode: {rep.get('Market_Mode', 'CALCULATING...')}")
    c_head2.markdown(f"<div style='text-align: right; color: #8892b0;'>Last Update: {rep.get('Last_Updated', 'N/A')}</div>", unsafe_allow_html=True)
    
    sig_color = "#00e676" if "BUY" in rep['Signal'] else "#ff1744" if "SELL" in rep['Signal'] else "#ffea00"
    st.markdown(f"<div class='signal-box' style='background: {sig_color}; color: #111;'>{rep['Signal']}</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Current Price", f"₹{rep['Price']:,.2f}", delta=f"{rep['Error']:.1f}% Error")
    c2.metric("Sharpe Ratio", f"{rep.get('Sharpe', 0):.2f}")
    c3.metric("Max Drawdown", f"{rep.get('MaxDD', 0):.2f}%")
    c4.metric("Win Probability", f"{rep['Prob']}%")
    c5.metric("GARCH Volatility", f"{rep['Vol']*100:.2f}%")
    
    st.markdown("### 🧠 Trade Rationale & Logic Log")
    st.markdown(f"<div class='rationale-box'>{rep.get('Rationale', 'Rationale computing...')}</div>", unsafe_allow_html=True)

    if "Investing_Tools" in rep:
        st.markdown("### 🏛️ Long-Term Investing Metrics")
        inv_t = rep["Investing_Tools"]
        iv1, iv2, iv3, iv4, iv5 = st.columns(5)
        iv1.metric("5Y CAGR", f"{inv_t.get('CAGR', 0):.2f}%")
        iv2.metric("Sortino Ratio", f"{inv_t.get('Sortino', 0):.2f}")
        iv3.metric("Historical VaR (95%)", f"{inv_t.get('VaR_95', 0):.2f}%")
        iv4.metric("Trend (50/200 SMA)", inv_t.get('Golden_Cross', 'N/A'))
        iv5.metric("52W H/L Dist", f"H: {inv_t.get('Dist_52W_High', 0):.1f}%", delta=f"L: +{inv_t.get('Dist_52W_Low', 0):.1f}%", delta_color="off")

    if "Technical_Indicators" in rep:
        st.markdown("### 🔬 Advanced Technical Indicators (AI Inputs)")
        ti = rep["Technical_Indicators"]
        t1, t2, t3, t4, t5 = st.columns(5)
        t1.metric("RSI (14)", f"{ti.get('RSI', 0):.1f}")
        t2.metric("MACD", f"{ti.get('MACD', 0):.2f}")
        t3.metric("Bollinger %B", f"{ti.get('BB_PB', 0):.2f}")
        t4.metric("ATR (14)", f"{ti.get('ATR_14', 0):.2f}")
        t5.metric("Stoch %K", f"{ti.get('Stoch_K', 0):.1f}")

    st.markdown("### 📈 Quantitative Vision (AI vs Reality)")
    recent = df.tail(200) # Show 200 days for better institutional view
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=recent['Date'], open=recent['Open'], high=recent['High'], low=recent['Low'], close=recent['Close'], name='Price Action'))
    if 'SMA_50' in recent.columns:
        fig.add_trace(go.Scatter(x=recent['Date'], y=recent['SMA_50'], name='SMA 50', line=dict(color='#ff9900', width=1)))
    if 'Hist_Ghost_Price' in recent.columns:
        fig.add_trace(go.Scatter(x=recent['Date'], y=recent['Hist_Ghost_Price'], name='AI Hist Fit', line=dict(color='rgba(0,255,204,0.5)', dash='dot', width=2)))
    
    g_dates = [df['Date'].iloc[-1] + timedelta(days=i) for i in range(8)]
    fig.add_trace(go.Scatter(x=g_dates, y=[rep['Price']]+rep['Ghost'], name='7D Forward Projection', line=dict(color='#00ffcc', dash='dash', width=3)))
    
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    col_f, col_bt = st.columns(2)
    feat_file = os.path.join(dp, "features.json")
    if os.path.exists(feat_file):
        with open(feat_file, 'r') as f: feats = json.load(f)
        col_f.markdown("#### Feature Importance (SHAP)")
        feat_df = pd.DataFrame(list(feats.items()), columns=['Indicator', 'Weight']).sort_values('Weight', ascending=True)
        fig_feat = go.Figure(go.Bar(x=feat_df['Weight'], y=feat_df['Indicator'], orientation='h', marker_color='#00ffcc'))
        fig_feat.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=30, b=0))
        col_f.plotly_chart(fig_feat, use_container_width=True)

    bt_file = os.path.join(dp, "backtest.csv")
    if os.path.exists(bt_file):
        bt_df = get_csv(bt_file)
        col_bt.markdown("#### 180D Strategy Backtest")
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=bt_df['Date'], y=bt_df['Hold_Equity'], name='Buy & Hold', line=dict(color='gray', dash='dash')))
        fig_bt.add_trace(go.Scatter(x=bt_df['Date'], y=bt_df['Strategy_Equity'], name='AI Strategy', line=dict(color='#00ffcc')))
        fig_bt.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=30, b=0))
        col_bt.plotly_chart(fig_bt, use_container_width=True)

    st.markdown("### 💰 Capital Deployment Scenarios")
    inv = st.number_input("Capital Allocation (₹)", value=100000.0, step=10000.0) / rep['Price']
    s = rep['Scenarios']
    matrix = {
        "Scenario": ["🟢 95th Percentile (Ext. Good)", "↗️ 75th Percentile (Good)", "🎯 50th Percentile (EXPECTED)", "↘️ 25th Percentile (Bad)", "🔴 5th Percentile (Ext. Bad)"],
        "7 Days": [f"₹{s['7_Day']['Extreme_Good']*inv:,.0f}", f"₹{s['7_Day']['Good']*inv:,.0f}", f"₹{s['7_Day']['Most_Likely']*inv:,.0f}", f"₹{s['7_Day']['Bad']*inv:,.0f}", f"₹{s['7_Day']['Extreme_Bad']*inv:,.0f}"],
        "1 Month": [f"₹{s['1_Month']['Extreme_Good']*inv:,.0f}", f"₹{s['1_Month']['Good']*inv:,.0f}", f"₹{s['1_Month']['Most_Likely']*inv:,.0f}", f"₹{s['1_Month']['Bad']*inv:,.0f}", f"₹{s['1_Month']['Extreme_Bad']*inv:,.0f}"],
        "1 Year": [f"₹{s['1_Year']['Extreme_Good']*inv:,.0f}", f"₹{s['1_Year']['Good']*inv:,.0f}", f"₹{s['1_Year']['Most_Likely']*inv:,.0f}", f"₹{s['1_Year']['Bad']*inv:,.0f}", f"₹{s['1_Year']['Extreme_Bad']*inv:,.0f}"]
    }
    st.table(pd.DataFrame(matrix).set_index("Scenario"))

    st.markdown("### 🌀 1,000-Path Monte Carlo Distribution (1 Year)")
    if os.path.exists(os.path.join(dp, "mc.csv")):
        mc = get_csv(os.path.join(dp, "mc.csv"))
        fig_mc = go.Figure()
        for c in mc.columns[:50]: fig_mc.add_trace(go.Scatter(y=mc[c], line=dict(color='rgba(0,255,204,0.05)'), showlegend=False))
        fig_mc.add_trace(go.Scatter(y=mc.mean(axis=1), name='Expected Path', line=dict(color='#ffea00', width=3)))
        m = rep['Macro']
        if t_08: fig_mc.add_trace(go.Scatter(y=m['2008_Crash'], name='2008 Crash', line=dict(color='#ff1744', dash='dash')))
        if t_oil: fig_mc.add_trace(go.Scatter(y=m['Oil_War'], name='Oil Shock', line=dict(color='#ff9100', dash='dash')))
        if t_bub: fig_mc.add_trace(go.Scatter(y=m['Bubble_Burst'], name='Bubble Burst', line=dict(color='#d500f9', dash='dash')))
        if t_pan: fig_mc.add_trace(go.Scatter(y=m['Pandemic'], name='Pandemic', line=dict(color='#f50057', dash='dash')))
        if t_hyp: fig_mc.add_trace(go.Scatter(y=m['Hyperinflation'], name='Hyperinflation', line=dict(color='#00e676', dash='dash')))
        if t_tech: fig_mc.add_trace(go.Scatter(y=m['Tech_Boom'], name='Tech Boom', line=dict(color='#00b0ff', dash='dash')))
        fig_mc.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_mc, use_container_width=True)
else:
    st.info("System is currently syncing and calculating initial predictions for this asset. Please check back later.")
