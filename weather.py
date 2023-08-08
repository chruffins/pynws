from dataclasses import dataclass
import json
import datetime
from math import sqrt
from typing import Any

import requests

from geocoding import Coordinates, get_coords_from_address

POINTS_API_URL = "https://api.weather.gov/points/{0:.4f},{1:.4f}"

class LocationData:
    def __init__(self, points_json: Any, max_age: int = 0) -> None:
        self.x: int = points_json['properties']['gridX']
        self.y: int = points_json['properties']['gridY']

        self.cwa: str = points_json['properties']['cwa']

        self.weekly_forecast_url: str = points_json['properties']['forecast']
        self.hourly_forecast_url: str = points_json['properties']['forecastHourly']
        self.forecast_grid_data_url: str = points_json['properties']['forecastGridData']

        self.timezone: str = points_json['properties']['timeZone']

        self.max_age = max_age
        self.created = datetime.datetime.now()
        #self.forecast_zone_url: str = points_json['properties']['forecastZone']
    
    def is_expired(self) -> bool:
        return datetime.datetime.now() - self.created > self.max_age

class Forecast:
    def __init__(self, forecast_json) -> None:
        self.name: str = forecast_json['name']

        self.start_time: datetime.datetime = datetime.datetime.fromisoformat(forecast_json['startTime'])
        self.end_time: datetime.datetime = datetime.datetime.fromisoformat(forecast_json['endTime'])

        self.is_daytime: bool = forecast_json['isDaytime']

        self.temperature: int = forecast_json['temperature']
        self.temperature_unit: str = forecast_json['temperatureUnit']

        self.precipitation_prob: int = forecast_json['probabilityOfPrecipitation']['value']
        self.relative_humidity: int = forecast_json['relativeHumidity']['value']

        self.dew_point: int = forecast_json['dewpoint']['value']
        self.dew_point_unit: str = forecast_json['dewpoint']['unitCode']

        self.wind_speed: str = forecast_json['windSpeed']
        self.wind_speed_direction: str = forecast_json['windDirection']

        self.short_forecast: str = forecast_json['shortForecast']
        self.detailed_forecast: str = forecast_json['detailedForecast']

    def heat_index(self):
        """
        Calculates the heat index for the forecast from the formula described at https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml.
        """

        # for less verbosity
        t: int = self.temperature
        rh: int = self.relative_humidity

        # simple formula that works for heat indices below 80 deg F
        hi: float = 0.5 * (t + 61.0 + ((t - 68.0) * 1.2) + (rh * 0.094))

        # more accurate formula above 80 deg F
        if hi >= 80:
            hi = -42.379 + 2.04901523*t + 10.14333127*rh - .22475541*t*rh - .00683783*t*t - .05481717*rh*rh + .00122874*t*t*rh + .00085282*t*rh*rh - .00000199*t*t*rh*rh

            # adjustments for certain conditions
            if 80 <= t and t <= 112 and rh < 13:
                hi -= ((13 - rh) / 4) * sqrt((17 - abs(t - 95)) / 17)
            elif rh > 85 and 80 <= t and t <= 87:
                hi += ((rh - 85) / 10) * ((87 - t) / 5)

        return hi
    
    def __str__(self) -> str:
        return "{0} - {1}".format(self.name, self.short_forecast)

class WeeklyForecast:
    def __init__(self, forecast_json: Any, max_age: int = 0) -> None:
        self.forecasts: list[Forecast] = list(map(Forecast, forecast_json['properties']['periods']))

        self.max_age = max_age
        self.created = datetime.datetime.now()
    
    def is_expired(self) -> bool:
        return datetime.datetime.now() - self.created > self.max_age
    
    def __iter__(self):
        return iter(self.forecasts)
    
    def __str__(self):
        return "WeeklyForecast({0} - {1})".format(self.forecasts[0].start_time.strftime('dd/mm/yy'), self.forecasts[-1].end_time.strftime('dd/mm/yy'))
    
    def today(self) -> Forecast:
        return self.forecasts[0]

class NWSClient:
    def __init__(self, user_agent: str) -> None:
        assert user_agent is not None and user_agent != "", "The NWS API requires a User-Agent string!"

        self.user_agent = user_agent

    def get_location_data(self, coords: Coordinates) -> LocationData:
        url_string = POINTS_API_URL.format(coords.lat, coords.long)

        r: requests.Response
        response: Any
        
        try:
            r = requests.get(url_string, headers={'User-Agent': self.user_agent})
            r.raise_for_status()
        except Exception as e:
        # decode json and raise error if necessary
            response = json.loads(r.content)
            if response.get("errors"):
                raise ValueError(response['errors'])
            else:
                raise e
            
        # rip the coordinates out of the json
        response = json.loads(r.content)
            
        return LocationData(response)
    
    def get_weekly_forecast(self, coords: Coordinates, cached_result: WeeklyForecast | None = None) -> WeeklyForecast:
        if cached_result and not cached_result.is_expired():
            return cached_result

        loc_data = self.get_location_data(coords)

        weekly_url = loc_data.weekly_forecast_url
        r: requests.Response
        response: Any

        try:
            r = requests.get(weekly_url, headers={'User-Agent': self.user_agent})
            r.raise_for_status()
        except Exception as e:
            # decode json and raise error if necessary
            response = json.loads(r.content)
            if response.get("errors"):
                raise ValueError(response['errors'])
            else:
                raise e
            
        # rip the coordinates out of the json
        response = json.loads(r.content)

        return WeeklyForecast(response)
        

if __name__ == "__main__":
    c = NWSClient("chris lee - lee4cr@mail.uc.edu")
    cincy_coords = get_coords_from_address("4064 Royal Dornoch Lane", "Mason", "OH")

    weekly_forecast = c.get_weekly_forecast(cincy_coords)

    for forecast in weekly_forecast:
        print(forecast, forecast.temperature, forecast.relative_humidity, forecast.heat_index())
    