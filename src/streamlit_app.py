import os
import sys
import json
import random
import pandas as pd
import streamlit as st
import altair as alt

# ── Path setup so we can import routing_engine ──────────────────────────────
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)
from routing_engine import route_transaction_with_trace, update_bandit

st.set_page_config(
    page_title="RouteIQ — Intelligent Payment Routing",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Subtle grid background */
.stApp {
    background-color: #F3F4F8;
    background-image:
        linear-gradient(rgba(0,102,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,102,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    color: #0F172A;
}

.block-container {
    padding: 2rem 3rem 4rem 3rem;
    max-width: 1400px;
}

/* ── Header ── */
.routeiq-header {
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
    border-bottom: 3px solid #0066FF;
}
.routeiq-title {
    font-size: 36px;
    font-weight: 700;
    color: #0A0F1E;
    letter-spacing: -1px;
    line-height: 1.1;
}
.routeiq-subtitle {
    font-size: 14px;
    color: #64748B;
    margin-top: 4px;
    font-weight: 400;
}

/* Pulsing LIVE badge */
.routeiq-badge {
    display: inline-block;
    background: #0066FF;
    color: white;
    font-size: 10px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
    margin-left: 12px;
    vertical-align: middle;
    letter-spacing: 1px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(0,102,255,0.5); }
    70%  { box-shadow: 0 0 0 8px rgba(0,102,255,0); }
    100% { box-shadow: 0 0 0 0 rgba(0,102,255,0); }
}

/* ── KPI cards ── */
.kpi-row {
    display: flex;
    gap: 16px;
    margin-top: 1.4rem;
}
.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 16px 24px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    min-width: 180px;
}
.kpi-card-blue   { border-left: 4px solid #0066FF; }
.kpi-card-green  { border-left: 4px solid #00C853; }
.kpi-card-purple { border-left: 4px solid #7C3AED; }
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.kpi-value {
    font-size: 22px;
    font-weight: 700;
    color: #0A0F1E;
    margin-top: 4px;
    letter-spacing: -0.5px;
}
.kpi-value-blue   { color: #0066FF; }
.kpi-value-green  { color: #00C853; }
.kpi-value-purple { color: #7C3AED; }

/* ── Section titles with blue accent bar ── */
.section-title {
    font-size: 17px;
    font-weight: 700;
    color: #0A0F1E;
    margin-bottom: 1rem;
    padding-left: 12px;
    border-left: 4px solid #0066FF;
    line-height: 1.3;
}

/* ── Route a Payment card wrapper ── */
.route-card {
    background: white;
    border-radius: 16px;
    padding: 28px 32px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    margin-bottom: 1.5rem;
}

/* ── Cards ── */
.card {
    background: white;
    border: 1px solid #E8EDF5;
    border-radius: 14px;
    padding: 24px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    margin-bottom: 1rem;
}

/* ── Decision result card ── */
.decision-card {
    background: white;
    border: 1px solid #E8EDF5;
    border-left: 5px solid #0066FF;
    border-radius: 14px;
    padding: 28px;
    box-shadow: 0 8px 24px rgba(0,102,255,0.10);
    margin-top: 1rem;
}
.selected-psp {
    font-size: 38px;
    font-weight: 700;
    color: #0A0F1E;
    letter-spacing: -1px;
    line-height: 1.1;
}
.decision-label {
    font-size: 10px;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.decision-value {
    font-size: 15px;
    font-weight: 600;
    color: #0A0F1E;
}
.confidence-badge {
    background: linear-gradient(135deg, #0066FF, #0044CC);
    color: white;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 700;
    display: inline-block;
}
.badge-optimal {
    background: #DCFCE7;
    color: #15803D;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
    border: 1px solid #BBF7D0;
}
.badge-explore {
    background: #FEF9C3;
    color: #B45309;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
    border: 1px solid #FDE68A;
}

/* ── Route Now button ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #0066FF, #0044CC) !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 32px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 4px 14px rgba(0,102,255,0.35) !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(0,102,255,0.45) !important;
}

/* ── Input labels ── */
div[data-testid="stSelectbox"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"] label {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #64748B !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}

/* ── Tables ── */
[data-testid="stDataFrame"] {
    border: 1px solid #E8EDF5 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
}
thead th {
    background: #0A0F1E !important;
    color: white !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
}
tbody tr:nth-child(even) { background: #F8FAFC !important; }
tbody td { font-size: 13px !important; color: #1E293B !important; }

/* ── A/B comparison table ── */
.ab-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.ab-table th {
    background: #0A0F1E;
    color: white;
    padding: 10px 16px;
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.ab-table th.early { background: #1E293B; }
.ab-table th.late  { background: #0044CC; }
.ab-table td {
    padding: 10px 16px;
    border-bottom: 1px solid #F1F5F9;
    color: #1E293B;
    font-weight: 500;
}
.ab-table tr:last-child td { border-bottom: none; }
.ab-table tr:nth-child(even) td { background: #F8FAFC; }
.ab-improved { color: #16A34A; font-weight: 700; }
.ab-delta    { color: #16A34A; font-size: 12px; font-weight: 600; }
.ab-delta-neg { color: #DC2626; font-size: 12px; font-weight: 600; }
.ab-subtitle {
    font-size: 13px;
    color: #64748B;
    margin-bottom: 1rem;
    font-style: italic;
}

/* ── Decision quality badges ── */
.dq-card {
    background: white;
    border-radius: 12px;
    padding: 16px 24px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    min-width: 160px;
    text-align: center;
}
.dq-card-green  { border-top: 4px solid #00C853; }
.dq-card-blue   { border-top: 4px solid #0066FF; }
.dq-card-orange { border-top: 4px solid #F97316; }
.dq-value-green  { font-size: 28px; font-weight: 700; color: #00C853; letter-spacing: -0.5px; }
.dq-value-blue   { font-size: 28px; font-weight: 700; color: #0066FF; letter-spacing: -0.5px; }
.dq-value-orange { font-size: 28px; font-weight: 700; color: #F97316; letter-spacing: -0.5px; }
.dq-label { font-size: 11px; font-weight: 600; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px; }

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Data ────────────────────────────────────────────────────────────────────
REPLAY_RESULTS_PATH = os.path.join(CURRENT_DIR, "replay_results.csv")
DECISION_LOG_PATH   = os.path.join(CURRENT_DIR, "decision_log.csv")
PSP_DATA_PATH       = os.path.join(CURRENT_DIR, "../data/payment_data.csv")


@st.cache_data(ttl=300)
def load_decision_log():
    try:
        return pd.read_csv(DECISION_LOG_PATH)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_replay_results():
    try:
        return pd.read_csv(REPLAY_RESULTS_PATH)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_psp_data():
    try:
        return pd.read_csv(PSP_DATA_PATH)
    except Exception:
        return pd.DataFrame()


df      = load_replay_results()
psp_df  = load_psp_data()

# PSP lookup dicts used by the live routing simulator
_psp_success_rate = psp_df.groupby("psp")["success_rate"].mean().to_dict()
_psp_base_cost    = psp_df.groupby("psp")["base_cost"].mean().to_dict()
_psp_base_latency = psp_df.groupby("psp")["latency_ms"].mean().to_dict()

total_txns = len(df)
avg_regret = round(df["regret"].mean(), 4)
osr        = df["is_optimal"].mean()

# ── Country → methods / currency mapping ────────────────────────────────────
COUNTRY_CONFIG = {
    "Indonesia":   {"methods": ["GoPay", "OVO", "DANA", "ShopeePay", "BANK_TRANSFER"], "currency": "IDR"},
    "Philippines": {"methods": ["GCash", "PayMaya", "BANK_TRANSFER"],                   "currency": "PHP"},
    "Vietnam":     {"methods": ["MoMo", "ZaloPay", "Viettel_Pay"],                      "currency": "VND"},
    "Thailand":    {"methods": ["PromptPay", "BANK_TRANSFER"],                           "currency": "THB"},
    "Malaysia":    {"methods": ["FPX", "Touch_n_Go", "BANK_TRANSFER"],                  "currency": "MYR"},
    "Nigeria":     {"methods": ["BANK_TRANSFER"],                                        "currency": "NGN"},
    "Kenya":       {"methods": ["M-Pesa", "BANK_TRANSFER"],                              "currency": "KES"},
    "Ghana":       {"methods": ["MTN_Mobile_Money", "BANK_TRANSFER"],                   "currency": "GHS"},
    "Tanzania":    {"methods": ["Airtel_Money", "HaloPesa", "BANK_TRANSFER"],           "currency": "TZS"},
    "EU":          {"methods": ["SEPA", "OPEN_BANKING"],                                 "currency": "EUR"},
    "Brazil":      {"methods": ["PIX", "BANK_TRANSFER"],                                 "currency": "BRL"},
    "Mexico":      {"methods": ["SPEI", "BANK_TRANSFER"],                                "currency": "MXN"},
    "Chile":       {"methods": ["BANK_TRANSFER"],                                        "currency": "CLP"},
    "USA":         {"methods": ["ACH", "WIRE"],                                          "currency": "USD"},
}

REGION_MAP = {
    "Nigeria": "Africa", "Kenya": "Africa", "Ghana": "Africa", "Tanzania": "Africa",
    "Indonesia": "APAC", "Philippines": "APAC", "Vietnam": "APAC", "Thailand": "APAC", "Malaysia": "APAC",
    "EU": "Europe",
    "Brazil": "Americas", "Mexico": "Americas", "Chile": "Americas", "USA": "Americas",
}

_psp_region = (
    psp_df.assign(region=psp_df["country"].map(REGION_MAP))
    .groupby("psp")["region"]
    .first()
    .to_dict()
)

# ═══════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="routeiq-header">
  <div>
    <span class="routeiq-title">RouteIQ</span>
    <span class="routeiq-badge">LIVE</span>
  </div>
  <div class="routeiq-subtitle">AI-powered PSP selection across 14 markets</div>
  <div class="kpi-row">
    <div class="kpi-pill">
      <div>
        <div class="kpi-pill-label">Total Transactions</div>
        <div class="kpi-pill-value">{total_txns:,}</div>
      </div>
    </div>
    <div class="kpi-pill">
      <div>
        <div class="kpi-pill-label">Avg Regret</div>
        <div class="kpi-pill-value">{avg_regret}</div>
      </div>
    </div>
    <div class="kpi-pill">
      <div>
        <div class="kpi-pill-label">Optimal Selection Rate</div>
        <div class="kpi-pill-value kpi-pill-accent">{osr:.2%}</div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# REVENUE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Revenue Intelligence</div>', unsafe_allow_html=True)

if os.path.exists(DECISION_LOG_PATH):
    _dl_profit = load_decision_log()

    # ── Build profit figures ─────────────────────────────────────────────
    TAKE_RATE = 0.015

    if "reward" in _dl_profit.columns and _dl_profit["reward"].notna().any():
        # Use pre-computed economic reward
        _dl_profit["_reward"] = _dl_profit["reward"]
    else:
        # Fallback: reconstruct from amount + outcome + base_cost
        _dl_profit["_success"] = _dl_profit["outcome"].str.lower() == "success"
        _dl_profit["_revenue"] = _dl_profit["amount"] * TAKE_RATE
        _psp_cost_map = psp_df.groupby("psp")["base_cost"].mean().to_dict()
        _dl_profit["_cost"]   = _dl_profit["selected_psp"].map(_psp_cost_map).fillna(1.80)
        _dl_profit["_reward"] = _dl_profit.apply(
            lambda r: r["_revenue"] - r["_cost"] if r["_success"]
                      else -(r["_cost"] + r["_revenue"] * 0.5),
            axis=1,
        )

    _dl_profit["_success"]    = _dl_profit.get("final_outcome", _dl_profit.get("outcome", "failure")).str.lower() == "success"
    _dl_profit["_revenue_txn"] = _dl_profit.apply(
        lambda r: r["amount"] * TAKE_RATE if r["_success"] else 0, axis=1
    )
    _psp_cost_map2 = psp_df.groupby("psp")["base_cost"].mean().to_dict()
    _dl_profit["_cost_txn"]   = _dl_profit["selected_psp"].map(_psp_cost_map2).fillna(1.80)

    total_revenue = _dl_profit["_revenue_txn"].sum()
    total_cost    = _dl_profit["_cost_txn"].sum()
    net_profit    = total_revenue - total_cost
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    margin_color  = "#16A34A" if net_profit >= 0 else "#DC2626"
    margin_sign   = "+" if net_profit >= 0 else ""

    # ── 4 KPI cards ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex; gap:16px; margin-bottom:1.5rem;">
      <div class="kpi-card kpi-card-blue" style="flex:1;">
        <div class="kpi-label">Total Revenue</div>
        <div class="kpi-value kpi-value-blue">${total_revenue:,.2f}</div>
        <div style="font-size:11px;color:#94A3B8;margin-top:3px;">from successful txns × 1.5%</div>
      </div>
      <div class="kpi-card kpi-card-purple" style="flex:1;">
        <div class="kpi-label">Total PSP Cost</div>
        <div class="kpi-value kpi-value-purple">${total_cost:,.2f}</div>
        <div style="font-size:11px;color:#94A3B8;margin-top:3px;">base cost per transaction</div>
      </div>
      <div class="kpi-card" style="flex:1; border-left:4px solid {margin_color};">
        <div class="kpi-label">Net Profit</div>
        <div style="font-size:22px;font-weight:700;color:{margin_color};margin-top:4px;letter-spacing:-0.5px;">
          {margin_sign}${abs(net_profit):,.2f}
        </div>
        <div style="font-size:11px;color:#94A3B8;margin-top:3px;">revenue − PSP cost</div>
      </div>
      <div class="kpi-card kpi-card-green" style="flex:1;">
        <div class="kpi-label">Profit Margin</div>
        <div class="kpi-value kpi-value-green">{margin_sign}{profit_margin:.1f}%</div>
        <div style="font-size:11px;color:#94A3B8;margin-top:3px;">net / revenue</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Retry intelligence metrics ────────────────────────────────────────
    _retry_mask   = _dl_profit["attempts"].str.contains("→", na=False) if "attempts" in _dl_profit.columns else pd.Series([False] * len(_dl_profit))
    _retry_rate   = _retry_mask.mean() * 100
    _retried_df   = _dl_profit[_retry_mask]
    _recovery_rate = ((_retried_df["final_outcome"].str.lower() == "success").mean() * 100) if (len(_retried_df) > 0 and "final_outcome" in _dl_profit.columns) else 0.0
    _saved_count  = int((_retry_mask & (_dl_profit.get("final_outcome", _dl_profit.get("outcome", "")).str.lower() == "success")).sum()) if "final_outcome" in _dl_profit.columns else 0

    st.markdown(f"""
    <div style="display:flex; gap:16px; margin-bottom:1.5rem;">
      <div class="kpi-card" style="flex:1; border-left:4px solid #16A34A;">
        <div class="kpi-label">Retry Rate</div>
        <div class="kpi-value kpi-value-green">{_retry_rate:.1f}%</div>
        <div style="font-size:11px;color:#94A3B8;margin-top:3px;">Retry Rate</div>
      </div>
      <div class="kpi-card" style="flex:1; border-left:4px solid #16A34A;">
        <div class="kpi-label">RL Recovery Rate</div>
        <div class="kpi-value kpi-value-green">{_recovery_rate:.1f}%</div>
        <div style="font-size:11px;color:#94A3B8;margin-top:3px;">RL Recovery Rate</div>
      </div>
      <div class="kpi-card" style="flex:1; border-left:4px solid #16A34A;">
        <div class="kpi-label">Payments Saved by RL</div>
        <div class="kpi-value kpi-value-green">{_saved_count:,}</div>
        <div style="font-size:11px;color:#94A3B8;margin-top:3px;">Payments Saved by RL</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Charts side by side ───────────────────────────────────────────────
    ri_left, ri_right = st.columns([1.8, 1])

    with ri_left:
        # Cumulative profit line chart using reward column
        _dl_profit["_cumulative"] = _dl_profit["_reward"].cumsum()
        _dl_profit["_txn_num"]    = range(1, len(_dl_profit) + 1)

        # Single colour based on final value
        final_val   = _dl_profit["_cumulative"].iloc[-1]
        line_color  = "#16A34A" if final_val >= 0 else "#DC2626"

        cum_chart = (
            alt.Chart(_dl_profit[["_txn_num", "_cumulative"]])
            .mark_line(strokeWidth=2, color=line_color)
            .encode(
                x=alt.X("_txn_num:Q", title="Transaction Number"),
                y=alt.Y("_cumulative:Q", title="Cumulative Net Profit ($)"),
                tooltip=[
                    alt.Tooltip("_txn_num:Q", title="Transaction"),
                    alt.Tooltip("_cumulative:Q", title="Cumulative Profit ($)", format="$,.2f"),
                ],
            )
            .properties(title="Cumulative Profit Over Transactions", height=260)
            .configure_view(strokeWidth=0)
            .configure_axis(grid=True, gridColor="#F1F5F9", labelColor="#64748B", titleColor="#64748B")
            .configure_title(fontSize=13, fontWeight=600, color="#0F172A")
        )
        st.altair_chart(cum_chart, use_container_width=True)

    with ri_right:
        # Avg profit per transaction by region
        _psp_primary_country2 = psp_df.groupby("psp")["country"].first().to_dict()
        _dl_profit["_region"] = (
            _dl_profit["selected_psp"]
            .map(_psp_primary_country2)
            .map(REGION_MAP)
            .fillna("Other")
        )
        region_profit = (
            _dl_profit.groupby("_region")["_reward"].mean()
            .reset_index()
            .rename(columns={"_region": "Region", "_reward": "Avg Profit"})
        )
        region_profit = region_profit[region_profit["Region"] != "Other"]

        region_colors_map = {
            "Africa": "#F97316", "APAC": "#7C3AED",
            "Europe": "#0066FF", "Americas": "#00C853",
        }
        region_profit["color"] = region_profit["Region"].map(region_colors_map).fillna("#94A3B8")

        region_chart = (
            alt.Chart(region_profit)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Region:N", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Avg Profit:Q", title="Avg Profit / Txn ($)"),
                color=alt.Color("Region:N", scale=alt.Scale(
                    domain=list(region_colors_map.keys()),
                    range=list(region_colors_map.values()),
                ), legend=None),
                tooltip=[
                    alt.Tooltip("Region:N"),
                    alt.Tooltip("Avg Profit:Q", title="Avg Profit ($)", format="$,.4f"),
                ],
            )
            .properties(title="Avg Profit by Region", height=260)
            .configure_view(strokeWidth=0)
            .configure_axis(grid=False, labelColor="#64748B", titleColor="#64748B")
            .configure_title(fontSize=13, fontWeight=600, color="#0F172A")
        )
        st.altair_chart(region_chart, use_container_width=True)
else:
    st.info("Run transaction_simulator.py first to generate decision_log.csv.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# DECISION QUALITY
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Decision Quality</div>', unsafe_allow_html=True)

if "decision_quality" in df.columns:
    n_total    = len(df)
    n_optimal  = (df["decision_quality"] == "Optimal").sum()
    n_near     = (df["decision_quality"] == "Near-optimal").sum()
    n_sub      = (df["decision_quality"] == "Suboptimal").sum()
    pct_opt    = n_optimal  / n_total * 100
    pct_near   = n_near     / n_total * 100
    pct_sub    = n_sub      / n_total * 100

    dq_left, dq_right = st.columns([1.4, 1])

    with dq_left:
        st.markdown(f"""
        <div style="display:flex; gap:16px; margin-bottom:0.5rem;">
          <div class="dq-card dq-card-green">
            <div class="dq-value-green">{pct_opt:.1f}%</div>
            <div class="dq-label">Optimal</div>
            <div style="font-size:12px; color:#64748B; margin-top:4px;">{n_optimal:,} decisions</div>
          </div>
          <div class="dq-card dq-card-blue">
            <div class="dq-value-blue">{pct_near:.1f}%</div>
            <div class="dq-label">Near-Optimal</div>
            <div style="font-size:12px; color:#64748B; margin-top:4px;">{n_near:,} decisions</div>
          </div>
          <div class="dq-card dq-card-orange">
            <div class="dq-value-orange">{pct_sub:.1f}%</div>
            <div class="dq-label">Suboptimal</div>
            <div style="font-size:12px; color:#64748B; margin-top:4px;">{n_sub:,} decisions</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with dq_right:
        quality_counts = pd.DataFrame({
            "Quality": ["Optimal", "Near-optimal", "Suboptimal"],
            "Count":   [n_optimal, n_near, n_sub],
            "Pct":     [pct_opt, pct_near, pct_sub],
        })
        donut = (
            alt.Chart(quality_counts)
            .mark_arc(innerRadius=55, outerRadius=100)
            .encode(
                theta=alt.Theta("Count:Q"),
                color=alt.Color(
                    "Quality:N",
                    scale=alt.Scale(
                        domain=["Optimal", "Near-optimal", "Suboptimal"],
                        range=["#00C853", "#0066FF", "#F97316"],
                    ),
                    legend=alt.Legend(orient="right", labelFontSize=12, titleFontSize=11),
                ),
                tooltip=[
                    alt.Tooltip("Quality:N"),
                    alt.Tooltip("Count:Q", format=","),
                    alt.Tooltip("Pct:Q", format=".1f", title="Pct %"),
                ],
            )
            .properties(height=220, title="Decision Quality Breakdown")
            .configure_view(strokeWidth=0)
            .configure_title(fontSize=13, fontWeight=600, color="#0F172A")
        )
        st.altair_chart(donut, use_container_width=True)
else:
    st.info("Re-run replay_engine.py to generate decision_quality data.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# A/B COMPARISON — EARLY VS LATE LEARNING
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Learning Improvement — Early vs Late</div>', unsafe_allow_html=True)
st.markdown('<div class="ab-subtitle">Proving the system gets smarter over time</div>', unsafe_allow_html=True)

if os.path.exists(DECISION_LOG_PATH):
    dl_ab = load_decision_log()

    # Need psp_data for scoring — build same lookups as replay_engine
    _psp_df_ab = psp_df.copy()
    _MAX_COST    = 3.0
    _MAX_LATENCY = 2500
    _psp_df_ab["cost_score"]    = 1 - (_psp_df_ab["base_cost"]  / _MAX_COST)
    _psp_df_ab["latency_score"] = 1 - (_psp_df_ab["latency_ms"] / _MAX_LATENCY)
    _psp_df_ab["combined_score"] = (
        0.8 * _psp_df_ab["success_rate"] +
        0.1 * _psp_df_ab["cost_score"]   +
        0.1 * _psp_df_ab["latency_score"]
    )
    _best_lookup = (
        _psp_df_ab.sort_values("combined_score", ascending=False)
        .groupby(["country", "payment_method"])["psp"].first().to_dict()
    )
    _score_map = _psp_df_ab.groupby("psp")["combined_score"].mean().to_dict()

    def _ab_stats(group):
        n = len(group)
        if n == 0:
            return {}
        best_psps    = group.apply(lambda r: _best_lookup.get((r["country"], r["payment_method"])), axis=1)
        best_scores  = best_psps.map(_score_map).fillna(0)
        chosen_scores = group["selected_psp"].map(_score_map).fillna(0)
        regrets      = (best_scores - chosen_scores).clip(lower=0)
        is_optimal   = (regrets == 0)
        is_suboptimal = regrets >= 0.05
        avg_reward   = group["reward"].mean() if "reward" in group.columns and group["reward"].notna().any() else None
        return {
            "osr":            round(is_optimal.mean() * 100, 2),
            "avg_regret":     round(regrets.mean(), 6),
            "pct_suboptimal": round(is_suboptimal.mean() * 100, 2),
            "avg_reward":     round(avg_reward, 4) if avg_reward is not None else None,
        }

    total_ab = len(dl_ab)
    mid_ab   = total_ab // 2
    a_stats  = _ab_stats(dl_ab.iloc[:mid_ab])
    b_stats  = _ab_stats(dl_ab.iloc[mid_ab:mid_ab * 2])

    def _delta(a_val, b_val, lower_is_better=False):
        """Return (improved, delta_str). improved=True means B is better."""
        if a_val is None or b_val is None:
            return False, "—"
        delta = b_val - a_val
        improved = (delta > 0) if not lower_is_better else (delta < 0)
        sign = "+" if delta > 0 else ""
        cls  = "ab-delta" if improved else "ab-delta-neg"
        return improved, f'<span class="{cls}">{sign}{delta:.4g}</span>'

    osr_imp,    osr_d    = _delta(a_stats.get("osr"),            b_stats.get("osr"))
    reg_imp,    reg_d    = _delta(a_stats.get("avg_regret"),     b_stats.get("avg_regret"),     lower_is_better=True)
    sub_imp,    sub_d    = _delta(a_stats.get("pct_suboptimal"), b_stats.get("pct_suboptimal"), lower_is_better=True)
    rew_imp,    rew_d    = _delta(a_stats.get("avg_reward"),     b_stats.get("avg_reward"))

    def _val(stats, key, suffix=""):
        v = stats.get(key)
        return f"{v}{suffix}" if v is not None else "—"

    def _cell(stats, key, b_improved, suffix=""):
        v = stats.get(key)
        if v is None:
            return "—"
        txt = f"{v}{suffix}"
        return f'<span class="ab-improved">{txt}</span>' if b_improved else txt

    ab_col, insight_col = st.columns([1.6, 1])

    with ab_col:
        st.markdown(f"""
        <table class="ab-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th class="early">Early Learning<br><span style="font-weight:400;font-size:10px;">Txn 1 – {mid_ab:,}</span></th>
              <th class="late">Late Learning<br><span style="font-weight:400;font-size:10px;">Txn {mid_ab+1:,} – {mid_ab*2:,}</span></th>
              <th>Δ Change</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>OSR %</td>
              <td>{_val(a_stats, 'osr', '%')}</td>
              <td>{_cell(b_stats, 'osr', osr_imp, '%')}</td>
              <td>{osr_d}</td>
            </tr>
            <tr>
              <td>Avg Regret</td>
              <td>{_val(a_stats, 'avg_regret')}</td>
              <td>{_cell(b_stats, 'avg_regret', reg_imp)}</td>
              <td>{reg_d}</td>
            </tr>
            <tr>
              <td>% Suboptimal</td>
              <td>{_val(a_stats, 'pct_suboptimal', '%')}</td>
              <td>{_cell(b_stats, 'pct_suboptimal', sub_imp, '%')}</td>
              <td>{sub_d}</td>
            </tr>
            <tr>
              <td>Avg Reward</td>
              <td>{_val(a_stats, 'avg_reward')}</td>
              <td>{_cell(b_stats, 'avg_reward', rew_imp)}</td>
              <td>{rew_d}</td>
            </tr>
          </tbody>
        </table>
        """, unsafe_allow_html=True)

    with insight_col:
        improvements = sum([osr_imp, reg_imp, sub_imp, rew_imp])
        total_metrics = sum([1 for v in [a_stats.get("osr"), a_stats.get("avg_regret"),
                                          a_stats.get("pct_suboptimal"), a_stats.get("avg_reward")]
                              if v is not None])
        verdict = "Significantly better" if improvements == total_metrics else \
                  "Mostly better" if improvements >= total_metrics / 2 else "Mixed results"

        osr_lift = round(b_stats.get("osr", 0) - a_stats.get("osr", 0), 2) if a_stats.get("osr") else 0

        st.markdown(f"""
        <div class="card" style="height:100%; min-height:180px;">
          <div class="decision-label">Verdict</div>
          <div style="font-size:18px; font-weight:700; color:#0066FF; margin:6px 0 12px;">{verdict}</div>
          <div class="decision-label">Metrics Improved</div>
          <div style="font-size:22px; font-weight:700; color:#0A0F1E; margin:4px 0 12px;">{improvements} / {total_metrics}</div>
          <div class="decision-label">OSR Lift</div>
          <div style="font-size:22px; font-weight:700; color:{'#16A34A' if osr_lift >= 0 else '#DC2626'}; margin-top:4px;">
            {'+' if osr_lift >= 0 else ''}{osr_lift}%
          </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Run transaction_simulator.py first to generate decision_log.csv.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# LIVE ROUTING SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Route a Payment</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1])

with col1:
    country = st.selectbox("Country", list(COUNTRY_CONFIG.keys()))

with col2:
    methods = COUNTRY_CONFIG[country]["methods"]
    payment_method = st.selectbox("Payment Method", methods)

with col3:
    amount = st.number_input("Amount", min_value=1, value=1000, step=100)

with col4:
    currency = COUNTRY_CONFIG[country]["currency"]
    st.text_input("Currency", value=currency, disabled=True)

route_clicked = st.button("Route Now →", type="primary", use_container_width=False)

if route_clicked:
    txn = {
        "txn_id":         "live_demo",
        "country":        country,
        "payment_method": payment_method,
        "amount":         amount,
        "time_bucket":    "afternoon",
    }

    try:
        selected_psp, trace = route_transaction_with_trace(txn)
        if selected_psp is None:
            st.error("No PSP available for this route")
        else:
            pass  # proceed below
    except Exception as e:
        st.error(f"Routing error: {str(e)}")
        selected_psp = None
        trace = {}

    if selected_psp is not None:
        ranking   = trace.get("psp_ranking", [])
        reason    = trace.get("reason", "")
        is_opt    = selected_psp == trace.get("best_psp")
        top_score = ranking[0]["score"] if ranking else 0
        confidence = f"{top_score:.1%}" if isinstance(top_score, float) else str(top_score)
        badge = '<span class="badge-optimal">Optimal</span>' if is_opt else '<span class="badge-explore">Exploration</span>'

        # ── Simulate outcome ──────────────────────────────────────────────
        TAKE_RATE        = 0.015
        psp_success_rate = _psp_success_rate.get(selected_psp, 0.75)
        base_latency     = _psp_base_latency.get(selected_psp, 1000)

        outcome_success  = random.random() < psp_success_rate
        latency_ms       = round(base_latency * random.uniform(0.8, 1.2))

        revenue          = amount * TAKE_RATE
        psp_cost         = _psp_base_cost.get(selected_psp, 1.5)
        latency_penalty  = latency_ms / 100000
        if outcome_success:
            reward = revenue - psp_cost - latency_penalty
        else:
            failure_cost = revenue * 0.5
            reward = -(psp_cost + failure_cost + latency_penalty)
        reward = max(-100, min(100, round(reward, 4)))

        # Feed outcome back to the bandit
        update_bandit((country, payment_method), selected_psp, reward)

        # ── Outcome display ───────────────────────────────────────────────
        if outcome_success:
            outcome_html = '<span style="color:#16A34A; font-size:18px; font-weight:700;">✅ Payment Succeeded</span>'
            reward_html  = f'<span style="color:#16A34A; font-weight:700;">+${reward:.2f} profit</span>'
        else:
            outcome_html = '<span style="color:#DC2626; font-size:18px; font-weight:700;">❌ Payment Failed</span>'
            reward_html  = f'<span style="color:#DC2626; font-weight:700;">-${abs(reward):.2f} loss</span>'

        why_winner = trace.get("why_winner", "")

        st.markdown(f"""
        <div class="decision-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <div class="decision-label">Selected PSP</div>
              <div class="selected-psp">{selected_psp}</div>
              {f'<div style="font-size:12px; color:#64748B; font-style:italic; margin-top:4px;">{why_winner}</div>' if why_winner else ''}
              <div style="margin-top:10px;">{outcome_html}</div>
            </div>
            <div style="text-align:right;">
              {badge}
              <div style="margin-top:8px;">
                <div class="decision-label">Confidence</div>
                <div class="decision-value">{confidence}</div>
              </div>
            </div>
          </div>
          <div style="margin-top:16px; padding-top:16px; border-top:1px solid #F1F5F9;
                      display:flex; gap:32px;">
            <div>
              <div class="decision-label">Economic Reward</div>
              <div class="decision-value" style="margin-top:2px;">{reward_html}</div>
            </div>
            <div>
              <div class="decision-label">Latency</div>
              <div class="decision-value" style="margin-top:2px;">Processed in {latency_ms:,}ms</div>
            </div>
            <div>
              <div class="decision-label">Decision Reason</div>
              <div class="decision-value" style="font-weight:400; color:#475569; margin-top:2px;">{reason}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption("Bandit updated — system learned from this transaction")

        if ranking:
            st.markdown("**PSP Score Breakdown**")
            _detail_cols = [
                "psp", "local_sample", "ucb_bonus",
                "cost_score", "latency_score", "q_bonus", "final_score",
            ]
            _available = [c for c in _detail_cols if c in ranking[0]]
            rdf = pd.DataFrame(ranking)[_available].copy()

            # Format display columns
            rdf = rdf.rename(columns={
                "psp":          "PSP",
                "local_sample": "Success Est.",
                "ucb_bonus":    "UCB Bonus",
                "cost_score":   "Cost Score",
                "latency_score":"Latency Score",
                "q_bonus":      "Q Bonus",
                "final_score":  "Final Score",
            })
            if "Success Est." in rdf.columns:
                rdf["Success Est."] = rdf["Success Est."].apply(lambda x: f"{x:.1%}")
            for col in ["UCB Bonus", "Cost Score", "Latency Score", "Q Bonus"]:
                if col in rdf.columns:
                    rdf[col] = rdf[col].round(3 if col == "UCB Bonus" else 2)
            if "Final Score" in rdf.columns:
                rdf["Final Score"] = rdf["Final Score"].round(3)

            rdf = rdf.sort_values("Final Score", ascending=False).reset_index(drop=True)
            top_score = rdf["Final Score"].iloc[0] if "Final Score" in rdf.columns else None

            def _colour_final(row):
                styles = [""] * len(row)
                if "Final Score" in row.index:
                    fs_idx = row.index.get_loc("Final Score")
                    if row["Final Score"] == top_score:
                        styles[fs_idx] = "color: #16A34A; font-weight: 700"
                return styles

            rdf.index = range(1, len(rdf) + 1)
            st.dataframe(rdf.style.apply(_colour_final, axis=1), use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# WHAT-IF SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">What-if Simulator</div>', unsafe_allow_html=True)
st.markdown('<div class="ab-subtitle">See how routing changes under different conditions</div>', unsafe_allow_html=True)

wif_col1, wif_col2, wif_col3 = st.columns(3)

with wif_col1:
    st.markdown("**Success Rate Multiplier** — Simulate if PSPs perform better or worse")
    sr_mult = st.slider("Success Rate", 0.5, 1.5, 1.0, 0.1, key="sr_mult")

with wif_col2:
    st.markdown("**Cost Multiplier** — Simulate if PSP costs increase or decrease")
    cost_mult = st.slider("Cost Multiplier", 0.5, 2.0, 1.0, 0.1, key="cost_mult")

with wif_col3:
    st.markdown("**Transaction Amount**")
    wif_amount = st.slider("Amount ($)", 100, 10000, 1000, 100, key="sim_amount")

run_sim = st.button("Run Simulation", type="primary")

if run_sim:
    # Get PSPs available for the currently selected country + method
    wif_psps_rows = psp_df[
        (psp_df["country"] == country) & (psp_df["payment_method"] == payment_method)
    ].copy()

    if wif_psps_rows.empty:
        st.warning(f"No PSP data found for {country} / {payment_method}.")
    else:
        TAKE_RATE    = 0.015
        _MAX_COST    = 3.0
        _MAX_LATENCY = 2500

        sim_rows = []
        for _, row in wif_psps_rows.iterrows():
            psp = row["psp"]

            # Apply multipliers (clamp success rate to [0, 1])
            sim_sr      = min(1.0, row["success_rate"] * sr_mult)
            sim_cost    = row["base_cost"] * cost_mult
            sim_latency = row["latency_ms"]   # latency unchanged

            # Scoring formula — same as routing_engine
            cost_score    = 1 - (sim_cost    / _MAX_COST)
            latency_score = 1 - (sim_latency / _MAX_LATENCY)
            combined_score = 0.8 * sim_sr + 0.1 * cost_score + 0.1 * latency_score

            # Expected economic reward under simulation
            revenue          = wif_amount * TAKE_RATE
            latency_penalty  = sim_latency / 100000
            exp_reward = (
                sim_sr   * (revenue - sim_cost - latency_penalty) +
                (1 - sim_sr) * -(sim_cost + revenue * 0.5 + latency_penalty)
            )

            # Baseline (no multipliers) for comparison
            base_sr      = row["success_rate"]
            base_cost_v  = row["base_cost"]
            base_cs      = 1 - (base_cost_v / _MAX_COST)
            base_ls      = 1 - (sim_latency / _MAX_LATENCY)
            base_score   = 0.8 * base_sr + 0.1 * base_cs + 0.1 * base_ls

            sim_rows.append({
                "PSP":           psp,
                "Base Score":    round(base_score, 4),
                "Sim Score":     round(combined_score, 4),
                "Score Δ":       round(combined_score - base_score, 4),
                "Sim SR %":      f"{sim_sr*100:.1f}%",
                "Sim Cost ($)":  round(sim_cost, 2),
                "Exp Reward":    round(exp_reward, 4),
                "_sim_score":    combined_score,
                "_base_score":   base_score,
            })

        sim_df = pd.DataFrame(sim_rows).sort_values("_sim_score", ascending=False).reset_index(drop=True)
        sim_df.index += 1

        baseline_winner = sim_df.sort_values("_base_score", ascending=False).iloc[0]["PSP"]
        sim_winner      = sim_df.iloc[0]["PSP"]
        routing_changed = sim_winner != baseline_winner

        # ── Headline ─────────────────────────────────────────────────────
        if routing_changed:
            st.markdown(f"""
            <div style="background:#FEF9C3; border:1px solid #FDE68A; border-left:4px solid #F59E0B;
                        border-radius:10px; padding:14px 20px; margin-bottom:1rem;">
              <span style="font-weight:700; color:#B45309;">Routing would change</span>
              <span style="color:#92400E;"> — Baseline selects <strong>{baseline_winner}</strong>,
              simulation selects <strong>{sim_winner}</strong> under these conditions.</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:#DCFCE7; border:1px solid #BBF7D0; border-left:4px solid #00C853;
                        border-radius:10px; padding:14px 20px; margin-bottom:1rem;">
              <span style="font-weight:700; color:#15803D;">Routing unchanged</span>
              <span style="color:#166534;"> — <strong>{sim_winner}</strong> remains the top PSP
              under these conditions.</span>
            </div>
            """, unsafe_allow_html=True)

        # ── Ranked table ──────────────────────────────────────────────────
        display_sim = sim_df[["PSP", "Base Score", "Sim Score", "Score Δ", "Sim SR %", "Sim Cost ($)", "Exp Reward"]].copy()

        def colour_sim(row):
            styles = [""] * len(row)
            delta_idx  = row.index.get_loc("Score Δ")
            reward_idx = row.index.get_loc("Exp Reward")
            delta = row["Score Δ"]
            styles[delta_idx] = (
                "color: #16A34A; font-weight: 600" if delta > 0
                else "color: #DC2626; font-weight: 600" if delta < 0
                else ""
            )
            reward = row["Exp Reward"]
            styles[reward_idx] = (
                "color: #16A34A; font-weight: 600" if reward > 0
                else "color: #DC2626; font-weight: 600"
            )
            return styles

        st.dataframe(
            display_sim.style.apply(colour_sim, axis=1),
            use_container_width=True,
            height=min(420, 60 + len(display_sim) * 38),
        )

        # ── Chart: base vs simulated score per PSP ────────────────────────
        chart_data = pd.concat([
            sim_df[["PSP", "_base_score"]].rename(columns={"_base_score": "Score"}).assign(Scenario="Baseline"),
            sim_df[["PSP", "_sim_score"]].rename(columns={"_sim_score": "Score"}).assign(Scenario="Simulation"),
        ])
        bar = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 1]), title="Combined Score"),
                y=alt.Y("PSP:N", sort="-x", title=None),
                color=alt.Color("Scenario:N", scale=alt.Scale(
                    domain=["Baseline", "Simulation"],
                    range=["#CBD5E1", "#0066FF"],
                )),
                tooltip=["PSP:N", "Scenario:N", alt.Tooltip("Score:Q", format=".4f")],
            )
            .properties(height=max(200, len(sim_df) * 30), title="PSP Score: Baseline vs Simulation")
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor="#64748B", titleColor="#64748B", grid=False)
            .configure_title(fontSize=13, fontWeight=600, color="#0F172A")
        )
        st.altair_chart(bar, use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
# PSP HEALTH MONITOR
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">PSP Health Monitor</div>', unsafe_allow_html=True)

if os.path.exists(DECISION_LOG_PATH):
    dl_health = load_decision_log()
    dl_health["outcome_bool"] = dl_health["outcome"].apply(
        lambda x: True if str(x).lower() == "success" else False
    )

    # Baseline success rates from payment_data.csv
    baseline = psp_df.groupby("psp")["success_rate"].mean().to_dict()

    # PSP → region lookup
    health_rows = []
    for psp, group in dl_health.groupby("selected_psp"):
        if len(group) < 50:
            continue

        recent        = group.tail(200)
        current_rate  = recent["outcome_bool"].mean()
        baseline_rate = baseline.get(psp)
        if baseline_rate is None:
            continue

        diff = current_rate - baseline_rate
        if diff < -0.10:
            trend  = "Degrading"
            status = "Warning"
        elif diff > 0.10:
            trend  = "Improving"
            status = "Healthy"
        else:
            trend  = "Stable"
            status = "Healthy"

        health_rows.append({
            "PSP":      psp,
            "Region":   _psp_region.get(psp, "—"),
            "Baseline": f"{baseline_rate*100:.1f}%",
            "Current":  f"{current_rate*100:.1f}%",
            "Trend":    trend,
            "Status":   status,
            "_diff":    diff,
        })

    if health_rows:
        health_df = pd.DataFrame(health_rows).sort_values("_diff").reset_index(drop=True)
        health_df.index += 1

        def colour_status(row):
            styles = [""] * len(row)
            status_idx = row.index.get_loc("Status")
            trend_idx  = row.index.get_loc("Trend")
            if row["Status"] == "Warning":
                styles[status_idx] = "color: #CA8A04; font-weight: 600"
                styles[trend_idx]  = "color: #CA8A04; font-weight: 600"
            else:
                styles[status_idx] = "color: #16A34A; font-weight: 600"
            return styles

        display_health = health_df.drop(columns=["_diff"])
        st.dataframe(
            display_health.style.apply(colour_status, axis=1),
            use_container_width=True,
            height=min(400, 40 + len(health_df) * 35),
        )
    else:
        st.info("Not enough transaction data yet — run more simulations.")
else:
    st.info("Run transaction_simulator.py first to generate decision_log.csv")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">System Performance</div>', unsafe_allow_html=True)

if os.path.exists(DECISION_LOG_PATH):
    dl = load_decision_log()
    best_lookup = (
        psp_df.sort_values("success_rate", ascending=False)
        .groupby(["country", "payment_method"])["psp"]
        .first()
        .to_dict()
    )
    dl["best_psp"]   = dl.apply(lambda r: best_lookup.get((r["country"], r["payment_method"])), axis=1)
    dl["is_optimal"] = (dl["selected_psp"] == dl["best_psp"]).astype(int)
    dl["batch"]      = dl.index // 200
    dl["txn_number"] = (dl["batch"] + 1) * 200

    batch_osr = dl.groupby(["batch", "txn_number"])["is_optimal"].mean().reset_index()
    batch_osr["osr_pct"] = batch_osr["is_optimal"] * 100
    batch_osr["trend"]   = batch_osr["osr_pct"].rolling(3, min_periods=1).mean()

    chart_data = batch_osr[["txn_number", "osr_pct", "trend"]].melt(
        id_vars="txn_number",
        value_vars=["osr_pct", "trend"],
        var_name="Series",
        value_name="OSR %"
    )
    chart_data["Series"] = chart_data["Series"].map({
        "osr_pct": "OSR %",
        "trend":   "Trend (3-batch avg)"
    })

    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("txn_number:Q", title="Transaction Number"),
            y=alt.Y("OSR %:Q", scale=alt.Scale(domain=[50, 100]), title="OSR %"),
            color=alt.Color("Series:N", scale=alt.Scale(
                domain=["OSR %", "Trend (3-batch avg)"],
                range=["#0066FF", "#94A3B8"]
            )),
            tooltip=["txn_number:Q", "Series:N", alt.Tooltip("OSR %:Q", format=".1f")]
        )
        .properties(title="Optimal Selection Rate Improving Over Time", height=280)
        .configure_view(strokeWidth=0)
        .configure_axis(grid=True, gridColor="#F1F5F9", labelColor="#64748B", titleColor="#64748B")
        .configure_title(fontSize=14, fontWeight=600, color="#0F172A")
    )

    st.altair_chart(chart, use_container_width=True)
    st.caption("System gets smarter with every transaction")
else:
    st.info("Run transaction_simulator.py to generate the learning curve data.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# PSP INTELLIGENCE TABLE
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">PSP Intelligence</div>', unsafe_allow_html=True)

psp_perf = df.groupby("chosen_psp").agg(
    volume=("txn_id",    "count"),
    osr=("is_optimal",   "mean"),
    avg_regret=("regret","mean"),
).reset_index()

psp_meta = psp_df.groupby("psp")["success_rate"].mean().reset_index()
psp_meta.columns = ["chosen_psp", "success_rate"]

psp_perf = psp_perf.merge(psp_meta, on="chosen_psp", how="left")

# Build PSP → region by looking up which countries each PSP appears in
psp_perf["Region"]         = psp_perf["chosen_psp"].map(_psp_region).fillna("—")
psp_perf["OSR %"]          = psp_perf["osr"].apply(lambda x: f"{x*100:.1f}%")
psp_perf["Success Rate %"] = psp_perf["success_rate"].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")
psp_perf["Avg Regret"]     = psp_perf["avg_regret"].round(4)

# Keep numeric OSR for colour coding before converting to string
psp_perf["_osr_num"] = psp_perf["osr"] * 100

display = psp_perf[["chosen_psp", "Region", "Success Rate %", "volume", "OSR %", "Avg Regret"]].copy()
display.columns = ["PSP", "Region", "Success Rate %", "Volume", "OSR %", "Avg Regret"]
display = display.sort_values("Success Rate %", ascending=False).reset_index(drop=True)
display.index += 1

display["_osr_num"] = psp_perf["_osr_num"].values

def colour_osr_row(row):
    val = row["_osr_num"]
    colour = "#16A34A" if val >= 80 else ("#CA8A04" if val >= 60 else "#DC2626")
    styles = [""] * len(row)
    osr_idx = row.index.get_loc("OSR %")
    styles[osr_idx] = f"color: {colour}; font-weight: 600"
    return styles

styled = display.style.apply(colour_osr_row, axis=1)

st.dataframe(
    styled,
    column_config={"_osr_num": None},  # hide the helper column
    use_container_width=True,
    height=420,
)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# GEOGRAPHIC INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Geographic Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="ab-subtitle">Performance across 14 markets</div>', unsafe_allow_html=True)

# Build region-level data from replay_results.csv + psp_df
_country_region = {c: r for c, r in REGION_MAP.items()}
_region_countries = {}
for country, region in _country_region.items():
    _region_countries.setdefault(region, []).append(country)

# Join replay df with region via chosen_psp → country lookup from psp_df
# psp_df has country per PSP; map chosen_psp → primary country → region
_psp_primary_country = psp_df.groupby("psp")["country"].first().to_dict()

geo_df = df.copy()
geo_df["region"] = geo_df["chosen_psp"].map(_psp_primary_country).map(_country_region)

# Also pull avg reward if available
has_reward = "reward" not in df.columns  # replay_results doesn't have reward; load from decision_log
_dl_reward = None
if os.path.exists(DECISION_LOG_PATH):
    _tmp_dl = load_decision_log()
    _dl_reward = _tmp_dl[["txn_id", "reward"]] if "reward" in _tmp_dl.columns else _tmp_dl[["txn_id"]]

if _dl_reward is not None and "reward" in _dl_reward.columns:
    geo_df = geo_df.merge(_dl_reward[["txn_id", "reward"]], on="txn_id", how="left")

# Best PSP per region: highest avg OSR
_region_best_psp = (
    geo_df.groupby(["region", "chosen_psp"])["is_optimal"].mean()
    .reset_index()
    .sort_values("is_optimal", ascending=False)
    .groupby("region")["chosen_psp"].first()
    .to_dict()
)

geo_summary_rows = []
for region in ["Africa", "APAC", "Europe", "Americas"]:
    region_slice = geo_df[geo_df["region"] == region]
    if region_slice.empty:
        continue
    countries    = sorted(_region_countries.get(region, []))
    total_txns_r = len(region_slice)
    avg_osr_r    = round(region_slice["is_optimal"].mean() * 100, 1)
    best_psp_r   = _region_best_psp.get(region, "—")
    avg_reward_r = (
        round(region_slice["reward"].mean(), 4)
        if "reward" in region_slice.columns and region_slice["reward"].notna().any()
        else None
    )
    geo_summary_rows.append({
        "Region":            region,
        "Countries":         ", ".join(countries),
        "Transactions":      total_txns_r,
        "OSR %":             avg_osr_r,
        "Best PSP":          best_psp_r,
        "Avg Reward":        avg_reward_r if avg_reward_r is not None else "—",
        "_osr_num":          avg_osr_r,
    })

if geo_summary_rows:
    # ── 4 region KPI cards ───────────────────────────────────────────────
    region_colors = {"Africa": "#F97316", "APAC": "#7C3AED", "Europe": "#0066FF", "Americas": "#00C853"}
    cards_html = '<div style="display:flex; gap:16px; margin-bottom:1.5rem;">'
    for row_g in geo_summary_rows:
        color = region_colors.get(row_g["Region"], "#0066FF")
        osr_v = row_g["OSR %"]
        osr_color = "#16A34A" if osr_v >= 80 else ("#CA8A04" if osr_v >= 60 else "#DC2626")
        cards_html += f"""
        <div style="background:white; border-radius:12px; padding:16px 22px;
                    box-shadow:0 4px 16px rgba(0,0,0,0.08); flex:1;
                    border-top:4px solid {color}; text-align:center;">
          <div style="font-size:11px; font-weight:600; color:#94A3B8;
                      text-transform:uppercase; letter-spacing:0.8px;">{row_g["Region"]}</div>
          <div style="font-size:26px; font-weight:700; color:{osr_color};
                      margin:6px 0 2px; letter-spacing:-0.5px;">{osr_v}%</div>
          <div style="font-size:11px; color:#64748B;">OSR</div>
          <div style="font-size:12px; color:#94A3B8; margin-top:4px;">{row_g["Transactions"]:,} txns</div>
        </div>"""
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    # ── Geographic table ─────────────────────────────────────────────────
    geo_table = pd.DataFrame(geo_summary_rows)
    geo_display = geo_table[["Region", "Countries", "Transactions", "OSR %", "Best PSP", "Avg Reward", "_osr_num"]].copy()

    def colour_geo_osr(row):
        styles = [""] * len(row)
        osr_idx = row.index.get_loc("OSR %")
        val = row["_osr_num"]
        colour = "#16A34A" if val >= 80 else ("#CA8A04" if val >= 60 else "#DC2626")
        styles[osr_idx] = f"color: {colour}; font-weight: 700; font-size: 15px"
        return styles

    st.dataframe(
        geo_display.style.apply(colour_geo_osr, axis=1),
        column_config={"_osr_num": None},
        use_container_width=True,
        height=210,
    )
else:
    st.info("Run transaction_simulator.py and replay_engine.py to generate geographic data.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# HOW ROUTEIQ WORKS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">How RouteIQ Works</div>', unsafe_allow_html=True)

with st.expander("Learn how the AI makes decisions"):
    hw_cols = st.columns(5)

    explanations = [
        ("🧠", "The Brain", "Hierarchical Bandit",
         "RouteIQ learns at 3 levels simultaneously — per country, per region (Africa/APAC/Europe/Americas), and globally. When Nigeria learns Fincra is best, Kenya benefits immediately."),
        ("⚡", "The Decision", "Thompson Sampling + UCB",
         "For every payment, RouteIQ samples from each PSP's performance distribution. PSPs with less data get an exploration bonus — ensuring the system never stops learning."),
        ("📈", "Long-term Thinking", "Q-Learning",
         "RouteIQ doesn't just optimize each transaction — it considers future consequences. Like a chess player thinking 10 moves ahead."),
        ("🛡️", "Self-Protection", "Circuit Breakers + Drift Detection",
         "If a PSP starts failing, RouteIQ detects it within 10–20 transactions and automatically reduces or stops traffic. No human intervention needed."),
        ("💰", "Business Optimization", "Economic Reward",
         "RouteIQ optimizes for profit, not just success rate. Every decision considers revenue, PSP cost, and latency penalty simultaneously."),
    ]

    for col, (icon, title, subtitle, desc) in zip(hw_cols, explanations):
        with col:
            st.markdown(f"""
            <div style="background:white; border-radius:12px; padding:20px 16px;
                        box-shadow:0 2px 10px rgba(0,0,0,0.07); height:100%;
                        border-top:3px solid #0066FF; text-align:center;">
              <div style="font-size:28px; margin-bottom:8px;">{icon}</div>
              <div style="font-size:13px; font-weight:700; color:#0A0F1E;
                          margin-bottom:2px;">{title}</div>
              <div style="font-size:10px; font-weight:600; color:#0066FF;
                          text-transform:uppercase; letter-spacing:0.5px;
                          margin-bottom:10px;">{subtitle}</div>
              <div style="font-size:12px; color:#475569; line-height:1.55;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# TRANSACTION EXPLORER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Transaction Explorer</div>', unsafe_allow_html=True)

left, right = st.columns([2.5, 1])

with left:
    drop_cols = ["psp_ranking"]
    explorer_df = df.drop(columns=drop_cols, errors="ignore").sort_values("regret", ascending=False).reset_index(drop=True)

    if "decision_quality" in explorer_df.columns:
        def colour_dq_row(row):
            styles = [""] * len(row)
            if "decision_quality" not in row.index:
                return styles
            dq_idx = row.index.get_loc("decision_quality")
            q = row["decision_quality"]
            if q == "Optimal":
                styles[dq_idx] = "color: #16A34A; font-weight: 600"
            elif q == "Near-optimal":
                styles[dq_idx] = "color: #0066FF; font-weight: 600"
            elif q == "Suboptimal":
                styles[dq_idx] = "color: #F97316; font-weight: 600"
            return styles

        st.dataframe(
            explorer_df.style.apply(colour_dq_row, axis=1),
            height=420,
            use_container_width=True,
        )
    else:
        st.dataframe(explorer_df, height=420, use_container_width=True)

with right:
    st.markdown("**Inspect Decision**")
    txn_id = st.selectbox("Transaction", df["txn_id"].astype(str))
    row    = df[df["txn_id"].astype(str) == txn_id].iloc[0]

    if row["is_optimal"] == 1:
        status_badge = '<span class="badge-optimal">Optimal</span>'
    elif row["regret"] < 0.02:
        status_badge = '<span class="badge-explore">Near Optimal</span>'
    else:
        status_badge = '<span style="background:#FEE2E2;color:#DC2626;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">Suboptimal</span>'

    st.markdown(f"""
    <div class="card">
      <div class="decision-label">Txn ID</div>
      <div class="decision-value" style="font-size:12px; margin-bottom:12px;">{row['txn_id']}</div>
      <div class="decision-label">Chosen PSP</div>
      <div class="decision-value" style="color:#0066FF; margin-bottom:12px;">{row['chosen_psp']}</div>
      <div class="decision-label">Best PSP</div>
      <div class="decision-value" style="margin-bottom:12px;">{row['best_psp']}</div>
      <div class="decision-label">Regret</div>
      <div class="decision-value" style="margin-bottom:12px;">{round(row['regret'], 4)}</div>
      <div class="decision-label">Status</div>
      <div style="margin-top:4px;">{status_badge}</div>
    </div>
    """, unsafe_allow_html=True)

    if "psp_ranking" in row and pd.notna(row.get("psp_ranking")):
        try:
            raw_ranking = row["psp_ranking"]
            # Stored as pipe-separated PSP names (from transaction_simulator)
            # or as JSON list of dicts (from route_transaction_with_trace)
            if isinstance(raw_ranking, str) and raw_ranking.startswith("["):
                ranking_data = json.loads(raw_ranking)
            else:
                # pipe-separated names only — no detail available
                ranking_data = None

            if ranking_data and isinstance(ranking_data[0], dict):
                _detail_cols = [
                    "psp", "local_sample", "ucb_bonus",
                    "cost_score", "latency_score", "q_bonus", "final_score",
                ]
                _available = [c for c in _detail_cols if c in ranking_data[0]]
                idf = pd.DataFrame(ranking_data)[_available].rename(columns={
                    "psp":          "PSP",
                    "local_sample": "Success Est.",
                    "ucb_bonus":    "UCB Bonus",
                    "cost_score":   "Cost Score",
                    "latency_score":"Latency Score",
                    "q_bonus":      "Q Bonus",
                    "final_score":  "Final Score",
                })
                if "Success Est." in idf.columns:
                    idf["Success Est."] = idf["Success Est."].apply(lambda x: f"{x:.1%}")
                for col in ["UCB Bonus", "Cost Score", "Latency Score", "Q Bonus"]:
                    if col in idf.columns:
                        idf[col] = idf[col].round(3 if col == "UCB Bonus" else 2)
                if "Final Score" in idf.columns:
                    idf["Final Score"] = idf["Final Score"].round(3)
                idf = idf.sort_values("Final Score", ascending=False).reset_index(drop=True)
                top_score_i = idf["Final Score"].iloc[0] if "Final Score" in idf.columns else None

                def _colour_final_i(r):
                    styles = [""] * len(r)
                    if "Final Score" in r.index and r["Final Score"] == top_score_i:
                        styles[r.index.get_loc("Final Score")] = "color: #16A34A; font-weight: 700"
                    return styles

                idf.index = range(1, len(idf) + 1)
                st.markdown("**PSP Score Breakdown**")
                st.dataframe(idf.style.apply(_colour_final_i, axis=1), use_container_width=True)
            elif isinstance(raw_ranking, str) and "|" in raw_ranking:
                psps = [p.strip() for p in raw_ranking.split("|") if p.strip()]
                st.markdown("**PSP Ranking**")
                st.dataframe(pd.DataFrame({"Rank": range(1, len(psps)+1), "PSP": psps}),
                             use_container_width=True, hide_index=True)
        except Exception:
            pass
