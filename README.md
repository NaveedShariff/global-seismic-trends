# Global Seismic Trends - Earthquake Data Analysis

Live dashboard: https://global-seismic-trends-suxcksqpegf7ntsbu46rvb.streamlit.app/

In this project I collected 5 years of earthquake data (Nov 2021 - Oct 2026, magnitude 4.5+) from the USGS API, cleaned it using Pandas and Regex, stored it in MySQL, answered 30 questions using SQL, and made a Streamlit dashboard to show the results.

## Tools used
Python, Pandas, Regex, MySQL, SQLAlchemy, Streamlit, Plotly

## Files
- `src/fetch_data.py` - gets the data from the USGS API month by month
- `src/clean_data.py` - cleans the data and adds new columns
- `src/load_to_mysql.py` - creates the table in MySQL and inserts the data
- `src/queries.py` - all 30 SQL queries
- `src/export_results.py` - saves the query results to CSV (used by the online dashboard)
- `sql/analysis_queries.sql` - the same 30 queries in one SQL file
- `app.py` - Streamlit dashboard
- `data/` - raw data, cleaned data and query results

## How to run
```
pip install -r requirements.txt
python src/fetch_data.py
python src/clean_data.py
python src/load_to_mysql.py
python src/export_results.py
streamlit run app.py
```
MySQL should be running (I used root user with no password on my laptop).

## What I did

**Getting the data:** I called the USGS API for each month. The geojson format didn't have magError, depthError, magNst, locationSource and magSource, so I also downloaded the csv format and merged both on `id` to get all 26 columns. Time was in milliseconds, so I converted it to datetime.

**Cleaning:**
- Used regex to get the country from `place` (example: "66 km NNW of Ende, Indonesia" -> "Indonesia")
- Made text columns lowercase and removed extra spaces and commas
- Filled missing values: median for nst, gap, rms, dmin, magError, depthError, magNst and 0 for sig, tsunami, felt
- Added new columns: year, month, day, day_of_week, hour, country, continent, depth_category (shallow < 70 km, intermediate 70-300 km, deep > 300 km), is_strong (mag >= 6), is_destructive (mag >= 7)

**SQL:** 30 queries on magnitude, depth, time, alerts, tsunamis, countries and data quality. I used GROUP BY, CASE, CTEs and window functions like LAG and LEAD.

**Note:** USGS data has no casualty or economic loss numbers, so for those questions I used the PAGER `alert` level (green/yellow/orange/red), because USGS sets it from estimated deaths and losses.

**Dashboard:** It has filters (year, magnitude, continent, depth), a world map, charts, and a dropdown to see the result of each of the 30 SQL questions. On my laptop it reads from MySQL. Online it reads the saved query results because the cloud can't connect to my local MySQL.

## Findings
- Total: 38,371 earthquakes
- Strongest: M8.8, Kamchatka, Russia (July 2025)
- Deepest earthquakes are near Fiji (around 670 km deep)
- Most active countries: Indonesia, Japan, Philippines, Russia (Pacific Ring of Fire)
- 2025 had the most earthquakes (8,561)
- Earthquakes with a tsunami flag are about 1 magnitude stronger on average (5.8 vs 4.8)
- Only 23 red alerts in 5 years, mostly from shallow quakes near cities (Turkey, Myanmar, Tibet)
- Iran, Turkey, China and Panama have mostly shallow earthquakes, which are more dangerous for buildings

## Limitations
- No casualty data in USGS, so I used alert level instead
- Continent is roughly calculated from latitude and longitude
- 2021 and 2026 are not full years
