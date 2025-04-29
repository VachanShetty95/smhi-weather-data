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
HISTORICAL_DATA_URL = f"{METOBS_API_BASE}/version/latest/parameter/1/station/{{station_id}}/period/corrected-archive.json"
HISTORICAL_CSV_URL = f"{METOBS_API_BASE}/version/latest/parameter/1/station/{{station_id}}/period/corrected-archive/data.csv"

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


def get_city_historical_data(city_name: str, station_id: int) -> Optional[pd.DataFrame]:
    """Get historical temperature data for a city by downloading the CSV file directly"""
    try:
        # Use directly version 1.0 which has a more stable data format
        data_url = f"{METOBS_API_BASE}/version/1.0/parameter/1/station/{station_id}/period/corrected-archive/data.csv"
        
        print(f"Downloading CSV from URL: {data_url}")  # Debug log
        
        # Download the CSV data
        csv_response = requests.get(data_url, timeout=30)  # Longer timeout for CSV download
        csv_response.raise_for_status()
        
        # Read in the CSV data
        # SMHI CSVs have metadata at the top, so we need to find the actual data start
        raw_text = csv_response.text
        lines = raw_text.splitlines()
        
        # Find where the actual data starts (after the headers)
        data_start_line = 0
        for i, line in enumerate(lines):
            if "Datum" in line and "Lufttemperatur" in line:
                data_start_line = i
                break
                
        if data_start_line == 0:
            print(f"Could not find data header in CSV for station {station_id}")
            return None
            
        # Read the CSV with pandas, starting from the identified header line
        csv_data = pd.read_csv(
            pd.io.common.StringIO("\n".join(lines[data_start_line:])),
            sep=';',
            encoding='utf-8',
            na_values=['Y']  # Replace quality indicator with NaN
        )
        
        # Filter and rename columns - the actual column names vary, so find them dynamically
        # Find temperature column - it's usually "Lufttemperatur"
        temp_column = None
        date_column = None
        
        for col in csv_data.columns:
            if "temperatur" in col.lower():
                temp_column = col
            if "datum" in col.lower():
                date_column = col
                
        if not temp_column or not date_column:
            print(f"Expected columns not found in CSV for station {station_id}")
            print(f"Available columns: {csv_data.columns.tolist()}")
            return None
            
        # Create a DataFrame with just the needed columns
        df = pd.DataFrame({
            'time': pd.to_datetime(csv_data[date_column]),
            'temperature': csv_data[temp_column].astype(float)
        })
        
        # Drop rows with missing temperature values
        df = df.dropna(subset=['temperature'])
        
        if df.empty:
            print(f"No valid temperature data found for station {station_id}")
            return None
            
        print(f"Retrieved {len(df)} historical records for {city_name}")  # Debug log
        return df

    except requests.RequestException as e:
        print(f"Error getting historical data for {city_name} (station {station_id}): {e}")
        return None
    except Exception as e:
        print(
            f"Unexpected error getting historical data for {city_name} (station {station_id}): {e}"
        )
        return None


def get_city_monthly_data(city_name: str, station_id: int) -> Optional[pd.DataFrame]:
    """Get latest monthly temperature data for a city from the CSV endpoint."""
    try:
        # Use version 1.0 which has a stable CSV format
        data_url = f"{METOBS_API_BASE}/version/1.0/parameter/1/station/{station_id}/period/latest-months/data.csv"
        
        print(f"Downloading monthly CSV from URL: {data_url}")  # Debug log
        
        # Download the CSV data
        csv_response = requests.get(data_url, timeout=20)
        csv_response.raise_for_status()
        
        # Read in the CSV data
        raw_text = csv_response.text
        lines = raw_text.splitlines()
        
        # Find the section with actual data (skip informational headers)
        data_start_line = 0
        for i, line in enumerate(lines):
            if line.startswith("Datum;Tid (UTC);Lufttemperatur;Kvalitet"):
                data_start_line = i
                break
                
        if data_start_line == 0:
            # Try alternative header format
            for i, line in enumerate(lines):
                if "Datum" in line and ("Tid" in line or "UTC" in line) and "Lufttemperatur" in line:
                    data_start_line = i
                    break
        
        if data_start_line == 0:
            print(f"Could not find data header in CSV for station {station_id}")
            return None
            
        # Extract column names from the header 
        headers = lines[data_start_line].split(';')
        
        # Read the CSV data after the header line
        data_lines = [line for line in lines[data_start_line+1:] if line.strip() and not line.startswith("Tidsutsnitt:")]
        
        # If no data lines found, return None
        if not data_lines:
            print(f"No data lines found in CSV for station {station_id}")
            return None
            
        # Manually parse CSV to create a dataframe
        dates = []
        times = []
        temperatures = []
        qualities = []
        
        for line in data_lines:
            parts = line.split(';')
            if len(parts) >= 4:  # Ensure minimum required columns
                date_str = parts[0].strip()
                time_str = parts[1].strip()
                temp_str = parts[2].strip().replace(',', '.')  # Handle European decimal format
                quality = parts[3].strip() if len(parts) > 3 else 'Unknown'
                
                # Only process if we have both date and temperature
                if date_str and temp_str:
                    try:
                        # Check if the temperature value can be converted to float
                        temp = float(temp_str)
                        dates.append(date_str)
                        times.append(time_str)
                        temperatures.append(temp)
                        qualities.append(quality)
                    except ValueError:
                        # Skip malformed data
                        continue
        
        if not dates:
            print(f"No valid data extracted from CSV for station {station_id}")
            return None
            
        # Create datetime column from date and time
        datetime_strings = [f"{d} {t}" for d, t in zip(dates, times)]
        
        # Create pandas dataframe
        df = pd.DataFrame({
            'date_str': dates,
            'time_str': times,
            'datetime_str': datetime_strings,
            'temperature': temperatures,
            'quality': qualities
        })
        
        # Convert date string to datetime
        try:
            df['time'] = pd.to_datetime(df['datetime_str'], format='%Y-%m-%d %H:%M:%S')
        except ValueError:
            # If standard format fails, try alternative format
            try:
                df['time'] = pd.to_datetime(df['datetime_str'], format='%Y-%m-%d %H:%M')
            except ValueError:
                # Last resort, let pandas infer the format
                df['time'] = pd.to_datetime(df['datetime_str'], errors='coerce')
        
        # Drop rows with invalid datetimes
        df = df.dropna(subset=['time'])
        
        # Filter to include only the data with good quality if that exists
        if 'G' in df['quality'].unique():
            df = df[df['quality'] == 'G']
        
        # Select only needed columns
        df = df[['time', 'temperature']]
        
        # Filter to include only data from the last 12 months
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
        
        # Drop rows with missing temperature values
        df = df.dropna(subset=['temperature'])
        
        if df.empty:
            print(f"No valid temperature data found for station {station_id}")
            return None
            
        print(f"Retrieved {len(df)} monthly records for {city_name}")  # Debug log
        return df

    except requests.RequestException as e:
        print(f"Error getting monthly data for {city_name} (station {station_id}): {e}")
        return None
    except Exception as e:
        print(
            f"Unexpected error getting monthly data for {city_name} (station {station_id}): {e}"
        )
        return None
