from agents import Agent , ModelSettings, function_tool, Runner
from pydantic import BaseModel
import asyncio
import os
from dotenv import load_dotenv

# Setup api key 
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny."


agent = Agent(
    name= "Haiku agent",
    instructions= "Always respond in Haiku form",
    model= "o3-mini",
    tools=[get_weather]
)

# Calender Extractor
class CalenderEvent(BaseModel):
    name: str 
    date: str 
    participations: list[str]

calender_agent = Agent(
    name="Calendar extractor",
    instructions="Extract calendar events from text",
    output_type=CalenderEvent,
)

# Agent Cloning

class DateFetch(BaseModel):
    date: str

date_extractor_agent = calender_agent.clone(
    name= "Date Extractor",
    instructions = "Fetch the date",
    output_type=DateFetch,
)

async def main():
    result = await Runner.run(agent,"Weather of Dhaka")

    print(result.final_output)

    input_text = "We have a team meeting on March 25th with Alice, Bob, and Charlie."
    result = await Runner.run(calender_agent,input_text)
    calendar_event = result.final_output_as(CalenderEvent)

    print(calendar_event)
    print("Event Name:", calendar_event.name)
    print("Event Date:", calendar_event.date)
    print("Participants:", calendar_event.participations)


    # date extractor
    result = await Runner.run(date_extractor_agent,input_text)
    date = result.final_output_as(DateFetch)
    print(date.date)
      
if __name__ == "__main__":
    asyncio.run(main())