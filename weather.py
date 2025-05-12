import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from cache import InMemoryCache
from settings import OPENWEATHER_API_KEY, OPENWEATHER_API_URL, OPENWEATHER_URL, WEATHER_LOCATION_QUERY
from utils import make_api_request

logger = logging.getLogger(__name__)

def get_lat_long(location: str, limit: int = 1):
    geocode_url = f"{OPENWEATHER_API_URL}/geo/1.0/direct"
    params = {
        "q": location,
        "limit": limit,
        "appid": OPENWEATHER_API_KEY,
    }
    status, msg, resp = make_api_request(geocode_url, "GET", params=params)
    if not status or not resp:
        logger.error(f"Geocode lookup failed: {msg}")
        return status, None
    resp = resp.json()
    if not resp:
        logger.error(f"No results found for {location}")
        return False, None
    
    return status, resp[0]

def get_weather(lat: float, lon: float):
    weather_url = f"{OPENWEATHER_API_URL}/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
    }
    status, msg, resp = make_api_request(weather_url, "GET", params=params)
    if not status or not resp.ok:
        logger.error(f"Weather lookup failed: {msg}")
        return status, None
    
    resp = resp.json()
    if not resp:
        logger.error(f"No results found for {lat}, {lon}")
        return False, None
    
    return status, resp


def get_weather_icon(weather_code: str):
    return f"{OPENWEATHER_URL}/img/wn/{weather_code}@2x.png"


def get_current_weather(request: Request):
    cache:InMemoryCache = request.app.cache
    key = f"weather-{WEATHER_LOCATION_QUERY}"
    cached = cache.get(key)
    if cached:
        return JSONResponse(content=cached, status_code=200)
    
    location = WEATHER_LOCATION_QUERY
    status, resp = get_lat_long(location)
    if not status:
        return JSONResponse(content={"message": "No location found"}, status_code=404)
    
    state = resp.get("state")
    country = resp.get("country")
    lat = resp.get("lat")
    lon = resp.get("lon")
    
    status, resp = get_weather(lat, lon)
    if not status:
        return JSONResponse(content={"message": "No weather found"}, status_code=404)
    
    response = {
        "weather": resp.get("weather")[0].get("main"),
        "temp": resp.get("main").get("temp"),
        "temp_min": resp.get("main").get("temp_min"),
        "temp_max": resp.get("main").get("temp_max"),
        "icon": get_weather_icon(resp.get("weather")[0].get("icon")),
        "city": resp.get("name"),
        "country": country,
        "state": state,
        "timezone": resp.get("timezone"),
    }

    cache.set(key, response, ttl=300)
    return JSONResponse(content=response, status_code=200)