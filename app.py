"""
Step 4: Streamlit dashboard.  Run:  streamlit run app.py
Tab 1 - Overview: filters, KPIs, world map, trend charts (from MySQL)
Tab 2 - SQL Insights: pick any of the 30 analytical queries, see SQL + result + chart
"""
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

from src.queries import QUERIES

DB_URL = (f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}"
          f"@{os.getenv('DB_HOST', 'localhost')}:3306/earthquake_db")

st.set_page_config(page_title="Global Seismic Trends", page_icon="🌍", layout="wide")


@st.cache_resource
def get_engine():
    """Return a MySQL engine, or None if MySQL isn't reachable (e.g. on Streamlit Cloud)."""
    try:
        engine = create_engine(DB_URL)
        with engine.connect():
            pass
        return engine
    except Exception:
        return None


@st.cache_data
def run_query(sql):
    return pd.read_sql(sql, get_engine())


@st.cache_data
def load_saved(path, **kwargs):
    return pd.read_csv(path, **kwargs)


ONLINE = get_engine() is None   # no MySQL -> use the saved MySQL results

st.title("🌍 Global Seismic Trends: Data-Driven Earthquake Insights")
st.caption("USGS earthquakes, magnitude 4.5+, Nov 2021 – Oct 2026 · stored in MySQL"
           + (" · online view: results exported from MySQL" if ONLINE else " · live MySQL"))

if ONLINE:
    df = load_saved("data/clean_earthquakes.csv", parse_dates=["time", "updated"])
else:
    df = run_query("SELECT * FROM earthquakes")

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")
years = st.sidebar.slider("Year", int(df.year.min()), int(df.year.max()),
                          (int(df.year.min()), int(df.year.max())))
mags = st.sidebar.slider("Magnitude", float(df.mag.min()), float(df.mag.max()),
                         (float(df.mag.min()), float(df.mag.max())), step=0.1)
continents = st.sidebar.multiselect("Continent", sorted(df.continent.unique()),
                                    default=sorted(df.continent.unique()))
depths = st.sidebar.multiselect("Depth category", ["Shallow", "Intermediate", "Deep"],
                                default=["Shallow", "Intermediate", "Deep"])

f = df[df.year.between(*years) & df.mag.between(*mags)
       & df.continent.isin(continents) & df.depth_category.isin(depths)]

tab1, tab2 = st.tabs(["📊 Overview", "🧮 SQL Insights (30 queries)"])

with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Earthquakes", f"{len(f):,}")
    c2.metric("Avg magnitude", f"{f.mag.mean():.2f}" if len(f) else "-")
    c3.metric("Max magnitude", f"{f.mag.max():.1f}" if len(f) else "-")
    c4.metric("Tsunami events", int(f.tsunami.sum()))
    c5.metric("Strong (M6+)", int(f.is_strong.sum()))

    st.subheader("Where earthquakes happen")
    fig = px.scatter_geo(f, lat="latitude", lon="longitude", color="mag", size="mag",
                         size_max=12, hover_name="place", projection="natural earth",
                         color_continuous_scale="OrRd",
                         hover_data={"depth_km": True, "time": True})
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    monthly = f.groupby(f.time.dt.to_period("M").astype(str)).size().reset_index(name="count")
    left.plotly_chart(px.line(monthly, x="time", y="count", title="Earthquakes per month"),
                      use_container_width=True)
    right.plotly_chart(px.histogram(f, x="mag", nbins=40, title="Magnitude distribution"),
                       use_container_width=True)

    left, right = st.columns(2)
    top = f.country.value_counts().head(15).reset_index()
    top.columns = ["country", "count"]
    left.plotly_chart(px.bar(top, x="count", y="country", orientation="h",
                             title="Top 15 countries/regions").update_yaxes(autorange="reversed"),
                      use_container_width=True)
    right.plotly_chart(px.scatter(f, x="depth_km", y="mag", color="depth_category", opacity=0.5,
                                  title="Depth vs magnitude"), use_container_width=True)

    left, right = st.columns(2)
    left.plotly_chart(px.pie(f, names="depth_category", title="Depth categories", hole=0.4),
                      use_container_width=True)
    by_cont = f.groupby("continent").size().reset_index(name="count")
    right.plotly_chart(px.bar(by_cont, x="continent", y="count", title="Earthquakes by continent"),
                       use_container_width=True)

with tab2:
    choice = st.selectbox("Choose an analysis question", list(QUERIES))
    sql = QUERIES[choice]
    if ONLINE:
        number = list(QUERIES).index(choice) + 1
        result = load_saved(f"data/query_results/q{number:02d}.csv")
    else:
        result = run_query(sql)
    st.dataframe(result, use_container_width=True)
    st.caption(f"{len(result)} rows")

    # Auto chart: first text column vs first numeric column
    text_cols = [c for c in result.columns if result[c].dtype == object]
    num_cols = [c for c in result.columns if pd.api.types.is_numeric_dtype(result[c])]
    if len(result) > 1 and num_cols:
        x = text_cols[0] if text_cols else result.columns[0]
        y = [c for c in num_cols if c != x][0] if [c for c in num_cols if c != x] else None
        if y:
            st.plotly_chart(px.bar(result.head(30), x=x, y=y, title=choice),
                            use_container_width=True)
    with st.expander("Show SQL"):
        st.code(sql.strip(), language="sql")
    if choice.startswith(("11.", "12.", "13.")):
        st.info("USGS has no casualty/loss columns. These use the USGS PAGER alert level as a "
                "proxy (PAGER alerts are based on estimated fatalities and losses: green < $1M, "
                "yellow $1M–100M, orange $100M–1B, red > $1B).")
