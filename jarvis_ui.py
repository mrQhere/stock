import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import timedelta

st.set_page_config(page_title="JARVIS V6.1 | Sovereign Engine", layout="wide", initial_sidebar_state="expanded")

DATA_DIR = "/home/dxt/JARVIS_System/data_lake"
ASSET_FILE = "/home/dxt/JARVIS_System/assets.json"

st.markdown("""
<style>
    .signal-box { padding: 20px; text-align: center; border-radius: 10px; font-weight: bold; font-size: 2em; margin-bottom: 20px;} 
    .alert-box { padding: 10px; border-radius: 5px; background-color: #550000; color: white; border: 1px solid red; margin-bottom: 20px; text-align: center; font-weight: bold;}
    .ai-box { padding: 20px; border-left: 5px solid #00FF00; background-color: #161B22; color: #E6EDF3; font-size: 16px; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

st.title("🟢 JARVIS: Sovereign Institutional Suite")

# --- MASTER DASHBOARDS ---
col_a, col_b = st.columns(2)
if os.path.exists(os.path.join(DATA_DIR, "lb.csv")):
    with col_a.expander("🏆 VIEW MASTER LEADERBOARD", expanded=False):
        st.dataframe(pd.read_csv(os.path.join(DATA_DIR, "lb.csv")), use_container_width=True, hide_index=True)
if os.path.exists(os.path.join(DATA_DIR, "portfolio_weights.csv")):
    with col_b.expander("⚖️ PORTFOLIO OPTIMIZER (Risk Parity)", expanded=False):
        st.dataframe(pd.read_csv(os.path.join(DATA_DIR, "portfolio_weights.csv")), use_container_width=True, hide_index=True)

if os.path.exists(os.path.join(DATA_DIR, "correlation_matrix.csv")):
    with st.expander("🕸️ Correlation Guardian (Asset Linkages)", expanded=False):
        st.dataframe(pd.read_csv(os.path.join(DATA_DIR, "correlation_matrix.csv"), index_col=0).style.background_gradient(cmap='coolwarm', axis=None), use_container_width=True)

# --- 6 BLACK SWAN TOGGLES ---
st.sidebar.header("Black Swan Stress Tests")
t_08 = st.sidebar.toggle("📉 2008 Crash")
t_oil = st.sidebar.toggle("🛢️ Oil War")
t_bub = st.sidebar.toggle("🫧 Bubble Burst")
t_pan = st.sidebar.toggle("🦠 Pandemic")
t_hyp = st.sidebar.toggle("💸 Hyperinflation")
t_tech = st.sidebar.toggle("🚀 Tech Boom")

try:
    with open(ASSET_FILE) as f: assets = json.load(f)
    ticker = st.sidebar.selectbox("Select Asset", [tk for cat in assets.values() for tk in cat])
except: st.stop()

dp = os.path.join(DATA_DIR, ticker)
if os.path.exists(os.path.join(dp, "pred.json")):
    with open(os.path.join(dp, "pred.json")) as f: rep = json.load(f)
    df = pd.read_csv(os.path.join(dp, "hist.csv"))
    df['Date'] = pd.to_datetime(df['Date'])

    if rep['Error'] > 3.0: 
        st.markdown(f"<div class='alert-box'>⚠️ AI HALLUCINATING: Deviation {rep['Error']:.2f}%. Predictions unstable. Training sequence engaged.</div>", unsafe_allow_html=True)
    
    st.subheader(f"System Mode: {rep.get('Market_Mode', 'CALCULATING...')}")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Current Price", f"₹{rep['Price']:,.2f}")
    c2.metric("Compatibility", f"{rep['Compat']:.2f}%")
    c3.metric("Volatility", f"{rep['Vol']*100:.2f}%")
    c4.metric("Profit Prob", f"{rep['Prob']}%")
    c5.metric("Database Memory", f"{len(df)} Days")

    sig_color = "#00FF00" if "BUY" in rep['Signal'] else "#FF0000" if "SELL" in rep['Signal'] else "#FFFF00"
    st.markdown(f"<div class='signal-box' style='background: {sig_color}; color: black;'>{rep['Signal']}</div>", unsafe_allow_html=True)
    
    st.markdown("### 🧠 Llama-3 Tactical Verdict")
    st.markdown(f"<div class='ai-box'>{rep['Verdict']}</div>", unsafe_allow_html=True)

    st.markdown("### 📈 Tactical Vision (AI Learning vs Reality)")
    recent = df.tail(1000)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=recent['Date'], y=recent['Close'], name='Actual', line=dict(color='#00FFFF', width=2)))
    if 'Hist_Ghost_Price' in recent.columns:
        fig.add_trace(go.Scatter(x=recent['Date'], y=recent['Hist_Ghost_Price'], name='AI Hist Fit', line=dict(color='rgba(0,255,0,0.5)', dash='dot')))
    
    g_dates = [df['Date'].iloc[-1] + timedelta(days=i) for i in range(8)]
    fig.add_trace(go.Scatter(x=g_dates, y=[rep['Price']]+rep['Ghost'], name='7D Forecast', line=dict(color='#00FF00', dash='dash', width=3)))
    fig.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True)

    # --- FEATURE IMPORTANCE & 180D BACKTEST ROW ---
    col_f, col_bt = st.columns(2)
    feat_file = os.path.join(dp, "features.json")
    if os.path.exists(feat_file):
        with open(feat_file, 'r') as f: feats = json.load(f)
        col_f.markdown("#### The 'Why' Factor (SHAP Logic)")
        feat_df = pd.DataFrame(list(feats.items()), columns=['Indicator', 'Weight'])
        fig_feat = go.Figure(go.Bar(x=feat_df['Weight'], y=feat_df['Indicator'], orientation='h', marker_color='#00FF00'))
        fig_feat.update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=0, t=30, b=0))
        col_f.plotly_chart(fig_feat, use_container_width=True)

    bt_file = os.path.join(dp, "backtest.csv")
    if os.path.exists(bt_file):
        bt_df = pd.read_csv(bt_file)
        col_bt.markdown("#### Reality Check (180D Paper Trade)")
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=bt_df['Date'], y=bt_df['Hold_Equity'], name='Hold Nifty', line=dict(color='gray', dash='dash')))
        fig_bt.add_trace(go.Scatter(x=bt_df['Date'], y=bt_df['Strategy_Equity'], name='JARVIS', line=dict(color='#00FFFF')))
        fig_bt.update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=0, t=30, b=0))
        col_bt.plotly_chart(fig_bt, use_container_width=True)

    # --- FULL 6x3 MATRIX RESTORED ---
    st.markdown("### 💰 Capital Deployment Projector (₹)")
    inv = st.number_input("Capital (₹)", value=10000.0) / rep['Price']
    s = rep['Scenarios']
    matrix = {
        "Reality": ["🟢 Ext. Good", "↗️ Good", "🎯 MOST LIKELY", "➖ OK", "↘️ Bad", "🔴 Ext. Bad"],
        "7 Days": [f"₹{s['7_Day']['Extreme_Good']*inv:,.0f}", f"₹{s['7_Day']['Good']*inv:,.0f}", f"₹{s['7_Day']['Most_Likely']*inv:,.0f}", f"₹{s['7_Day']['OK']*inv:,.0f}", f"₹{s['7_Day']['Bad']*inv:,.0f}", f"₹{s['7_Day']['Extreme_Bad']*inv:,.0f}"],
        "1 Month": [f"₹{s['1_Month']['Extreme_Good']*inv:,.0f}", f"₹{s['1_Month']['Good']*inv:,.0f}", f"₹{s['1_Month']['Most_Likely']*inv:,.0f}", f"₹{s['1_Month']['OK']*inv:,.0f}", f"SHAP Logic{s['1_Month']['Bad']*inv:,.0f}", f"₹{s['1_Month']['Extreme_Bad']*inv:,.0f}"],
        "1 Year": [f"₹{s['1_Year']['Extreme_Good']*inv:,.0f}", f"₹{s['1_Year']['Good']*inv:,.0f}", f"₹{s['1_Year']['Most_Likely']*inv:,.0f}", f"₹{s['1_Year']['OK']*inv:,.0f}", f"₹{s['1_Year']['Bad']*inv:,.0f}", f"₹{s['1_Year']['Extreme_Bad']*inv:,.0f}"]
    }
    st.table(pd.DataFrame(matrix))

    # --- ALL 6 MONTE CARLO MACRO LINES RESTORED ---
    if os.path.exists(os.path.join(dp, "mc.csv")):
        mc = pd.read_csv(os.path.join(dp, "mc.csv"))
        fig_mc = go.Figure()
        for c in mc.columns[:100]: fig_mc.add_trace(go.Scatter(y=mc[c], line=dict(color='rgba(0,150,255,0.05)'), showlegend=False))
        fig_mc.add_trace(go.Scatter(y=mc.mean(axis=1), name='MOST LIKELY', line=dict(color='yellow', width=3)))
        m = rep['Macro']
        if t_08: fig_mc.add_trace(go.Scatter(y=m['2008_Crash'], name='2008', line=dict(color='red', dash='dash')))
        if t_oil: fig_mc.add_trace(go.Scatter(y=m['Oil_War'], name='Oil War', line=dict(color='orange', dash='dash')))
        if t_bub: fig_mc.add_trace(go.Scatter(y=m['Bubble_Burst'], name='Bubble', line=dict(color='purple', dash='dash')))
        if t_pan: fig_mc.add_trace(go.Scatter(y=m['Pandemic'], name='Pandemic', line=dict(color='magenta', dash='dash')))
        if t_hyp: fig_mc.add_trace(go.Scatter(y=m['Hyperinflation'], name='Hyper', line=dict(color='green', dash='dash')))
        if t_tech: fig_mc.add_trace(go.Scatter(y=m['Tech_Boom'], name='Tech', line=dict(color='cyan', dash='dash')))
        fig_mc.update_layout(template="plotly_dark", height=450)
        st.plotly_chart(fig_mc, use_container_width=True)
