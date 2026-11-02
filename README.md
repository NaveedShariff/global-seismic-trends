# 🌍 Global Seismic Trends: Data-Driven Earthquake Insights

An end-to-end data project: **USGS API → Python (Pandas + Regex) cleaning → MySQL → 30 SQL analyses → Streamlit dashboard.**

🔗 **Live dashboard:** https://global-seismic-trends-suxcksqpegf7ntsbu46rvb.streamlit.app/

**Domain:** Disaster Management · Geoscience · Seismology
**Skills:** Python for data analytics, Regex, SQL & RDBMS, Streamlit

---

## 1. Problem statement
Analyze global earthquake data from the last 5 years to find seismic patterns, trends and risk zones. The goal is to help governments, insurers and researchers assess earthquake risk and plan disaster management.

## 2. Project structure
```
global-seismic-trends/
├── app.py                    # Streamlit dashboard (Overview + 30 SQL insights)
├── requirements.txt
├── data/
│   ├── raw_earthquakes.csv    # output of fetch_data.py
│   ├── clean_earthquakes.csv  # output of clean_data.py
│   └── query_results/         # q01.csv … q30.csv (MySQL query outputs)
├── sql/
│   └── analysis_queries.sql   # all 30 analytical queries
├── src/
│   ├── fetch_data.py          # Step 1: USGS API retrieval (month by month)
│   ├── clean_data.py          # Step 2: Pandas + Regex cleaning, derived columns
│   ├── load_to_mysql.py       # Step 3: create table, insert with SQLAlchemy
│   ├── export_results.py      # saves the 30 query results for the online dashboard
│   └── queries.py             # the 30 queries (shared by app + SQL file)
└── docs/
```

## 3. How to run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/fetch_data.py       # ~5 min, 120 API calls
python src/clean_data.py
python src/load_to_mysql.py    # needs MySQL running (root, no password by default)
python src/queries.py          # regenerates sql/analysis_queries.sql
python src/export_results.py   # saves the 30 MySQL query results to data/query_results/
streamlit run app.py
```
If your MySQL root user has a password: `export DB_PASSWORD=yourpassword` before running.

**Two modes of the dashboard:**
- **Local (with MySQL running):** every query runs live on MySQL.
- **Online (Streamlit Community Cloud):** the cloud can't reach a local MySQL, so the app automatically shows the query results exported from MySQL (`data/query_results/`) and the cleaned dataset.

## 4. Methodology

### Step 1: Data retrieval (`src/fetch_data.py`)
- API: `https://earthquake.usgs.gov/fdsnws/event/1/query`
- Range: **1 Nov 2021 → 1 Nov 2026 (5 years)**, `minmagnitude=4.5`. M4.5+ quakes are recorded consistently worldwide, so trends over time are fair to compare.
- Loops through each month and builds `starttime`/`endtime`, then calls `requests.get(url, params=...)`.
- Checks the status code and retries up to 3 times on failure.
- `format=geojson`: values are taken from `properties` (mag, place, status, tsunami, sig, alert, ids, sources, types…) and `geometry` (longitude, latitude, depth).
- GeoJSON doesn't include `magError, depthError, magNst, locationSource, magSource`, so the **CSV** format is fetched for the same month and merged on `id`. Together they give **all 26 features**.
- Timestamps are converted from milliseconds to datetime.

### Step 2: Cleaning (`src/clean_data.py`)
| Task | How |
|---|---|
| Duplicates | `drop_duplicates(subset="id")` |
| Dates | `time`, `updated` → datetime |
| **Regex country extraction** | Removes `"10 km SSW of "` (`^\d+(\.\d+)?\s*km\s+[NSEW]{1,3}\s+of\s+`), takes the text after the last comma, strips direction prefixes (`south of the`, `off the east coast of`…) and a trailing `region`. US state names/codes map to *United States*. |
| Text fields | Strip whitespace; lowercase `alert, magType, status, type, net`; remove leading/trailing commas from `ids, sources, types` (regex `^,+|,+$`) |
| Numeric fields | `pd.to_numeric(errors="coerce")`; quality metrics (`nst, dmin, rms, gap, magError, depthError, magNst`) filled with the **median**; `sig, tsunami, felt, cdi, mmi` filled with **0** |
| Missing alert | `"none"` (no PAGER alert issued) |

**Derived columns:** `year, month, day, day_of_week, hour, country, continent` (from lat/lon bounding boxes), `depth_category` (Shallow < 70 km, Intermediate 70–300, Deep > 300), `is_shallow`, `mag_category` (Light/Moderate/Strong/Major/Great), `is_strong` (M ≥ 6), `is_destructive` (M ≥ 7).

### Step 3: MySQL (`src/load_to_mysql.py`)
- Database `earthquake_db`, table `earthquakes`, `id` as **PRIMARY KEY**.
- Indexes on `time`, `country`, `mag`, `(year, month)` to speed up filters and GROUP BYs.
- Inserted with `DataFrame.to_sql()` through a SQLAlchemy engine (`mysql+pymysql`).

### Step 4: SQL analysis (`sql/analysis_queries.sql`)
30 queries covering magnitude & depth, time trends, losses, quality metrics, tsunamis & alerts, patterns, and distance-based analysis. They use GROUP BY/HAVING, CASE, subqueries, **CTEs**, **window functions** (`LAG`, `LEAD`, `MAX() OVER`), `FIND_IN_SET`, and `ST_Distance_Sphere` (geodesic distance).

> **Casualties & economic loss (Q11–13):** the USGS event API has no casualty or loss columns. These queries use the **USGS PAGER alert level** as a proxy, because PAGER alerts are set from *estimated* fatalities and economic losses (green < $1M, yellow $1M–100M, orange $100M–1B, red > $1B).

### Step 5: Dashboard (`app.py`)
- **Overview tab:** filters (year, magnitude, continent, depth), KPI cards, an interactive world map, monthly trend, magnitude histogram, top countries, depth vs magnitude, depth and continent breakdowns.
- **SQL Insights tab:** pick any of the 30 questions to see the result table, an auto chart, and the SQL used.

## 5. Key findings
**Dataset:** 38,371 earthquakes (M4.5+), 1 Nov 2021 – 31 Oct 2026, 26 features + 16 derived/extra columns.

1. **Strongest event:** the **M8.8 Kamchatka, Russia** earthquake (29 Jul 2025, 35 km deep). 12 shallow (< 50 km) quakes above M7.5 occurred, including Turkey–Syria M7.8 (Feb 2023) and Myanmar M7.7 (Mar 2025).
2. **Deepest quakes are almost all under Fiji/Tonga**, reaching ~670 km. Fiji alone has **1,008 deep-focus (> 300 km) events**, far ahead of Tonga (99) and Japan (86). This is the Tonga–Kermadec subduction zone.
3. **Most active regions** (frequency + average magnitude): **Indonesia (3,922), Japan (3,002), Russia (~2,700)**. The Pacific "Ring of Fire" dominates: Indonesia, Japan, Philippines, Russia, Tonga, PNG, Fiji and Vanuatu make up nearly half (48%) of all events.
4. **Depth by continent:** Oceania quakes are deepest on average (~106 km) and South America second (~77 km), both because of subduction zones. Mid-ocean ridges (Oceanic/Other) are shallow (~21 km).
5. **Time patterns:** 2025 was the busiest full year (8,561 events, +33.8% vs 2024), driven by the Kamchatka aftershock sequence. Day of week and hour of day are **nearly flat**. Earthquakes don't follow human calendars, which also shows the data has no reporting bias.
6. **Tsunamis:** 437 events were flagged with tsunami potential. Their average magnitude is **5.81 vs 4.79** for the rest, about **+1.0 magnitude** higher.
7. **Impact (PAGER proxy):** only **23 red** and **26 orange** alerts in 5 years. Asia carries the largest estimated loss, about ≥ $21B (lower bound of the PAGER bands). Most damaging events come from shallow quakes near populated land (Turkey, Myanmar, Tibet, Colombia, Venezuela).
8. **Shallow-heavy countries:** Iran, Panama, China and Turkey have almost only shallow quakes (ratios above 100:1). That means stronger surface shaking per magnitude, so higher risk for buildings.
9. **Clustering:** 4,226 consecutive pairs of quakes happened within **50 km and 1 hour** of each other. These are aftershock and swarm sequences, which matter for emergency response.
10. **Data quality:** 100% of events are *reviewed*. 99% come from the `us` network (USGS NEIC). The least reliable locations (high gap + RMS) are remote ocean and border areas.

## 6. Recommendations
- **Governments / urban planners:** enforce seismic building codes in shallow-quake countries (Iran, Turkey, China, Panama) and in Ring of Fire cities. Shallow M6+ quakes caused nearly all red alerts.
- **Emergency response:** plan for **aftershock clusters**. Many strong events are followed by more within an hour and 50 km, so keep rescue teams ready for 24–72 hours after a major quake.
- **Coastal authorities:** quakes with tsunami flags average **M5.8+**. Link automatic tsunami warnings to shallow offshore quakes above M6.5 in the Pacific.
- **Insurers:** price risk by **depth and region**, not magnitude alone. Deep Fiji quakes are frequent but cause little damage, while shallow continental quakes cause most losses.
- **Researchers:** add stations in high-gap ocean regions (South Pacific, Southern Ocean ridges) to improve location accuracy.

## 7. Limitations
- USGS does not publish casualties or economic losses per event, so PAGER alert levels are used as a proxy.
- Continent is approximated from coordinates. Country comes from the `place` text, so ocean features (e.g. Mid-Atlantic Ridge) appear as their own regions.
- 2021 (2 months) and 2026 (10 months) are partial years, which affects the year-over-year growth percentages.
