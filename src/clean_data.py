"""
Step 2: Clean and preprocess the raw data with Pandas + Regex.

- Convert time / updated to datetime
- Regex: extract country from `place`
- Normalize text fields (alert lowercase, strip spaces/commas)
- Convert numeric fields, fill missing values (median / 0)
- Derived columns: year, month, day, day_of_week, hour, depth category,
  shallow flag, magnitude category, strong / destructive flags, continent
"""
import re

import pandas as pd

INPUT = "data/raw_earthquakes.csv"
OUTPUT = "data/clean_earthquakes.csv"

US_STATES = {
    "alaska", "california", "hawaii", "nevada", "oregon", "washington", "utah",
    "idaho", "montana", "wyoming", "texas", "oklahoma", "new mexico", "arizona",
    "colorado", "puerto rico", "ca", "ak", "hi", "nv", "or", "wa", "ut", "id",
    "mt", "wy", "tx", "ok", "nm", "az", "co", "pr",
}

# "10 km SSW of Town, Country"  ->  removes "10 km SSW of "
DISTANCE_PREFIX = re.compile(r"^\s*\d+(\.\d+)?\s*km\s+[NSEW]{1,3}\s+of\s+", re.I)
# "south of the Fiji Islands", "off the east coast of Honshu", "near the coast of Peru"
# "south of X" needs "of" (so "South Sandwich Islands" is kept); "southern X" doesn't
DIRECTION_PREFIX = re.compile(
    r"^(?:(?:off|near)\s+the\s+(?:(?:north|south|east|west)\s+)?coast\s+of\s+|"
    r"(?:south|north|east|west|southeast|southwest|northeast|northwest)\s+of\s+|"
    r"(?:southern|northern|eastern|western|central)\s+)(?:the\s+)?",
    re.I,
)
REGION_SUFFIX = re.compile(r"\s+region$", re.I)
# Named events: "2025 Kamchatka Peninsula, Russia Earthquake" -> "Kamchatka Peninsula, Russia"
YEAR_PREFIX = re.compile(r"^\d{4}\s+")
EVENT_SUFFIX = re.compile(r"\s+earthquake(\s+sequence)?$", re.I)
# Same place written in different ways -> one name
ALIASES = {"Fiji Islands": "Fiji", "Kermadec Islands": "Kermadec Islands, New Zealand",
           "MX": "Mexico", "Philippine Islands": "Philippines",
           "Kahramanmaras": "Turkey", "Burma (Myanmar)": "Myanmar", "Burma": "Myanmar",
           "Tibetan Plateau": "China"}


def extract_country(place):
    """Regex-based country/region extraction from the USGS `place` text."""
    if not isinstance(place, str) or not place.strip():
        return "Unknown"
    text = EVENT_SUFFIX.sub("", YEAR_PREFIX.sub("", place.strip()))
    text = DISTANCE_PREFIX.sub("", text)
    if "," in text:
        text = text.split(",")[-1]          # country is after the last comma
    text = DIRECTION_PREFIX.sub("", text.strip())
    text = REGION_SUFFIX.sub("", text).strip()
    if text.lower() in US_STATES:
        return "United States"
    text = text.title() if text.islower() else text
    return ALIASES.get(text, text)


def get_continent(lat, lon):
    """Approximate continent from coordinates (bounding boxes). Oceans -> 'Oceanic/Other'."""
    if lat < -60:
        return "Antarctica"
    if 12 <= lat <= 42 and 34 <= lon <= 63:
        return "Asia"                        # Middle East
    if 35 <= lat <= 72 and -25 <= lon <= 45:
        return "Europe"
    if -35 <= lat < 35 and -20 <= lon <= 52:
        return "Africa"
    if (lat < -10 and lon >= 110) or (lat < 0 and lon >= 141) or (lat < 0 and lon <= -150):
        return "Oceania"
    if lat >= 50 and (lon >= 165 or lon <= -130):
        return "North America"               # Alaska + Aleutians
    if lat >= -11 and 45 < lon <= 180:
        return "Asia"
    if lat >= 7 and -170 <= lon <= -50:
        return "North America"
    if lat < 12 and -92 <= lon <= -30:
        return "South America"
    return "Oceanic/Other"


def depth_category(depth):
    if depth < 70:
        return "Shallow"        # 0-70 km
    if depth < 300:
        return "Intermediate"   # 70-300 km
    return "Deep"               # 300+ km


def magnitude_category(mag):
    if mag < 5:
        return "Light"
    if mag < 6:
        return "Moderate"
    if mag < 7:
        return "Strong"
    if mag < 8:
        return "Major"
    return "Great"


def main():
    df = pd.read_csv(INPUT)
    print("Raw shape:", df.shape)

    # 1. Remove duplicate events
    df = df.drop_duplicates(subset="id")

    # 2. Dates
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce")

    # 3. Clean text fields
    text_cols = ["magType", "status", "type", "net", "sources", "types", "ids",
                 "place", "locationSource", "magSource", "alert"]
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()
    for col in ["magType", "status", "type", "net", "locationSource", "magSource", "alert"]:
        df[col] = df[col].str.lower()
    for col in ["sources", "types", "ids"]:
        df[col] = df[col].str.replace(r"^,+|,+$", "", regex=True)   # ",us,at," -> "us,at"
    df["place"] = df["place"].fillna("Unknown")
    df["alert"] = df["alert"].fillna("none")

    # 4. Numeric fields
    numeric_cols = ["mag", "depth_km", "latitude", "longitude", "nst", "dmin", "rms",
                    "gap", "magError", "depthError", "magNst", "sig", "tsunami",
                    "felt", "cdi", "mmi"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["mag", "time", "latitude", "longitude"])   # core fields must exist
    print("Missing values before filling:\n", df.isna().sum()[df.isna().sum() > 0])
    for col in ["nst", "dmin", "rms", "gap", "magError", "depthError", "magNst", "depth_km"]:
        df[col] = df[col].fillna(df[col].median())                    # quality metrics -> median
    for col in ["sig", "tsunami", "felt", "cdi", "mmi"]:
        df[col] = df[col].fillna(0)                                    # missing = not reported
    df[["sig", "tsunami", "felt"]] = df[["sig", "tsunami", "felt"]].astype(int)
    for col in text_cols:
        df[col] = df[col].fillna("unknown")

    # 5. Derived columns
    df["year"] = df["time"].dt.year
    df["month"] = df["time"].dt.month
    df["day"] = df["time"].dt.day
    df["day_of_week"] = df["time"].dt.day_name()
    df["hour"] = df["time"].dt.hour
    df["country"] = df["place"].apply(extract_country)
    df["continent"] = [get_continent(a, b) for a, b in zip(df["latitude"], df["longitude"])]
    df["depth_category"] = df["depth_km"].apply(depth_category)
    df["is_shallow"] = (df["depth_km"] < 70).astype(int)
    df["mag_category"] = df["mag"].apply(magnitude_category)
    df["is_strong"] = (df["mag"] >= 6).astype(int)
    df["is_destructive"] = (df["mag"] >= 7).astype(int)

    print("Clean shape:", df.shape)
    print("Top countries:\n", df["country"].value_counts().head(15))
    df.to_csv(OUTPUT, index=False)
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
