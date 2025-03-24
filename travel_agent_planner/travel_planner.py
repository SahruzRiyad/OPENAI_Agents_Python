import os , requests
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool , InputGuardrailTripwireTriggered, InputGuardrail, GuardrailFunctionOutput, RunContextWrapper
from pydantic import BaseModel, Field
from typing import List, Optional
import asyncio, json
from dataclasses import dataclass
from datetime import datetime


# -- Setting API KEY and MODEL ---
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
model = os.getenv("MODEL_NAME")


# --- Models for structured outputs ---
class TravelPlan(BaseModel):
    destination: str
    duration_days: int
    budget: float
    activities: List[str] = Field(description="List of recommended activities")
    notes: str = Field(description="Additional notes or recommendations")

class FlightRecommendation(BaseModel):
    airline: str
    departure_time: str 
    arrival_time: str 
    price: float 
    direct_flight: bool
    recommendation_reason: str

class HotelRecommendation(BaseModel):
    name: str 
    location: str
    price_per_night: float
    amenities: List[str]
    recommendation_reason: str

# --- Context Class ---
@dataclass
class UserContext:  
    user_id: str
    preferred_airlines: List[str] = None
    hotel_amenities: List[str] = None
    budget_level: str = None
    session_start: datetime = None
    
    def __post_init__(self):
        if self.preferred_airlines is None:
            self.preferred_airlines = []
        if self.hotel_amenities is None:
            self.hotel_amenities = []
        if self.session_start is None:
            self.session_start = datetime.now()

# --- Guardrail Class ---
class BudgetAnalysis(BaseModel):
    is_realistic: bool
    reasoning: str
    suggested_budget: Optional[float] = None

# --- Guardrails for Agents ---
budget_analysis_agent = Agent(
    name="Budget Analyzer",
    instructions="""
    You analyze travel budgets to determine if they are realistic for the destination and duration.
    Consider factors like:
    - Average hotel costs in the destination
    - Flight costs
    - Food and entertainment expenses
    - Local transportation
    
    Provide a clear analysis of whether the budget is realistic and why.
    If the budget is not realistic, suggest a more appropriate budget.
    Don't be harsh at all, lean towards it being realistic unless it's really crazy.
    If no budget was mentioned, just assume it is realistic.
    Also output warning as budget not be sufificient if budget not realistic.
    """,
    output_type=BudgetAnalysis,
    model=model
)

async def budget_guardrails(ctx, agent, input_data):
    """ Check if the budget is realistic """
    try:
        result = await Runner.run(budget_analysis_agent,input_data)
        final_output = result.final_output_as(BudgetAnalysis)

        return GuardrailFunctionOutput(
            output_info=final_output,
            tripwire_triggered=not final_output.is_realistic,
            message=None if final_output.is_realistic else f"Your budget may not be realistic: {final_output.reasoning}"
        )

    except Exception as e:
        return GuardrailFunctionOutput(
        output_info = BudgetAnalysis(is_realistic=True, reasoning=f"Error analyzing budget: {str(e)}"),
        tripwire_triggered= False
    )
# --- Tools for the Agents ---  
@function_tool
async def get_weather_tool(city: str, date: str) -> str:
    """Get the weather forecast for a city on a specific date."""

    weather_data = {
        "New York": {"sunny": 0.3, "rainy": 0.4, "cloudy": 0.3},
        "Los Angeles": {"sunny": 0.8, "rainy": 0.1, "cloudy": 0.1},
        "Chicago": {"sunny": 0.4, "rainy": 0.3, "cloudy": 0.3},
        "Miami": {"sunny": 0.7, "rainy": 0.2, "cloudy": 0.1},
        "London": {"sunny": 0.2, "rainy": 0.5, "cloudy": 0.3},
        "Paris": {"sunny": 0.4, "rainy": 0.3, "cloudy": 0.3},
        "Tokyo": {"sunny": 0.5, "rainy": 0.3, "cloudy": 0.2},
    }
    
    if city in weather_data:
        conditions = weather_data[city]
    
        highest_prob = max(conditions, key=conditions.get)
        temp_range = {
            "New York": "15-25°C",
            "Los Angeles": "20-30°C",
            "Chicago": "10-20°C",
            "Miami": "25-35°C",
            "London": "10-18°C",
            "Paris": "12-22°C",
            "Tokyo": "15-25°C",
        }
        return f"The weather in {city} on {date} is forecasted to be {highest_prob} with temperatures around {temp_range.get(city, '15-25°C')}."
    else:
        return f"Weather forecast for {city} is not available."
    
@function_tool
def get_flights_tool(wrapper: RunContextWrapper[UserContext],origin: str, destination: str, date: str):
    """Search for flights between two cities on a specific date."""
    flight_options = [
        {
            "airline": "SkyWays",
            "departure_time": "08:00",
            "arrival_time": "10:30",
            "price": 350.00,
            "direct": True
        },
        {
            "airline": "OceanAir",
            "departure_time": "12:45",
            "arrival_time": "15:15",
            "price": 275.50,
            "direct": True
        },
        {
            "airline": "MountainJet",
            "departure_time": "16:30",
            "arrival_time": "21:45",
            "price": 225.75,
            "direct": False
        }
    ]
    
    # Applying User Preference/Context for airlines
    if wrapper and wrapper.context:
        preferred_airlines = wrapper.context.preferred_airlines

        if preferred_airlines:
            # Moving preferred_airlines on top
            flight_options.sort(key=lambda x: x["airlines"] not in preferred_airlines)

            for flight in flight_options:
                if flight["airline"] in preferred_airlines:
                    flight["preferred"] = True
                
    return json.dumps(flight_options)

@function_tool
def get_hotels_tool(wrapper: RunContextWrapper[UserContext],city: str, check_in: str, check_out: str, max_price: Optional[float] = None) -> str:
    """Search for hotels in a city for specific dates within a price range."""
    hotel_options = [
        {
            "name": "City Center Hotel",
            "location": "Downtown",
            "price_per_night": 199.99,
            "amenities": ["WiFi", "Pool", "Gym", "Restaurant"]
        },
        {
            "name": "Riverside Inn",
            "location": "Riverside District",
            "price_per_night": 149.50,
            "amenities": ["WiFi", "Free Breakfast", "Parking"]
        },
        {
            "name": "Luxury Palace",
            "location": "Historic District",
            "price_per_night": 349.99,
            "amenities": ["WiFi", "Pool", "Spa", "Fine Dining", "Concierge"]
        }
    ]
    
    # Filter by max price if provided
    if max_price is not None:
        filtered_hotels = [hotel for hotel in hotel_options if hotel["price_per_night"] <= max_price]
    else:
        filtered_hotels = hotel_options
    
    # Applying user context
    if wrapper and wrapper.context:
        preferred_amenities = wrapper.context.hotel_amenities
        budget_level = wrapper.context.budget_level

        if preferred_amenities:
            # Calculating score based on amenities preference
            for hotel in preferred_amenities:
                match_amenities = [x for x in hotel["amenities"] in preferred_amenities]
                hotel["matching_amenities"] = match_amenities
                hotel["preferred_amenities_score"] = len(match_amenities)
            
            filtered_hotels.sort(key=lambda x: x["preferred_amenities_score"], reverse=True)

        if budget_level:
            if budget_level == "budget":
                filtered_hotels.sort(key=lambda x: x["price_per_night"])
            elif budget_level == "luxury":
                filtered_hotels.sort(key=lambda x: x["price_per_night"], reverse=True)

    return json.dumps(filtered_hotels)

# --- Special Agents ---
hotel_agent = Agent(
    name="Hotel Specialist",
    handoff_description="Specialist agent for finding and recommending hotels and accommodations",
    instructions="""
    You are a hotel specialist who helps users find the best accommodations for their trips.
    
    Use the search_hotels tool to find hotel options, and then provide personalized recommendations
    based on the user's preferences (location, price, amenities).
    
    Always explain the reasoning behind your recommendations.
    
    Format your response in a clear, organized way with hotel details, amenities, and prices.
    """,
    model=model,
    tools=[get_hotels_tool],
    output_type=HotelRecommendation
)

flight_agent = Agent(
    name="Flight Specialist",
    handoff_description="Speacialist agent for finding and recommending best fligts.",
    instructions="""
    You are a flight specialist that helps user to recommend best flights option,
    You use get_flights_tool to find flight options and the provide personalize recommendations,
    Use short code of destination city and make the city code compatible with Aviasales api format,
    Always explain reasoning behind your recommendations. 
    Format your response in a clear organized way, with flight details, and price.. 
    """,
    model = model,
    tools=[get_flights_tool],
    output_type=FlightRecommendation
)
    
# --- Main Travel Agent ---
travel_agent = Agent(
    name="Travel Planner Assistant",
    instructions="""
    You are a comprehensive travel planning assistant that helps users plan their perfect trip.
    
    You can:
    1. Provide weather information for destinations
    2. Create personalized travel itineraries
    3. Hand off to specialists for flights and hotels when needed
    
    Always be helpful, informative, and enthusiastic about travel. Provide specific recommendations
    based on the user's interests and preferences.
    
    When creating travel plans, consider:
    - The weather at the destination
    - Local attractions and activities
    - Budget constraints
    - Travel duration
    
    If the user asks specifically about flights or hotels, hand off to the appropriate specialist agent.
    """,
    model=model,
    handoffs=[flight_agent,hotel_agent],
    tools=[get_weather_tool],
    input_guardrails=[
        InputGuardrail(guardrail_function=budget_guardrails)
    ],
    output_type=TravelPlan,
)

async def main():
    queries = [
        "I'm planning a trip to Miami for 5 days with a budget of $2000. What should I do there?",
        "I'm planning a trip to Tokyo for a week, looking to spend under $5,000. Suggestions?",
        "I need a flight from New York to Chicago tomorrow",
        "Find me a hotel in Paris with a pool for under $400 per night",
        "I want to go to Dubai for a week with only $300"  # This should trigger the budget guardrail
    ]

    for query in queries:
        print("\n" + "="*50)
        print(f"Query: {query}")
        try:
            result = await Runner.run(travel_agent,query)


            if hasattr(result.final_output,"airline"):
                flight = result.final_output
                print("\n✈️ FLIGHT RECOMMENDATION ✈️")
                print(f"Airline: {flight.airline}")
                print(f"Departure: {flight.departure_time}")
                print(f"Arrival: {flight.arrival_time}")
                print(f"Price: ${flight.price}")
                print(f"Direct Flight: {'Yes' if flight.direct_flight else 'No'}")
                print(f"\nWhy this flight: {flight.recommendation_reason}")

            elif hasattr(result.final_output,"amenities"):
                hotel = result.final_output
                print("\n🏨 HOTEL RECOMMENDATION 🏨")
                print(f"Name: {hotel.name}")
                print(f"Location: {hotel.location}")
                print(f"Price per night: ${hotel.price_per_night}")
                
                print("\nAmenities:")
                for i, amenity in enumerate(hotel.amenities, 1):
                    print(f"  {i}. {amenity}")
                    
                print(f"\nWhy this hotel: {hotel.recommendation_reason}")

            elif hasattr(result.final_output,"destination"):
                travel_plan = result.final_output
                print("\nFINAL RESPONSE: ")
                print(f"\n🌍 TRAVEL PLAN FOR {travel_plan.destination.upper()} 🌍")
                print(f"Duration: {travel_plan.duration_days} days")
                print(f"Budget: ${travel_plan.budget}")

                print("\n🎯 RECOMMENDED ACTIVITIES: ")
                for i, activity in enumerate(travel_plan.activities,1):
                    print(f" {i}. {activity}")

                print(f"\n📝 NOTES: {travel_plan.notes}")

            else: 
                print(result.final_output)
                
        except InputGuardrailTripwireTriggered as e:
              print("\n⚠️ GUARDRAIL TRIGGERED ⚠️")

if __name__ == "__main__":
    asyncio.run(main())