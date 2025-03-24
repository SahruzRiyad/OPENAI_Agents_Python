import os , requests, json
from datetime import date, timedelta
from agents import Agent, Runner
from pydantic import BaseModel

flight_api_key = os.getenv("FLIGHT_API_KEY")
model = os.getenv("MODEL_NAME")

class FlightRecommendation(BaseModel):
    airline: str
    departure_time: str 
    arrival_time: str 
    price: float 
    direct_flight: bool
    recommendation_reason: str


def date_current_plus_5():
    new_date = date.today() + timedelta(days=5)
    new_date_str = new_date.strftime("%Y-%m-%d")
    return new_date_str


async def search_flight_tool(origin: str , destination: str, depart_date: str, direct: bool):
    base_url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

    params = {
        "origin": origin,
        "destination": destination,
        "departure_at": depart_date,
        "currency": "usd",
        "sorting": "price",
        "direct": direct,
        "token": flight_api_key 
    }
    try:
        response = await requests.get(base_url, params=params)

        if response.status_code == 200:
            return json.dumps(response['data'])
        else: 
            return {"Error": "Error in fetching flights"}
    except:
        return {"Error": "Error in fetching flights"}
    

flight_search_agent = Agent(
    name="Flight Specialist",
    handoff_description="Speacialist agent for finding and recommending best fligts.",
    instructions="""
    You are a flight specialist that helps user to recommend best flights option,
    You use get_flights_tool to find flight options and the provide personalize recommendations,
    Always explain reasoning behind your recommendations. 
    Format your response in a clear organized way, with flight details, and price.. 
    """,
    model = model,
    tools=[search_flight_tool],
    output_type=FlightRecommendation
)

async def run_task():
    query = "Find a direct Flight from MAD to BCN, from 2025-04 to 2025-5"

    result = await Runner.run(flight_search_agent, query)

    flight = result.final_output
    print("\n✈️ FLIGHT RECOMMENDATION ✈️")
    print(f"Airline: {flight.airline}")
    print(f"Departure: {flight.departure_time}")
    print(f"Arrival: {flight.arrival_time}")
    print(f"Price: ${flight.price}")
    print(f"Direct Flight: {'Yes' if flight.direct_flight else 'No'}")
    print(f"\nWhy this flight: {flight.recommendation_reason}")