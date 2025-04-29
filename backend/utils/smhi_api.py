import datetime
import statistics
from typing import List

import httpx
import pandas as pd
from models.temperature_models import (
    MonthlyTemperature,
    Station,
    TemperatureData,
    TemperatureValue,
)

BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/latest"


async def get_station_by_city(city_name: str) -> Station:
    url = f"{BASE_URL}/parameter/1.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        print(data)

    for station_info in data.get("station", []):
        if city_name.lower() in station_info["name"].lower():
            return Station(
                id=int(station_info["id"]),
                name=station_info["name"],
                owner=station_info.get("owner", ""),
                owner_category=station_info.get("ownerCategory", None),
                latitude=station_info["latitude"],
                longitude=station_info["longitude"],
                height=station_info.get("height", None),
                active=station_info.get("active", True),
            )

    raise ValueError(f"No station found for city '{city_name}'.")


async def get_temperature_data(station_id: int) -> TemperatureData:
    url = f"{BASE_URL}/parameter/1/station/{station_id}/period/latest-months/data.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 404:
            raise ValueError(f"No temperature data found for station {station_id}.")
        response.raise_for_status()

    raw_data = response.json()

    try:
        data = raw_data.get("value", [])
        temperature_data = [TemperatureValue(**entry) for entry in data]

        # Return the data, filling in optional fields as None if missing
        return TemperatureData(
            data=temperature_data,
            parameter=raw_data.get("parameter", None),
            station=raw_data.get("station", None),
            period=raw_data.get("period", None),
            link=raw_data.get("link", None),
        )
    except Exception as e:
        raise ValueError(f"Error parsing temperature data: {e}")


def calculate_monthly_means(temperature_data) -> List[MonthlyTemperature]:
    """Calculate monthly mean temperatures from either TemperatureData or DataFrame"""
    monthly_values = {}

    if isinstance(temperature_data, pd.DataFrame):
        # Handle DataFrame input
        monthly_means = temperature_data.groupby(
            temperature_data["time"].dt.strftime("%Y-%m")
        )["temperature"].mean()
        return [
            MonthlyTemperature(month=month, temperature=round(float(temp), 2))
            for month, temp in monthly_means.items()
        ]
    elif isinstance(temperature_data, TemperatureData):
        # Handle TemperatureData input
        for value in temperature_data.data:
            if value.value is None:
                continue
            month_key = value.date.strftime("%Y-%m") if value.date else "unknown"
            if month_key not in monthly_values:
                monthly_values[month_key] = []
            monthly_values[month_key].append(value.value)

        return [
            MonthlyTemperature(
                month=month, temperature=round(statistics.mean(values), 2)
            )
            for month, values in monthly_values.items()
            if values
        ]
    else:
        raise ValueError("Input must be either a DataFrame or TemperatureData object")
