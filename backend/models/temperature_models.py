from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TemperatureResponse(BaseModel):
    data: Dict[str, Any]


class Station(BaseModel):
    """Model representing a weather station"""

    id: int
    name: str
    owner: str
    owner_category: Optional[str] = None
    latitude: float = Field(..., description="Latitude in WGS84 decimal degrees")
    longitude: float = Field(..., description="Longitude in WGS84 decimal degrees")
    height: Optional[float] = Field(
        None, description="Height above sea level in meters"
    )
    active: bool = True


# class TemperatureValue(BaseModel):
#     """Model representing a single temperature measurement"""
#     date: datetime
#     value: float
#     quality: Optional[str] = None


class TemperatureValue(BaseModel):
    """Model representing a single temperature measurement"""

    date: Optional[datetime] = None
    value: Optional[float] = None
    quality: Optional[str] = None


class TemperatureData(BaseModel):
    """Model representing temperature data for a station"""

    parameter: Optional[Dict[str, Any]] = None
    station: Optional[Dict[str, Any]] = None
    period: Optional[Dict[str, Any]] = None
    link: Optional[List[Dict[str, Any]]] = None
    data: List[TemperatureValue]


class MonthlyTemperature(BaseModel):
    """Model representing monthly mean temperature"""

    month: str
    temperature: float


class CityTemperatureResponse(BaseModel):
    """Response model for city temperature data"""

    city: str
    station_id: int
    station_name: str
    monthly_means: List[MonthlyTemperature]


class AllCitiesTemperatureResponse(BaseModel):
    """Response model for temperature data from multiple cities"""

    cities: Dict[str, CityTemperatureResponse]
    combined_data: Optional[List[Dict[str, Any]]] = None


class ChartResponse(BaseModel):
    """Response model for temperature chart data"""

    image_data: str = Field(..., description="Base64 encoded chart image data")
    chart_path: str = Field(..., description="Path to the saved chart file")


class StationListResponse(BaseModel):
    """Response model for station list"""

    stations: List[Station]


class ErrorResponse(BaseModel):
    """Response model for errors"""

    detail: str


class WeatherInfoResponse(BaseModel):
    """Model representing a single weather forecast point"""

    valid_time: str
    temperature: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    precipitation: Optional[float] = None
    cloud_cover: Optional[float] = None


class ForecastResponse(BaseModel):
    """Response model for forecast data"""

    reference_time: str
    approved_time: str
    latitude: float
    longitude: float
    forecasts: List[WeatherInfoResponse]


class WeatherSummary(BaseModel):
    """Model representing a weather summary"""

    current_temp: Optional[float] = None
    daily_high: Optional[float] = None
    daily_low: Optional[float] = None
    conditions: Optional[str] = None
    icon: Optional[str] = None

    @classmethod
    def from_forecast(cls, forecast_data: ForecastResponse) -> "WeatherSummary":
        """Create a summary from forecast data"""
        if not forecast_data or not forecast_data.forecasts:
            return cls()

        # First forecast is current weather
        current = forecast_data.forecasts[0]
        current_temp = current.temperature

        # Calculate daily high and low (first 24 hours)
        daily_forecasts = forecast_data.forecasts[:24]
        temps = [f.temperature for f in daily_forecasts if f.temperature is not None]
        daily_high = max(temps) if temps else None
        daily_low = min(temps) if temps else None

        # Determine conditions based on cloud cover and precipitation
        conditions = "Unknown"
        icon = "question"

        if current.cloud_cover is not None and current.precipitation is not None:
            if current.cloud_cover <= 1:  # 0-1 octas (clear)
                conditions = "Clear"
                icon = "sun"
            elif current.cloud_cover <= 3:  # 2-3 octas (partly cloudy)
                conditions = "Partly cloudy"
                icon = "cloud-sun"
            elif current.cloud_cover <= 6:  # 4-6 octas (mostly cloudy)
                conditions = "Mostly cloudy"
                icon = "cloud"
            else:  # 7-8 octas (overcast)
                conditions = "Overcast"
                icon = "cloud"

            # Check for precipitation
            if current.precipitation and current.precipitation > 0:
                if current_temp is not None and current_temp < 0:
                    conditions = "Snow"
                    icon = "snowflake"
                else:
                    conditions = "Rain"
                    icon = "cloud-rain"

                    # Heavy rain
                    if current.precipitation > 3:
                        conditions = "Heavy rain"
                        icon = "cloud-showers-heavy"

        return cls(
            current_temp=current_temp,
            daily_high=daily_high,
            daily_low=daily_low,
            conditions=conditions,
            icon=icon,
        )


class CityTemperatureData(BaseModel):
    """Model representing temperature data for a city"""

    city_name: str
    station_id: int
    temperatures: List[TemperatureValue]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
