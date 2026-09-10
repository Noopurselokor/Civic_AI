"""
CivicAI Admin Dashboard
------------------------
Modern-look map + heatmap of citizen-reported civic issues,
pulling live data from Supabase (Postgres + PostGIS).

Run locally with: streamlit run app.py
Deploy free on: https://share.streamlit.io (Streamlit Community Cloud)
"""

import streamlit as st
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
from supabase import create_client
import pandas as pd

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="CivicAI Admin Dashboard",
    page_icon="📍",
    layout="wide"
)

# ---------- SUPABASE CONNECTION ----------
# Store these in Streamlit's secrets.toml, never hardcode in real deployment
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()


# ---------- FETCH REPORTS ----------
@st.cache_data(ttl=30)  # refreshes every 30 seconds
def fetch_reports():
    response = (
        supabase.table("reports")
        .select("id, lat, lng, address, category, confidence, priority_score, status, ward_id, created_at")
        .execute()
    )
    return pd.DataFrame(response.data)


df = fetch_reports()

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("Filters")

category_filter = st.sidebar.multiselect(
    "Category",
    options=["pothole", "waterlogging", "garbage"],
    default=["pothole", "waterlogging", "garbage"]
)

status_filter = st.sidebar.multiselect(
    "Status",
    options=["pending", "in-progress", "resolved"],
    default=["pending", "in-progress"]
)

if not df.empty:
    df = df[df["category"].isin(category_filter)]
    df = df[df["status"].isin(status_filter)]

# ---------- HEADER METRICS ----------
st.title("CivicAI Admin Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total reports", len(df))
col2.metric("High priority", len(df[df["priority_score"] > 0.7]) if not df.empty else 0)
col3.metric("Pending", len(df[df["status"] == "pending"]) if not df.empty else 0)
col4.metric("Resolved", len(df[df["status"] == "resolved"]) if not df.empty else 0)

st.divider()

# ---------- MAP ----------
st.subheader("Live issue map")

# Default center: adjust to your ward's coordinates (example: Nagpur)
DEFAULT_LAT, DEFAULT_LNG = 21.1458, 79.0882

m = folium.Map(
    location=[DEFAULT_LAT, DEFAULT_LNG],
    zoom_start=13,
    tiles=None  # we add a custom clean tile layer below
)

# Modern clean tile layer (CartoDB Positron) instead of default OSM look
folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attr='&copy; <a href="https://carto.com/attributions">CARTO</a> &copy; OpenStreetMap contributors',
    name="Clean",
    control=False
).add_to(m)

if not df.empty:
    # Heatmap layer: weight by priority_score
    heat_data = [
        [row["lat"], row["lng"], row["priority_score"]]
        for _, row in df.iterrows()
    ]
    HeatMap(
        heat_data,
        radius=22,
        blur=18,
        max_zoom=13,
        gradient={0.2: "#639922", 0.5: "#EF9F27", 0.8: "#E24B4A"}
    ).add_to(m)

    # Clickable pins on top, clustered so they don't overlap when zoomed out
    cluster = MarkerCluster().add_to(m)
    color_map = {"pothole": "red", "waterlogging": "blue", "garbage": "orange"}

    for _, row in df.iterrows():
        popup_html = f"""
        <b>{row['category'].title()}</b><br>
        {row['address']}<br>
        Priority: {round(row['priority_score'], 2)}<br>
        Status: {row['status']}
        """
        folium.Marker(
            location=[row["lat"], row["lng"]],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color=color_map.get(row["category"], "gray"), icon="info-sign")
        ).add_to(cluster)
else:
    st.info("No reports match the current filters.")

st_folium(m, width=None, height=520)

st.divider()

# ---------- REPORT TABLE ----------
st.subheader("All reports")
if not df.empty:
    st.dataframe(
        df[["category", "address", "status", "priority_score", "confidence", "created_at"]]
        .sort_values("priority_score", ascending=False),
        use_container_width=True
    )
else:
    st.write("No reports to display.")
