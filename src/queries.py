"""
All 30 analytical SQL queries (MySQL 8). Used by the Streamlit app and exported to
sql/analysis_queries.sql by running:  python src/queries.py

Note on casualties / economic loss (Q11-Q13): the USGS event API has no casualty or
loss columns. We use the USGS PAGER `alert` level as a proxy, because PAGER alerts
are assigned from estimated fatalities and economic losses:
  green < $1M, yellow $1M-$100M, orange $100M-$1B, red > $1B  (estimated losses)
"""

LOSS_PROXY = """CASE alert WHEN 'red' THEN 1000 WHEN 'orange' THEN 100
                WHEN 'yellow' THEN 1 ELSE 0 END"""   # lower bound of PAGER band, USD millions

QUERIES = {
    # ---------------- Magnitude & Depth ----------------
    "1. Top 10 strongest earthquakes": """
SELECT id, time, place, country, mag, depth_km
FROM earthquakes
ORDER BY mag DESC
LIMIT 10;""",

    "2. Top 10 deepest earthquakes": """
SELECT id, time, place, country, depth_km, mag
FROM earthquakes
ORDER BY depth_km DESC
LIMIT 10;""",

    "3. Shallow (< 50 km) earthquakes with magnitude > 7.5": """
SELECT time, place, country, mag, depth_km
FROM earthquakes
WHERE depth_km < 50 AND mag > 7.5
ORDER BY mag DESC;""",

    "4. Average depth per continent": """
SELECT continent, COUNT(*) AS total_quakes, ROUND(AVG(depth_km), 2) AS avg_depth_km
FROM earthquakes
GROUP BY continent
ORDER BY avg_depth_km DESC;""",

    "5. Average magnitude per magnitude type": """
SELECT magType, COUNT(*) AS total_quakes, ROUND(AVG(mag), 2) AS avg_mag
FROM earthquakes
GROUP BY magType
ORDER BY total_quakes DESC;""",

    # ---------------- Time Analysis ----------------
    "6. Year with most earthquakes": """
SELECT year, COUNT(*) AS total_quakes
FROM earthquakes
GROUP BY year
ORDER BY total_quakes DESC;""",

    "7. Month with highest number of earthquakes": """
SELECT month, MONTHNAME(MIN(time)) AS month_name, COUNT(*) AS total_quakes
FROM earthquakes
GROUP BY month
ORDER BY total_quakes DESC;""",

    "8. Day of week with most earthquakes": """
SELECT day_of_week, COUNT(*) AS total_quakes
FROM earthquakes
GROUP BY day_of_week
ORDER BY total_quakes DESC;""",

    "9. Count of earthquakes per hour of day (UTC)": """
SELECT hour, COUNT(*) AS total_quakes
FROM earthquakes
GROUP BY hour
ORDER BY hour;""",

    "10. Most active reporting network": """
SELECT net, COUNT(*) AS total_quakes
FROM earthquakes
GROUP BY net
ORDER BY total_quakes DESC
LIMIT 10;""",

    # ---------------- Casualties & Economic Loss (PAGER proxy) ----------------
    "11. Top 5 places with highest casualties (PAGER alert proxy)": """
SELECT place, country, time, mag, alert, sig
FROM earthquakes
WHERE alert IN ('red', 'orange', 'yellow')
ORDER BY FIELD(alert, 'red', 'orange', 'yellow'), sig DESC
LIMIT 5;""",

    "12. Total estimated economic loss per continent (USD millions, PAGER proxy)": f"""
SELECT continent,
       SUM({LOSS_PROXY}) AS est_min_loss_usd_millions,
       SUM(alert IN ('orange', 'red')) AS high_loss_events
FROM earthquakes
GROUP BY continent
ORDER BY est_min_loss_usd_millions DESC;""",

    "13. Average economic loss by alert level (USD millions, PAGER proxy)": f"""
SELECT alert, COUNT(*) AS events,
       ROUND(AVG({LOSS_PROXY}), 2) AS avg_est_min_loss_usd_millions,
       ROUND(AVG(mag), 2) AS avg_mag, ROUND(AVG(sig)) AS avg_significance
FROM earthquakes
GROUP BY alert
ORDER BY FIELD(alert, 'red', 'orange', 'yellow', 'green', 'none');""",

    # ---------------- Event Type & Quality Metrics ----------------
    "14. Reviewed vs automatic earthquakes": """
SELECT status, COUNT(*) AS total_quakes,
       ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM earthquakes), 2) AS pct
FROM earthquakes
GROUP BY status;""",

    "15. Count by earthquake type": """
SELECT type, COUNT(*) AS total_events
FROM earthquakes
GROUP BY type
ORDER BY total_events DESC;""",

    "16. Number of earthquakes by data type (types)": """
SELECT data_type, total_quakes FROM (
    SELECT 'origin' AS data_type, SUM(FIND_IN_SET('origin', types) > 0) AS total_quakes FROM earthquakes
    UNION ALL SELECT 'phase-data', SUM(FIND_IN_SET('phase-data', types) > 0) FROM earthquakes
    UNION ALL SELECT 'moment-tensor', SUM(FIND_IN_SET('moment-tensor', types) > 0) FROM earthquakes
    UNION ALL SELECT 'focal-mechanism', SUM(FIND_IN_SET('focal-mechanism', types) > 0) FROM earthquakes
    UNION ALL SELECT 'shakemap', SUM(FIND_IN_SET('shakemap', types) > 0) FROM earthquakes
    UNION ALL SELECT 'dyfi', SUM(FIND_IN_SET('dyfi', types) > 0) FROM earthquakes
    UNION ALL SELECT 'losspager', SUM(FIND_IN_SET('losspager', types) > 0) FROM earthquakes
    UNION ALL SELECT 'finite-fault', SUM(FIND_IN_SET('finite-fault', types) > 0) FROM earthquakes
) t
ORDER BY total_quakes DESC;""",

    "17. Average RMS and gap per continent": """
SELECT continent, ROUND(AVG(rms), 3) AS avg_rms, ROUND(AVG(gap), 2) AS avg_gap
FROM earthquakes
GROUP BY continent
ORDER BY avg_gap DESC;""",

    "18. Events with high station coverage (nst > 100)": """
SELECT id, time, place, mag, nst
FROM earthquakes
WHERE nst > 100
ORDER BY nst DESC
LIMIT 50;""",

    # ---------------- Tsunamis & Alerts ----------------
    "19. Number of tsunamis triggered per year": """
SELECT year, SUM(tsunami) AS tsunami_events, COUNT(*) AS total_quakes
FROM earthquakes
GROUP BY year
ORDER BY year;""",

    "20. Count of earthquakes by alert level": """
SELECT alert, COUNT(*) AS total_quakes
FROM earthquakes
GROUP BY alert
ORDER BY FIELD(alert, 'red', 'orange', 'yellow', 'green', 'none');""",

    # ---------------- Seismic Pattern & Trends ----------------
    "21. Top 5 countries with highest average magnitude (min 20 quakes)": """
SELECT country, COUNT(*) AS total_quakes, ROUND(AVG(mag), 3) AS avg_mag
FROM earthquakes
GROUP BY country
HAVING COUNT(*) >= 20
ORDER BY avg_mag DESC
LIMIT 5;""",

    "22. Countries with both shallow and deep quakes in the same month": """
SELECT country, year, month,
       SUM(depth_km < 70)   AS shallow_quakes,
       SUM(depth_km >= 300) AS deep_quakes
FROM earthquakes
GROUP BY country, year, month
HAVING shallow_quakes > 0 AND deep_quakes > 0
ORDER BY year, month, country;""",

    "23. Year-over-year growth rate in total earthquakes": """
WITH yearly AS (
    SELECT year, COUNT(*) AS total_quakes
    FROM earthquakes
    GROUP BY year
)
SELECT year, total_quakes,
       LAG(total_quakes) OVER (ORDER BY year) AS previous_year,
       ROUND(100 * (total_quakes - LAG(total_quakes) OVER (ORDER BY year))
             / LAG(total_quakes) OVER (ORDER BY year), 2) AS yoy_growth_pct
FROM yearly
ORDER BY year;""",

    "24. Top 3 most seismically active regions (frequency + avg magnitude)": """
WITH stats AS (
    SELECT country, COUNT(*) AS total_quakes, AVG(mag) AS avg_mag
    FROM earthquakes
    GROUP BY country
    HAVING COUNT(*) >= 50
)
SELECT country, total_quakes, ROUND(avg_mag, 3) AS avg_mag,
       ROUND(0.5 * total_quakes / MAX(total_quakes) OVER ()
           + 0.5 * avg_mag / MAX(avg_mag) OVER (), 4) AS activity_score
FROM stats
ORDER BY activity_score DESC
LIMIT 3;""",

    # ---------------- Depth, Location & Distance ----------------
    "25. Average depth per country within ±5° of the equator": """
SELECT country, COUNT(*) AS total_quakes, ROUND(AVG(depth_km), 2) AS avg_depth_km
FROM earthquakes
WHERE latitude BETWEEN -5 AND 5
GROUP BY country
ORDER BY total_quakes DESC;""",

    "26. Countries with highest shallow-to-deep ratio": """
SELECT country,
       SUM(is_shallow = 1) AS shallow_quakes,
       SUM(is_shallow = 0) AS deep_quakes,
       ROUND(SUM(is_shallow = 1) / SUM(is_shallow = 0), 2) AS shallow_to_deep_ratio
FROM earthquakes
GROUP BY country
HAVING deep_quakes > 0 AND COUNT(*) >= 20
ORDER BY shallow_to_deep_ratio DESC
LIMIT 15;""",

    "27. Average magnitude: tsunami vs no tsunami": """
SELECT ROUND(AVG(CASE WHEN tsunami = 1 THEN mag END), 3) AS avg_mag_tsunami,
       ROUND(AVG(CASE WHEN tsunami = 0 THEN mag END), 3) AS avg_mag_no_tsunami,
       ROUND(AVG(CASE WHEN tsunami = 1 THEN mag END)
           - AVG(CASE WHEN tsunami = 0 THEN mag END), 3) AS magnitude_difference
FROM earthquakes;""",

    "28. Events with lowest data reliability (highest gap + rms)": """
SELECT id, time, place, mag, gap, rms,
       ROUND(gap / MAX(gap) OVER () + rms / MAX(rms) OVER (), 4) AS error_score
FROM earthquakes
ORDER BY error_score DESC
LIMIT 20;""",

    "29. Consecutive earthquakes within 50 km and 1 hour": """
WITH ordered AS (
    SELECT id, time, place, mag, latitude, longitude,
           LEAD(id)        OVER (ORDER BY time) AS next_id,
           LEAD(time)      OVER (ORDER BY time) AS next_time,
           LEAD(place)     OVER (ORDER BY time) AS next_place,
           LEAD(latitude)  OVER (ORDER BY time) AS next_lat,
           LEAD(longitude) OVER (ORDER BY time) AS next_lon
    FROM earthquakes
)
SELECT id, time, place, next_id, next_time, next_place,
       TIMESTAMPDIFF(MINUTE, time, next_time) AS minutes_apart,
       ROUND(ST_Distance_Sphere(POINT(longitude, latitude),
                                POINT(next_lon, next_lat)) / 1000, 2) AS km_apart
FROM ordered
WHERE next_time IS NOT NULL
  AND TIMESTAMPDIFF(SECOND, time, next_time) <= 3600
  AND ST_Distance_Sphere(POINT(longitude, latitude), POINT(next_lon, next_lat)) <= 50000
ORDER BY time;""",

    "30. Regions with most deep-focus earthquakes (> 300 km)": """
SELECT country, COUNT(*) AS deep_focus_quakes, ROUND(AVG(depth_km), 1) AS avg_depth_km
FROM earthquakes
WHERE depth_km > 300
GROUP BY country
ORDER BY deep_focus_quakes DESC
LIMIT 10;""",
}


if __name__ == "__main__":
    with open("sql/analysis_queries.sql", "w") as f:
        f.write("-- Global Seismic Trends: 30 analytical queries (MySQL 8)\nUSE earthquake_db;\n")
        for title, sql in QUERIES.items():
            f.write(f"\n-- {title}{sql}\n")
    print("Wrote sql/analysis_queries.sql")
