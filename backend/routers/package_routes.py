import base64
import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from models.temperature_models import (
    AllCitiesTemperatureResponse,
    ChartResponse,
    CityTemperatureResponse,
    MonthlyTemperature,
    StationListResponse,
)

# Create output directory if needed
output_dir = Path(__file__).parent.parent.parent / "output"
output_dir.mkdir(exist_ok=True)

# Package-based router
router = APIRouter(
    prefix="/package",
    tags=["package_temperature"],
    responses={404: {"description": "Not found"}},
)

# Constants - Swedish cities to analyze
MAJOR_CITIES = ["Stockholm", "Göteborg", "Malmö", "Uppsala", "Umeå"]


@router.get("/cities/data", response_model=AllCitiesTemperatureResponse)
async def get_cities_temperature_data():
    """
    Get temperature data for the five major Swedish cities for the last 12 months.
    Returns monthly mean temperatures for Stockholm, Göteborg, Malmö, Uppsala and Umeå.
    """
    try:
        import smhi_open_data

        # Collect data for all cities
        all_data = {}
        combined_monthly_data = []

        for city in MAJOR_CITIES:
            try:
                # Get station data for the city
                station = _find_station_by_name(city)
                if not station:
                    continue

                # Get temperature data for the last 12 months
                df = _get_city_data(city, station)
                if df is None or df.empty:
                    continue

                # Calculate monthly means
                monthly_df = _calculate_monthly_means(df)

                # Convert to response model format
                monthly_temps = []
                for _, row in monthly_df.iterrows():
                    monthly_temps.append(
                        MonthlyTemperature(
                            month=row["month"], temperature=row["temperature"]
                        )
                    )

                # Store in result
                all_data[city] = CityTemperatureResponse(
                    city=city,
                    station_id=station.station_id,
                    station_name=station.name,
                    monthly_means=monthly_temps,
                )

                # Add to combined data
                if not combined_monthly_data:
                    combined_monthly_data = monthly_df.copy()
                    combined_monthly_data.rename(
                        columns={"temperature": city}, inplace=True
                    )
                else:
                    combined_monthly_data[city] = monthly_df["temperature"].values

            except Exception as e:
                continue

        if not all_data:
            raise HTTPException(
                status_code=404, detail="No temperature data found for major cities"
            )

        # Calculate mean of all cities
        if not combined_monthly_data.empty:
            combined_monthly_data["Average"] = combined_monthly_data[
                list(all_data.keys())
            ].mean(axis=1)

        return AllCitiesTemperatureResponse(
            cities=all_data,
            combined_data=combined_monthly_data.to_dict("records")
            if not combined_monthly_data.empty
            else None,
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="SMHI package not available")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting temperature data: {str(e)}"
        )


@router.get("/cities/chart", response_model=ChartResponse)
async def get_cities_temperature_chart():
    """
    Generate a chart showing temperature data for the five major Swedish cities
    for the last 12 months, including the mean of all cities.
    """
    try:
        import matplotlib
        import smhi_open_data

        matplotlib.use("Agg")  # Use non-interactive backend

        # Get data for all cities
        all_data = {}
        combined_df = pd.DataFrame()

        for city in MAJOR_CITIES:
            try:
                # Get station data
                station = _find_station_by_name(city)
                if not station:
                    continue

                # Get temperature data
                df = _get_city_data(city, station)
                if df is None or df.empty:
                    continue

                # Calculate monthly means
                monthly_df = _calculate_monthly_means(df)

                # Store in result
                all_data[city] = monthly_df

                # Add to combined dataframe
                if combined_df.empty:
                    combined_df = monthly_df.copy()
                    combined_df.rename(columns={"temperature": city}, inplace=True)
                else:
                    combined_df[city] = monthly_df["temperature"].values

            except Exception as e:
                continue

        if not all_data:
            raise HTTPException(
                status_code=404, detail="No temperature data found for major cities"
            )

        # Calculate mean of all cities
        if not combined_df.empty:
            combined_df["Average"] = combined_df[list(all_data.keys())].mean(axis=1)

        # Generate chart
        plt.figure(figsize=(12, 8))

        # Plot each city
        for city in all_data.keys():
            plt.plot(combined_df["month"], combined_df[city], marker="o", label=city)

        # Plot the average
        if "Average" in combined_df.columns:
            plt.plot(
                combined_df["month"],
                combined_df["Average"],
                marker="*",
                linewidth=3,
                linestyle="--",
                color="black",
                label="Average",
            )

        plt.title("Mean Monthly Temperatures for Major Swedish Cities (Last 12 Months)")
        plt.xlabel("Month")
        plt.ylabel("Temperature (°C)")
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.legend()
        plt.tight_layout()

        # Save image to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100)
        buf.seek(0)

        # Also save to file for reference
        chart_path = output_dir / "temperature_chart.png"
        plt.savefig(chart_path, format="png", dpi=100)

        # Convert to base64 for embedding in HTML
        image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        plt.close()

        return ChartResponse(
            image_data=f"data:image/png;base64,{image_base64}",
            chart_path=str(chart_path),
        )

    except ImportError:
        raise HTTPException(
            status_code=500, detail="SMHI package or plotting libraries not available"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")


@router.get("/city/{city_name}", response_model=CityTemperatureResponse)
async def get_city_temperature(city_name: str):
    """
    Get temperature data for a specific city for the last 12 months.

    - **city_name**: Name of the city
    """
    try:
        import smhi_open_data

        # Get station data
        station = _find_station_by_name(city_name)
        if not station:
            raise HTTPException(
                status_code=404, detail=f"No station found for city: {city_name}"
            )

        # Get temperature data
        df = _get_city_data(city_name, station)
        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No temperature data found for city: {city_name}",
            )

        # Calculate monthly means
        monthly_df = _calculate_monthly_means(df)

        # Convert to response model
        monthly_temps = []
        for _, row in monthly_df.iterrows():
            monthly_temps.append(
                MonthlyTemperature(month=row["month"], temperature=row["temperature"])
            )

        return CityTemperatureResponse(
            city=city_name,
            station_id=station.station_id,
            station_name=station.name,
            monthly_means=monthly_temps,
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="SMHI package not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching temperature data: {str(e)}"
        )


# Helper functions
def _find_station_by_name(name: str):
    """Find a station by name using the SMHI package"""
    import smhi_open_data

    name_lower = name.lower()
    stations = smhi_open_data.smhi_open_data.get_parameter_stations(
        smhi_open_data.Parameter.Temperature
    )

    # Try exact match first
    for station in stations:
        if station.name.lower() == name_lower:
            return station

    # Try partial match
    for station in stations:
        if name_lower in station.name.lower():
            return station

    return None


def _get_city_data(city_name: str, station):
    """Get temperature data for a city using the SMHI package"""
    import smhi_open_data

    # Get data for the last 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # Get station data for temperature parameter
    try:
        period = (
            smhi_open_data.Period.Latest_months
            if hasattr(smhi_open_data, "Period")
            else "latest-months"
        )
        station_data = smhi_open_data.smhi_open_data.get_station_data(
            smhi_open_data.Parameter.Temperature, station.station_id, period
        )

        if not station_data or not station_data.value:
            return None

        # Format as DataFrame
        times = []
        values = []

        for value in station_data.value:
            if "date" in value and "value" in value:  # Handle different API formats
                date_time = pd.to_datetime(value["date"])
                if start_date.date() <= date_time.date() <= end_date.date():
                    times.append(date_time)
                    values.append(float(value["value"]))
            elif hasattr(value, "date") and hasattr(value, "value"):
                date_time = pd.to_datetime(value.date)
                if start_date.date() <= date_time.date() <= end_date.date():
                    times.append(date_time)
                    values.append(float(value.value))

        if not times:
            return None

        df = pd.DataFrame({"time": times, "temperature": values})

        return df

    except Exception as e:
        print(f"Error getting data for {city_name}: {e}")
        return None


def _calculate_monthly_means(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly mean temperatures from daily data"""
    # Add month column for grouping
    df["month"] = df["time"].dt.strftime("%Y-%m")

    # Group by month and calculate mean
    monthly_means = df.groupby("month")["temperature"].mean().reset_index()

    # Ensure the months are in chronological order
    monthly_means = monthly_means.sort_values("month")

    return monthly_means
