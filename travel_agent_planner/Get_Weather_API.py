import os, requests

weather_api_key = os.getenv("GET_WEATHER_API_KEY")

async def get_weather_tool(city: str):
    base_url = "http://api.weatherapi.com/v1/current.json"
    params = {
        "key": weather_api_key,
        "q": city
    }

    try:
        response = await requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            location = data['location']['name']
            temp_c = data['current']['temp_c']
            condition = data['current']['condition']['text']
         
            return {
                "location": location,
                "temperature": f"{temp_c}°C",
                "condition": condition
            }
        else:
            return {"location": city, "temperature": "N/A", "condition": "Unknown"}
    except Exception as e:
        return {"location": city, "temperature": "N/A", "condition": "Unknown"}