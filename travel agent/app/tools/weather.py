# app/tools/weather.py
from semantic_kernel.functions import kernel_function
import requests
import json
from app.utils.logger import setup_logger

logger = setup_logger("weather_tool")

class WeatherTools:
    @kernel_function(name="get_weather", description="Get 7-day weather forecast for a given city.")
    def get_weather(self, city: str) -> str:
        """
        Gets the 7-day weather forecast for a given city and returns a simple summary string.

        TODO: Implement weather retrieval
        - Geocoding API: https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1
          - Extract lat/lon from: response["results"][0]["latitude"], ["longitude"]
        - Weather API: https://api.open-meteo.com/v1/forecast
          - Parameters: latitude, longitude, daily=weathercode,temperature_2m_max,temperature_2m_min, forecast_days=7, timezone=UTC
        - Weather codes: ≤1 = Sunny, ≤3 = Cloudy, >50 = Rainy, else Mixed
        - Return a summary string with average temperature and conditions
        """
        logger.info(f"Weather tool called with city={city}")

        try:
            # 1. Geocode the city name to latitude/longitude
            geo_resp = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1},
                timeout=10
            )
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()

            results = geo_data.get("results")
            if not results:
                return json.dumps({"error": f"Could not geocode city: {city}"})

            lat = results[0]["latitude"]
            lon = results[0]["longitude"]
            resolved_name = results[0].get("name", city)

            # 2. Fetch the 7-day forecast for those coordinates
            weather_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                    "forecast_days": 7,
                    "timezone": "UTC"
                },
                timeout=10
            )
            weather_resp.raise_for_status()
            daily = weather_resp.json().get("daily", {})

            highs = daily.get("temperature_2m_max", [])
            lows = daily.get("temperature_2m_min", [])
            codes = daily.get("weathercode", [])

            if not highs or not lows or not codes:
                return json.dumps({"error": f"No weather data returned for {city}"})

            # 3. Summarize: average temperature and dominant conditions
            avg_temp = round(sum(highs + lows) / (len(highs) + len(lows)), 1)
            avg_code = sum(codes) / len(codes)

            if avg_code <= 1:
                conditions = "Sunny"
            elif avg_code <= 3:
                conditions = "Cloudy"
            elif avg_code > 50:
                conditions = "Rainy"
            else:
                conditions = "Mixed"

            summary = {
                "city": resolved_name,
                "temperature_c": avg_temp,
                "conditions": conditions,
                "summary": f"7-day forecast for {resolved_name}: average {avg_temp}°C, {conditions.lower()} conditions."
            }
            logger.info(f"Weather summary: {summary['summary']}")
            return json.dumps(summary, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ Weather tool failed: {e}")
            return json.dumps({"error": f"Failed to get weather for {city}: {e}"})
