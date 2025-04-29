from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from models.temperature_models import (
    AllCitiesTemperatureResponse,
    CityTemperatureResponse,
    MonthlyTemperature,
    Station,
)
from src.city_service import (
    MAJOR_CITIES,
    find_station_by_city_name,
    get_city_data,
    get_major_cities_data,
    search_stations_by_name,
)
from utils.smhi_api import calculate_monthly_means

router = APIRouter(
    prefix="/cities",
    tags=["city_data"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{city_name}", response_model=CityTemperatureResponse)
async def get_city_temperature(city_name: str):
    """Get temperature data for a specific city"""
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
            f"Getting temperature data for {city_name} (station {station_id})"
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

        return CityTemperatureResponse(
            city=city_name,
            station_id=station_id,
            station_name=station_name,
            monthly_means=monthly_temps,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_city_temperature for {city_name}: {str(e)}")  # Debug log
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving temperature data for {city_name}: {str(e)}",
        )


@router.get("/search/{query}", response_model=List[Station])
async def search_city(query: str):
    """Search for stations by city name"""
    try:
        if not query or len(query) < 2:
            raise HTTPException(
                status_code=400,
                detail="Search query must be at least 2 characters long",
            )

        matching_stations = search_stations_by_name(query)

        return matching_stations

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error searching for city {query}: {str(e)}")  # Debug log
        raise HTTPException(
            status_code=500, detail=f"Error searching for stations: {str(e)}"
        )


@router.get("/", response_model=AllCitiesTemperatureResponse)
async def get_all_cities_temperature():
    """Get temperature data for all major Swedish cities"""
    try:
        cities_data = {}
        combined_monthly_data = pd.DataFrame()

        # Get data for each major city
        city_data_map = get_major_cities_data()

        for city, df in city_data_map.items():
            try:
                station_id = MAJOR_CITIES[city]

                # Calculate monthly means
                monthly_temps = calculate_monthly_means(df)
                if not monthly_temps:
                    print(f"No monthly means available for {city}")
                    continue

                # Add to city data
                cities_data[city] = CityTemperatureResponse(
                    city=city,
                    station_id=station_id,
                    station_name=city,
                    monthly_means=monthly_temps,
                )

                # Add to combined data for average calculation
                if not df.empty:
                    df["city"] = city
                    combined_monthly_data = pd.concat([combined_monthly_data, df])

            except Exception as e:
                print(f"Error processing data for {city}: {e}")
                continue

        if not cities_data:
            raise HTTPException(
                status_code=404,
                detail="No temperature data available for any major city",
            )

        # Calculate combined data (average across all cities)
        combined_data = []
        if not combined_monthly_data.empty:
            combined_monthly_data.set_index("time", inplace=True)
            avg_monthly = combined_monthly_data.groupby(pd.Grouper(freq="M"))[
                "temperature"
            ].mean()

            for date, temp in avg_monthly.items():
                if pd.isna(temp):
                    continue
                combined_data.append(
                    {
                        "month": date.strftime("%Y-%m"),
                        "temperature": round(float(temp), 2),
                    }
                )

        return AllCitiesTemperatureResponse(
            cities=cities_data, combined_data=combined_data
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving temperature data: {str(e)}"
        )
