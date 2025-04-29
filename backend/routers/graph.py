from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from models.temperature_models import MonthlyTemperature
from src.city_service import (
    MAJOR_CITIES,
    find_station_by_city_name,
    get_city_data,
    get_city_historical_data,
    get_city_monthly_data,
    get_major_cities_data,
)
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

        # If not in predefined list, search for the city in SMHI stations
        if not station_id:
            station = find_station_by_city_name(city_name)
            if not station:
                raise HTTPException(
                    status_code=404, detail=f"No station found for city: {city_name}."
                )
            station_id = station.get("id")
            station_name = station.get("name")
        else:
            station_name = city_name

        print(
            f"Getting temperature graph data for {city_name} (station {station_id})"
        )  # Debug log

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
            "station_name": station_name,
            "station_id": station_id,
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


@router.get("/historical/{city_name}")
async def get_city_historical_data_endpoint(
    city_name: str, 
    from_year: Optional[int] = Query(None, description="Start year for filtering data"),
    to_year: Optional[int] = Query(None, description="End year for filtering data")
):
    """
    Get historical temperature data for a specific city.
    This uses the corrected-archive period which contains older data.
    
    - **city_name**: Name of the city to get data for
    - **from_year**: Optional start year to filter data
    - **to_year**: Optional end year to filter data
    """
    try:
        # Check if city is in our predefined list
        station_id = MAJOR_CITIES.get(city_name)

        # If not in predefined list, search for the city in SMHI stations
        if not station_id:
            station = find_station_by_city_name(city_name)
            if not station:
                raise HTTPException(
                    status_code=404, detail=f"No station found for city: {city_name}."
                )
            station_id = station.get("id")
            station_name = station.get("name")
        else:
            station_name = city_name

        print(
            f"Getting historical temperature data for {city_name} (station {station_id})"
        )  # Debug log

        # Get historical temperature data
        df = get_city_historical_data(city_name, station_id)
        if df is None:
            raise HTTPException(
                status_code=404, detail=f"No historical data available for {city_name}"
            )
            
        # Apply year filters if provided
        if from_year:
            df = df[df['time'].dt.year >= from_year]
        if to_year:
            df = df[df['time'].dt.year <= to_year]
            
        if df.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"No data found for {city_name} within the specified year range"
            )

        # Group data by year and month for better visualization
        df['year_month'] = df['time'].dt.strftime('%Y-%m')
        
        # Calculate monthly means for each year-month combination
        monthly_data = df.groupby('year_month').agg({
            'temperature': 'mean',
            'time': 'first'  # Keep one timestamp for reference
        }).reset_index()
        
        # Sort by time for chronological display
        monthly_data = monthly_data.sort_values('time')
        
        # Format response
        result = {
            "city": city_name,
            "station_name": station_name,
            "station_id": station_id,
            "data_points": len(df),
            "period": "historical",
            "time_range": {
                "start": df['time'].min().strftime('%Y-%m-%d'),
                "end": df['time'].max().strftime('%Y-%m-%d')
            },
            "months": monthly_data['year_month'].tolist(),
            "temperatures": monthly_data['temperature'].round(2).tolist(),
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving historical data for {city_name}: {str(e)}",
        )


@router.get("/monthly/{city_name}")
async def get_city_monthly_data_endpoint(city_name: str):
    """
    Get monthly temperature data for a specific city for the past 12 months.
    This uses the latest-months period which has more detailed hourly data.
    
    - **city_name**: Name of the city to get data for
    """
    try:
        # Check if city is in our predefined list
        station_id = MAJOR_CITIES.get(city_name)

        # If not in predefined list, search for the city in SMHI stations
        if not station_id:
            station = find_station_by_city_name(city_name)
            if not station:
                raise HTTPException(
                    status_code=404, detail=f"No station found for city: {city_name}."
                )
            station_id = station.get("id")
            station_name = station.get("name")
        else:
            station_name = city_name

        print(
            f"Getting monthly temperature data for {city_name} (station {station_id})"
        )  # Debug log

        # Get monthly temperature data
        df = get_city_monthly_data(city_name, station_id)
        if df is None:
            raise HTTPException(
                status_code=404, detail=f"No monthly data available for {city_name}"
            )

        # Group data by day to get daily averages for a cleaner visualization
        df['date'] = df['time'].dt.date
        daily_data = df.groupby('date').agg({
            'temperature': 'mean',
            'time': 'first'  # Keep one timestamp for reference
        }).reset_index()
        
        # Group data by month for monthly averages
        df['year_month'] = df['time'].dt.strftime('%Y-%m')
        monthly_data = df.groupby('year_month').agg({
            'temperature': 'mean',
            'time': 'first'  # Keep one timestamp for reference
        }).reset_index()
        
        # Sort by time for chronological display
        monthly_data = monthly_data.sort_values('time')
        
        # Format response
        result = {
            "city": city_name,
            "station_name": station_name,
            "station_id": station_id,
            "data_points": len(df),
            "period": "monthly",
            "time_range": {
                "start": df['time'].min().strftime('%Y-%m-%d'),
                "end": df['time'].max().strftime('%Y-%m-%d')
            },
            "months": monthly_data['year_month'].tolist(),
            "temperatures": monthly_data['temperature'].round(2).tolist(),
            # Also include daily data for more detailed view if needed
            "daily": {
                "dates": [d.strftime('%Y-%m-%d') for d in daily_data['date']],
                "temperatures": daily_data['temperature'].round(2).tolist()
            }
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving monthly data for {city_name}: {str(e)}",
        )
