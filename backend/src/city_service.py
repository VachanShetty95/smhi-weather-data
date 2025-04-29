from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from models.temperature_models import (
    AllCitiesTemperatureResponse,
    CityTemperatureResponse,
    MonthlyTemperature,
    Station,
)
from utils.smhi_api import calculate_monthly_means

# Constants
# SMHI API base URLs
METOBS_API_BASE = "https://opendata-download-metobs.smhi.se/api"
VERSION_URL = f"{METOBS_API_BASE}/version/latest.json"
PARAMETER_URL = f"{METOBS_API_BASE}/version/latest/parameter/1.json"  # 1 is temperature
STATION_URL = (
    f"{METOBS_API_BASE}/version/latest/parameter/1/station-set/all/station.json"
)
TEMP_DATA_URL = f"{METOBS_API_BASE}/version/latest/parameter/1/station/{{station_id}}/period/latest-months/data.json"

# Swedish cities to analyze with their station IDs
MAJOR_CITIES = {
    "Stockholm": 97400,  # Stockholm-Observatoriekullen
    "Göteborg": 72420,  # Göteborg A
    "Malmö": 53430,  # Malmö A
    "Uppsala": 97510,  # Uppsala Aut
    "Umeå": 140480,  # Umeå flygplats
}


def get_city_data(city_name: str, station_id: int) -> Optional[pd.DataFrame]:
    """Get temperature data for a city using direct API calls"""
    try:
        url = TEMP_DATA_URL.format(station_id=station_id)
        print(f"Fetching data from URL: {url}")  # Debug log

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Get data for the last 12 months
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        # Format as DataFrame
        times = []
        values = []

        for value in data.get("value", []):
            try:
                # Convert millisecond timestamp to datetime
                date_time = pd.to_datetime(value["date"], unit="ms")
                temp_value = float(value["value"])

                if start_date.date() <= date_time.date() <= end_date.date():
                    times.append(date_time)
                    values.append(temp_value)
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Error parsing value for {city_name}: {e}, Value: {value}")
                continue

        if not times:
            print(f"No data found for station {station_id} in the last 12 months")
            return None

        df = pd.DataFrame({"time": times, "temperature": values})

        print(f"Retrieved {len(df)} records for {city_name}")  # Debug log
        return df

    except requests.RequestException as e:
        print(f"Error getting data for {city_name} (station {station_id}): {e}")
        return None
    except Exception as e:
        print(
            f"Unexpected error getting data for {city_name} (station {station_id}): {e}"
        )
        return None


def find_station_by_city_name(city_name: str) -> Optional[Dict[str, Any]]:
    """Search for stations matching a city name and return the first match"""
    try:
        # Fetch all stations from SMHI API
        response = requests.get(PARAMETER_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Find stations that match the city name (case-insensitive)
        # First try an exact match
        for station in data.get("station", []):
            if city_name.lower() == station.get("name", "").lower() and station.get(
                "active", False
            ):
                return station

        # If no exact match, try partial match
        matching_stations = []
        for station in data.get("station", []):
            if city_name.lower() in station.get("name", "").lower() and station.get(
                "active", False
            ):
                matching_stations.append(station)

        # Return the first match if any found
        if matching_stations:
            return matching_stations[0]

        return None

    except requests.RequestException as e:
        print(f"Error searching for city {city_name}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error searching for city {city_name}: {e}")
        return None


def search_stations_by_name(query: str, limit: int = 10) -> List[Station]:
    """Search for stations by name and return matching stations"""
    try:
        # Fetch all stations from SMHI API
        response = requests.get(PARAMETER_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Find stations that match the query (case-insensitive)
        exact_matches = []
        partial_matches = []

        for station in data.get("station", []):
            station_name = station.get("name", "").lower()
            query_lower = query.lower()

            if not station.get("active", False):
                continue

            # Check for exact match
            if query_lower == station_name:
                exact_matches.append(station)
            # Check for partial match
            elif query_lower in station_name:
                partial_matches.append(station)

        # Combine exact matches first, then partial matches
        matching_stations = []

        # Process exact matches
        for station in exact_matches:
            matching_stations.append(
                Station(
                    id=station.get("id"),
                    name=station.get("name"),
                    owner=station.get("owner", ""),
                    owner_category=station.get("ownerCategory", None),
                    latitude=station.get("latitude"),
                    longitude=station.get("longitude"),
                    height=station.get("height", None),
                    active=station.get("active", True),
                )
            )

        # Process partial matches
        for station in partial_matches:
            matching_stations.append(
                Station(
                    id=station.get("id"),
                    name=station.get("name"),
                    owner=station.get("owner", ""),
                    owner_category=station.get("ownerCategory", None),
                    latitude=station.get("latitude"),
                    longitude=station.get("longitude"),
                    height=station.get("height", None),
                    active=station.get("active", True),
                )
            )

        # Return the matching stations (limit to specified number)
        return matching_stations[:limit]

    except Exception as e:
        print(f"Error searching for stations with query {query}: {str(e)}")
        return []


def get_major_cities_data() -> Dict[str, pd.DataFrame]:
    """Get temperature data for all major cities"""
    cities_data = {}

    for city, station_id in MAJOR_CITIES.items():
        try:
            df = get_city_data(city, station_id)
            if df is not None:
                cities_data[city] = df
        except Exception as e:
            print(f"Error processing data for {city}: {e}")
            continue

    return cities_data
