"""
CivicAI Admin Dashboard — Production
Run: python -m streamlit run admin-dashboard/app.py
"""

import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from supabase import create_client
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="CivicAI Admin", page_icon="📍", layout="wide")

st.markdown("""
<style>
  [data-testid="stSidebar"] { background:#0f172a; }
  [data-testid="stSidebar"] * { color:#e2e8f0 !important; }
  [data-testid="stSidebar"] hr { border-color:#1e293b; }
  .metric-card {
    background:#1e293b; border-radius:10px; padding:16px 20px;
    border-left:4px solid #3b82f6; margin-bottom:6px;
  }
  .metric-card .lbl { font-size:.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.06em; }
  .metric-card .val { font-size:1.9rem; font-weight:700; margin-top:2px; }
  .badge { padding:2px 9px; border-radius:20px; font-size:.71rem; font-weight:600; display:inline-block; }
  .b-critical    { background:#ef4444; color:#fff; }
  .b-high        { background:#f97316; color:#fff; }
  .b-medium      { background:#eab308; color:#1c1917; }
  .b-low         { background:#22c55e; color:#fff; }
  .b-pending     { background:#fbbf24; color:#1c1917; }
  .b-in-progress { background:#3b82f6; color:#fff; }
  .b-resolved    { background:#22c55e; color:#fff; }
  .complaint-card {
    background:#fff; border:1px solid #e2e8f0; border-radius:10px;
    padding:14px 18px; margin-bottom:4px;
  }
  .complaint-card:hover { border-color:#3b82f6; box-shadow:0 2px 8px rgba(59,130,246,.1); }
  .complaint-title { font-size:.95rem; font-weight:700; color:#0f172a; }
  .complaint-addr  { font-size:.8rem; color:#475569; margin-top:3px; }
  .complaint-meta  { font-size:.76rem; color:#94a3b8; margin-top:5px; }
  .resolved-card   { background:#f0fdf4 !important; border-color:#bbf7d0 !important; }
  .cat-header { font-size:1rem; font-weight:700; color:#1e293b; padding:8px 0 4px 0; border-bottom:2px solid #e2e8f0; margin:16px 0 8px 0; }
  div[data-testid="stTabs"] button { font-size:.9rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ── SUPABASE ──────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

db = get_client()

SEVERITY_COLOR = {
    "critical": "#ef4444",
    "high":     "#f97316",
    "medium":   "#eab308",
    "low":      "#22c55e",
}
STATUS_OPTIONS = ["pending", "in-progress", "resolved"]
CAT_ICON = {"pothole": "🕳️", "waterlogging": "💧", "garbage": "🗑️"}

def sev_color(s) -> str:
    if not s or str(s).lower() in ("none", "nan", ""):
        return "#94a3b8"
    return SEVERITY_COLOR.get(str(s).lower(), "#94a3b8")

def safe_sev(s) -> str:
    if not s or str(s).lower() in ("none", "nan", ""):
        return "unknown"
    return str(s).lower()

def safe_status(s) -> str:
    if not s or str(s).lower() in ("none", "nan", ""):
        return "pending"
    return str(s).lower()

def fmt_date(val) -> str:
    if not val:
        return "—"
    try:
        dt = datetime.fromisoformat(str(val).replace("Z",""))
        return dt.strftime("%d %b %Y, %I:%M %p").lstrip("0")
    except Exception:
        return str(val)[:16]

def short_address(addr: str) -> str:
    if not addr or addr.startswith("GPS:"):
        return addr
    parts = [p.strip() for p in addr.split(",")]
    clean = [p for p in parts if p and not p.isdigit() and len(p) > 2]
    return ", ".join(clean[:4])

# ── DATA — no cache, always fresh ─────────────────────────
def load_data() -> pd.DataFrame:
    try:
        res = db.table("reports").select(
            "id, lat, lng, address, description, category, severity, "
            "sentiment_label, priority_score, status, duplicate_of, created_at, user_id"
        ).execute()
        df = pd.DataFrame(res.data)
        if df.empty:
            return df
        df["priority_score"] = pd.to_numeric(df["priority_score"], errors="coerce").fillna(0)
        df["address"] = df["address"].apply(short_address)

        # Fetch user names and merge
        try:
            users_res = db.table("users").select("id, name, email").execute()
            users_df  = pd.DataFrame(users_res.data)
            if not users_df.empty:
                users_df = users_df.rename(columns={"id": "user_id"})
                users_df["display_name"] = users_df["name"].fillna(users_df["email"].str.split("@").str[0])
                df = df.merge(users_df[["user_id","display_name"]], on="user_id", how="left")
            else:
                df["display_name"] = "Citizen"
        except Exception:
            df["display_name"] = "Citizen"

        df["display_name"] = df["display_name"].fillna("Citizen")
        return df
    except Exception as e:
        st.error(f"Supabase error: {e}")
        return pd.DataFrame()


def get_all_group_ids(report_id: str) -> list:
    """Query Supabase directly to get ALL IDs in a duplicate group."""
    # Get the report to find its root
    row = db.table("reports").select("id,duplicate_of").eq("id", report_id).execute()
    if not row.data:
        return [report_id]
    root_id = row.data[0].get("duplicate_of") or report_id
    # Get all reports pointing to root + the root itself
    children = db.table("reports").select("id").eq("duplicate_of", root_id).execute()
    ids = set([root_id] + [r["id"] for r in children.data])
    return list(ids)


def patch_status(report_id: str, new_status: str) -> int:
    """Update status for a report AND every report in the same duplicate group."""
    linked_ids = get_all_group_ids(report_id)
    updated = 0
    for rid in linked_ids:
        res = db.table("reports").update({"status": new_status}).eq("id", rid).execute()
        if res.data:
            updated += 1
    if updated > 0:
        st.session_state.clear()
    return updated


# ── MAP ───────────────────────────────────────────────────
def build_map(map_df: pd.DataFrame) -> folium.Map:
    m = folium.Map(
        location=[21.1458, 79.0882],
        zoom_start=13, min_zoom=3, max_zoom=18,
        tiles=None, prefer_canvas=True
    )
    folium.TileLayer(
        tiles="OpenStreetMap",
        control=False
    ).add_to(m)

    if map_df.empty:
        return m

    valid = map_df.dropna(subset=["lat", "lng"])
    if valid.empty:
        return m

    # Only unresolved reports show on heatmap zones
    unresolved = valid[valid["status"] != "resolved"]

    if not unresolved.empty:
        HeatMap(
            [[r["lat"], r["lng"], max(float(r["priority_score"]), 0.1)] for _, r in unresolved.iterrows()],
            radius=25, blur=18, max_zoom=13, min_opacity=0.4,
            gradient={0.0: "#22c55e", 0.4: "#eab308", 0.7: "#f97316", 1.0: "#ef4444"}
        ).add_to(m)

    for _, r in valid.iterrows():
        color = sev_color(safe_sev(r.get("severity")))
        name  = r.get("display_name", "Citizen")
        popup = (
            f"<div style='font-family:sans-serif;min-width:210px'>"
            f"<b style='font-size:.95rem'>{CAT_ICON.get(r['category'],'')} {str(r['category']).title()}</b>"
            f"<span style='float:right;background:{color};color:#fff;"
            f"padding:1px 8px;border-radius:10px;font-size:.7rem'>{r.get('severity','—')}</span><br>"
            f"<span style='color:#64748b;font-size:.78rem'>📍 {r['address']}</span><br><br>"
            f"<b>Reported by:</b> {name}<br>"
            f"<b>Priority:</b> {round(r['priority_score'], 2)}<br>"
            f"<b>Status:</b> {r['status']}<br>"
            f"<b>Submitted:</b> {fmt_date(r.get('created_at'))}<br>"
            f"<b>GPS:</b> {r['lat']:.5f}, {r['lng']:.5f}"
            f"</div>"
        )
        folium.CircleMarker(
            location=[r["lat"], r["lng"]],
            radius=8, color=color, fill=True,
            fill_color=color, fill_opacity=0.85,
            popup=folium.Popup(popup, max_width=260),
            tooltip=f"{str(r['category']).title()} · {r.get('severity','—')}"
        ).add_to(m)
    return m


# ── LOAD ──────────────────────────────────────────────────
raw_df = load_data()

# ── SIDEBAR ───────────────────────────────────────────────
st.sidebar.markdown("## 📍 CivicAI")
st.sidebar.caption("Nagpur Municipal Admin Panel")
st.sidebar.divider()

cat_f = st.sidebar.multiselect("Category", ["pothole","waterlogging","garbage"], default=["pothole","waterlogging","garbage"])
sta_f = st.sidebar.multiselect("Status",   ["pending","in-progress","resolved"], default=["pending","in-progress","resolved"])
sev_f = st.sidebar.multiselect("Severity", ["critical","high","medium","low"],   default=["critical","high","medium","low"])

df = raw_df.copy()
if not df.empty:
    if "category" in df.columns:
        df = df[df["category"].isin(cat_f)]
    if "status" in df.columns:
        df = df[df["status"].isin(sta_f)]
    if "severity" in df.columns:
        # include rows where severity is None/NaN too
        df = df[df["severity"].isin(sev_f) | df["severity"].isna()]

st.sidebar.divider()
st.sidebar.caption(f"Showing {len(df)} / {len(raw_df)} reports")
if st.sidebar.button("🔄 Refresh"):
    st.session_state.clear()
    st.rerun()

# ── TABS ──────────────────────────────────────────────────
t1, t2, t3 = st.tabs(["📊 Overview", "🗺️ Map", "✅ Manage Reports"])


# ══════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════
with t1:
    st.markdown("### CivicAI — Admin Control Panel")
    st.caption("Live civic issue monitoring · Nagpur Municipal Corporation")
    st.divider()

    total    = len(raw_df)
    pending  = len(raw_df[raw_df["status"]=="pending"])     if not raw_df.empty else 0
    in_prog  = len(raw_df[raw_df["status"]=="in-progress"]) if not raw_df.empty else 0
    resolved = len(raw_df[raw_df["status"]=="resolved"])    if not raw_df.empty else 0
    critical = len(raw_df[raw_df["priority_score"]>=0.7])   if not raw_df.empty else 0
    citizens = raw_df["user_id"].nunique()                  if not raw_df.empty else 0

    for col, label, val, color in zip(
        st.columns(6),
        ["Total","Pending","In Progress","Resolved","Critical","Citizens"],
        [total, pending, in_prog, resolved, critical, citizens],
        ["#3b82f6","#fbbf24","#8b5cf6","#22c55e","#ef4444","#06b6d4"]
    ):
        col.markdown(f"""
        <div class="metric-card" style="border-left-color:{color}">
          <div class="lbl">{label}</div>
          <div class="val" style="color:{color}">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    if not df.empty:
        # Category breakdown with bar chart
        ca, cb = st.columns([1, 2])
        with ca:
            st.markdown("**Category Breakdown**")
            cc = df["category"].value_counts().reset_index()
            cc.columns = ["Category", "Count"]
            st.dataframe(cc, use_container_width=True, hide_index=True)
        with cb:
            st.markdown("**Complaints by Category**")
            st.bar_chart(cc.set_index("Category"))

    st.divider()

    # Complaints grouped by category
    st.markdown("**All Complaints by Category**")
    if not df.empty:
        for cat in ["pothole", "waterlogging", "garbage"]:
            cat_df = df[df["category"] == cat]
            if cat_df.empty:
                continue
            st.markdown(
                f'<div class="cat-header">{CAT_ICON.get(cat,"")} {cat.title()} ({len(cat_df)})</div>',
                unsafe_allow_html=True
            )
            show_cols = [c for c in ["display_name","severity","sentiment_label","priority_score","address","status","created_at"] if c in cat_df.columns]
            display = (
                cat_df[show_cols]
                .rename(columns={"display_name":"Citizen","severity":"Severity",
                    "sentiment_label":"Sentiment","priority_score":"Priority",
                    "address":"Location","status":"Status","created_at":"Submitted"})
                .copy()
            )
            if "Submitted" in display.columns:
                display["Submitted"] = display["Submitted"].apply(fmt_date)
            if "Priority" in display.columns:
                display = display.sort_values("Priority", ascending=False)
            st.dataframe(display.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No complaints match filters.")


# ══════════════════════════════════════════════════════════
# TAB 2 — MAP
# ══════════════════════════════════════════════════════════
with t2:
    st.markdown("### Live Issue Map — Nagpur City")
    st.caption("Severity zones: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low · Click any pin for details")

    st_folium(build_map(df.copy()), width=None, height=570, returned_objects=[])

    st.markdown("""
    <div style="display:flex;gap:16px;margin-top:8px;font-size:.82rem;color:#475569;flex-wrap:wrap">
      <span><span style="background:#ef4444;padding:2px 10px;border-radius:4px;color:#fff">●</span> Critical</span>
      <span><span style="background:#f97316;padding:2px 10px;border-radius:4px;color:#fff">●</span> High</span>
      <span><span style="background:#eab308;padding:2px 10px;border-radius:4px;color:#1c1917">●</span> Medium</span>
      <span><span style="background:#22c55e;padding:2px 10px;border-radius:4px;color:#fff">●</span> Low</span>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# TAB 3 — MANAGE REPORTS
# ══════════════════════════════════════════════════════════
with t3:
    st.markdown("### Manage Reports")
    st.caption("Updates apply to all linked duplicate reports instantly.")
    st.divider()

    if raw_df.empty:
        st.info("No reports available.")
    else:
        dup_child_ids = (
            raw_df[raw_df["duplicate_of"].notna()]["id"].tolist()
            if "duplicate_of" in raw_df.columns else []
        )
        dup_roots = (
            raw_df[raw_df["duplicate_of"].notna()]["duplicate_of"].unique().tolist()
            if "duplicate_of" in raw_df.columns else []
        )

        top_level = (
            raw_df[~raw_df["id"].isin(dup_child_ids)]
            .sort_values("priority_score", ascending=False)
        )

        # Group by category
        for cat in ["pothole", "waterlogging", "garbage"]:
            cat_rows = top_level[top_level["category"] == cat]
            if cat_rows.empty:
                continue

            st.markdown(
                f'<div class="cat-header">{CAT_ICON.get(cat,"")} {cat.title()} ({len(cat_rows)})</div>',
                unsafe_allow_html=True
            )

            for _, r in cat_rows.iterrows():
                rid        = r["id"]
                sev        = safe_sev(r.get("severity"))
                color      = sev_color(sev)
                status     = safe_status(r.get("status"))
                status_cls = status.replace(" ", "-")
                is_root    = rid in dup_roots
                name       = r.get("display_name", "Citizen")

                group = (
                    raw_df[(raw_df["id"] == rid) | (raw_df["duplicate_of"] == rid)]
                    if is_root else None
                )
                group_count = len(group) if group is not None else 1

                dup_tag = (
                    f'<span style="background:#e0e7ff;color:#3730a3;padding:2px 8px;'
                    f'border-radius:20px;font-size:.7rem;margin-left:6px">'
                    f'🔁 {group_count} reports</span>'
                ) if is_root else ""

                resolved_extra = " resolved-card" if status == "resolved" else ""

                col_info, col_action = st.columns([5, 1])
                with col_info:
                    st.markdown(f"""
                    <div class="complaint-card{resolved_extra}" style="border-left:4px solid {color}">
                      <div class="complaint-title">
                        {CAT_ICON.get(cat,"")} {cat.title()}
                        <span class="badge b-{sev}" style="margin-left:6px">{sev}</span>
                        <span class="badge b-{status_cls}" style="margin-left:4px">{status}</span>
                        {dup_tag}
                      </div>
                      <div class="complaint-addr">📍 {r['address']}</div>
                      <div class="complaint-meta">
                        👤 {name} &nbsp;·&nbsp;
                        Priority: <b>{round(r['priority_score'], 2)}</b> &nbsp;·&nbsp;
                        🕐 {fmt_date(r.get('created_at'))}
                      </div>
                    </div>""", unsafe_allow_html=True)

                    if is_root and group is not None:
                        with st.expander(f"🔁 View all {group_count} linked reports"):
                            g_show = group[["display_name","category","severity","address","status","priority_score"]].copy()
                            g_show.columns = ["Citizen","Category","Severity","Location","Status","Priority"]
                            st.dataframe(g_show.reset_index(drop=True), use_container_width=True)

                with col_action:
                    st.write("")
                    st.write("")
                    cur_idx = STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0
                    new_s = st.selectbox(
                        "s", STATUS_OPTIONS, index=cur_idx,
                        key=f"sel_{rid}", label_visibility="collapsed"
                    )
                    if st.button("Update", key=f"upd_{rid}", type="primary", use_container_width=True):
                        count = patch_status(rid, new_s)
                        if count:
                            if new_s == "resolved":
                                st.success(f"✅ Resolved {count} report{'s' if count > 1 else ''}. Citizens notified.")
                            else:
                                st.success(f"✅ {count} report{'s' if count > 1 else ''} → {new_s}")
                            st.rerun()
