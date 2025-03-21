import os 
from dotenv import load_dotenv
from pymongo import MongoClient
from agents import Agent, Runner, WebSearchTool, TContext, function_tool

# Setup API key 
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Setup MongoDB connection
database_url = os.getenv("DATABASE_URL")
mongo_client = MongoClient(database_url)
db = mongo_client.get_database('Query_Results')
collection = db['queryResult']


# Web Search Agent
webSearch_agent = Agent(
    name="Web Search",
    instructions="Use the web search tool to fetch information based on input" 
    "Generate short and precise answers.",
    tools=[WebSearchTool()],
)

# Custom databse storage tool
@function_tool
async def store_in_mongodb(query: str, result: str) -> str:
    try:
        collection.insert_one({"query": query, "result": result})
        return "Data successfully stored in MongoDB."
    except Exception as e:
        return f"Error storing data: {str(e)}"

# MongoDB Storage Agent
mongodb_store_agent = Agent(
    name="MongoDB Storage Agent",
    instructions="Store the fetched data into MongoDB.",
    tools=[store_in_mongodb],
)


async def generate_response(query):
    input_text = query
    
    # Runnign Web Search Agent
    web_result = await Runner.run(webSearch_agent, input_text)

    # Structuring data
    structured_data = {
        "query": input_text,
        "result": web_result.final_output
    }

    # Store the data in MongoDB
    store_result = await Runner.run(
        mongodb_store_agent, 
        [{"role": "user", "content": str(structured_data)}]
    )

    return web_result.final_output

