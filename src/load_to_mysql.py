"""
Step 3: Store the cleaned data in MySQL using SQLAlchemy.

Creates database `earthquake_db` and table `earthquakes` (26 USGS features + extra
USGS fields + derived columns), then inserts the cleaned DataFrame.
Change DB_USER / DB_PASSWORD below if your MySQL root has a password.
"""
import os

import pandas as pd
from sqlalchemy import create_engine, text

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = "earthquake_db"
INPUT = "data/clean_earthquakes.csv"

SERVER_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306"

CREATE_TABLE = """
CREATE TABLE earthquakes (
    id              VARCHAR(30) PRIMARY KEY,
    time            DATETIME,
    updated         DATETIME,
    latitude        DOUBLE,
    longitude       DOUBLE,
    depth_km        DOUBLE,
    mag             DOUBLE,
    magType         VARCHAR(10),
    place           VARCHAR(255),
    status          VARCHAR(20),
    tsunami         TINYINT,
    sig             INT,
    net             VARCHAR(10),
    nst             DOUBLE,
    dmin            DOUBLE,
    rms             DOUBLE,
    gap             DOUBLE,
    magError        DOUBLE,
    depthError      DOUBLE,
    magNst          DOUBLE,
    locationSource  VARCHAR(20),
    magSource       VARCHAR(20),
    types           VARCHAR(500),
    ids             VARCHAR(255),
    sources         VARCHAR(255),
    type            VARCHAR(50),
    alert           VARCHAR(10),
    felt            INT,
    cdi             DOUBLE,
    mmi             DOUBLE,
    year            INT,
    month           INT,
    day             INT,
    day_of_week     VARCHAR(10),
    hour            INT,
    country         VARCHAR(100),
    continent       VARCHAR(30),
    depth_category  VARCHAR(20),
    is_shallow      TINYINT,
    mag_category    VARCHAR(20),
    is_strong       TINYINT,
    is_destructive  TINYINT,
    INDEX idx_time (time),
    INDEX idx_country (country),
    INDEX idx_mag (mag),
    INDEX idx_year_month (year, month)
)
"""


def main():
    df = pd.read_csv(INPUT, parse_dates=["time", "updated"])

    server = create_engine(SERVER_URL)
    with server.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))

    engine = create_engine(f"{SERVER_URL}/{DB_NAME}")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS earthquakes"))
        conn.execute(text(CREATE_TABLE))

    df.to_sql("earthquakes", engine, if_exists="append", index=False, chunksize=2000)

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM earthquakes")).scalar()
    print(f"Inserted {count} rows into {DB_NAME}.earthquakes")


if __name__ == "__main__":
    main()
