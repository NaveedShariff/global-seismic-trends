"""
Step 5: Run all 30 SQL queries on MySQL and save each result as a CSV in
data/query_results/. The online (Streamlit Cloud) version of the dashboard can't
reach your local MySQL, so it shows these saved MySQL results instead.
Run again whenever the data or queries change:  python src/export_results.py
"""
import os

import pandas as pd
from sqlalchemy import create_engine

from queries import QUERIES

DB_URL = (f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}"
          f"@{os.getenv('DB_HOST', 'localhost')}:3306/earthquake_db")
OUTPUT_DIR = "data/query_results"


def result_file(number):
    return f"{OUTPUT_DIR}/q{number:02d}.csv"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    engine = create_engine(DB_URL)
    for number, (title, sql) in enumerate(QUERIES.items(), start=1):
        result = pd.read_sql(sql, engine)
        result.to_csv(result_file(number), index=False)
        print(f"{title}: {len(result)} rows")


if __name__ == "__main__":
    main()
