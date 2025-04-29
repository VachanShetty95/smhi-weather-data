from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from models.temperature_models import MonthlyTemperature
from src.city_service import MAJOR_CITIES, get_city_data, get_major_cities_data
from utils.smhi_api import calculate_monthly_means

router = APIRouter(
    prefix="/graph",
    tags=["graph_data"],
    responses={404: {"description": "Not found"}},
)


@router.get("/cities")
async def get_temperature_graph_data():
    """
    Get temperature data for major Swedish cities for the last 12 months.
    Returns data formatted for easy plotting in a graph.
    """
    try:
        # Get data for each major city
        city_data_map = get_major_cities_data()
        if not city_data_map:
            raise HTTPException(
                status_code=404,
                detail="No temperature data available for any major city",
            )

        # Convert to monthly means for each city
        result = {"months": [], "cities": {}, "average": []}

        # First, collect all months across all cities
        all_months = set()
        city_monthly_data = {}

        for city, df in city_data_map.items():
            monthly_temps = calculate_monthly_means(df)
            city_monthly_data[city] = {
                item.month: item.temperature for item in monthly_temps
            }
            for item in monthly_temps:
                all_months.add(item.month)

        # Sort months chronologically
        sorted_months = sorted(
            list(all_months), key=lambda x: pd.to_datetime(x, format="%Y-%m")
        )
        result["months"] = sorted_months

        # For each city, provide temperature values for all months (null if missing)
        for city, monthly_data in city_monthly_data.items():
            result["cities"][city] = [
                monthly_data.get(month) for month in sorted_months
            ]

        # Calculate average across all cities for each month
        month_totals = {month: [] for month in sorted_months}

        for city, monthly_data in city_monthly_data.items():
            for month in sorted_months:
                if month in monthly_data:
                    month_totals[month].append(monthly_data[month])

        result["average"] = [
            round(sum(values) / len(values), 2) if values else None
            for month, values in [(m, month_totals[m]) for m in sorted_months]
        ]

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving graph data: {str(e)}"
        )


@router.get("/city/{city_name}")
async def get_city_temperature_graph_data(city_name: str):
    """
    Get temperature data for a specific city for the last 12 months.
    Returns data formatted for easy plotting in a graph.
    """
    try:
        # Check if city is in our predefined list
        station_id = MAJOR_CITIES.get(city_name)

        if not station_id:
            raise HTTPException(
                status_code=404,
                detail=f"City not found in predefined list: {city_name}",
            )

        # Get temperature data
        df = get_city_data(city_name, station_id)
        if df is None:
            raise HTTPException(
                status_code=404, detail=f"No temperature data available for {city_name}"
            )

        # Calculate monthly means
        monthly_temps = calculate_monthly_means(df)
        if not monthly_temps:
            raise HTTPException(
                status_code=404,
                detail=f"No monthly temperature data available for {city_name}",
            )

        # Sort months chronologically
        sorted_data = sorted(
            monthly_temps, key=lambda x: pd.to_datetime(x.month, format="%Y-%m")
        )

        # Format response for graphing
        result = {
            "city": city_name,
            "months": [item.month for item in sorted_data],
            "temperatures": [item.temperature for item in sorted_data],
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving graph data for {city_name}: {str(e)}",
        )
