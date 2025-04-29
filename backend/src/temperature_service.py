from typing import Dict, List

from models.temperature_models import (
    AllCitiesTemperatureResponse,
    CityTemperatureResponse,
    MonthlyTemperature,
)
from utils import smhi_api


class TemperatureService:
    async def get_city_temperature(self, city_name: str) -> CityTemperatureResponse:
        station = await smhi_api.get_station_by_city(city_name)
        raw_data = await smhi_api.get_temperature_data(station.id)
        monthly_means = smhi_api.calculate_monthly_means(raw_data)

        monthly_temperature = [
            MonthlyTemperature(month=month, temperature=temp)
            for month, temp in monthly_means.items()
        ]

        return CityTemperatureResponse(
            city=city_name,
            station_id=station.id,
            station_name=station.name,
            monthly_means=monthly_temperature,
        )

    async def compare_cities(self, cities: List[str]) -> AllCitiesTemperatureResponse:
        cities_data: Dict[str, CityTemperatureResponse] = {}
        combined_months: Dict[str, List[float]] = {}

        for city in cities:
            city_data = await self.get_city_temperature(city)
            cities_data[city] = city_data

            for month_temp in city_data.monthly_means:
                if month_temp.month not in combined_months:
                    combined_months[month_temp.month] = []
                combined_months[month_temp.month].append(month_temp.temperature)

        combined_data = [
            {"month": month, "temperature": round(sum(temps) / len(temps), 2)}
            for month, temps in combined_months.items()
        ]

        return AllCitiesTemperatureResponse(
            cities=cities_data, combined_data=combined_data
        )
