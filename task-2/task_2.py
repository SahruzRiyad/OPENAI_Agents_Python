from agents import Agent, Runner , WebSearchTool, function_tool
import uuid, httpx , os
from bs4 import BeautifulSoup
from pymongo import MongoClient
from dotenv import load_dotenv

# Connect Mongodb atlas 
def initialize_db():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    mongo_client = MongoClient(database_url)
    db = mongo_client.get_database('Query_Results')
    return db['queryResult']

collection = initialize_db()


sessions = {}

async def browse_web(task_id):

    # Web Browse agent
    web_serach_agent = Agent(
        name="Web Search Agent",
        instructions= "Browse Google for the information.",
        tools=[WebSearchTool()],
    )

    input_text = sessions[task_id]["query"]

    result = await Runner.run(web_serach_agent,input_text)

    sessions[task_id]['agent1_result'] = result.final_output


# Web Scraper Tool
@function_tool
async def web_scraping_tool(url: str)-> str:

    task_id = list(sessions.keys())[-1]  
    sessions[task_id]['scraped_url'] = url

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extracting all paragraph text
    paragraphs = soup.find_all('p')
    texts = [p.get_text() for p in paragraphs]
    text = "\n".join(texts)

    return text


async def find_and_scrape_web(task_id):

    find_urls_and_scrape_agent = Agent(
        name="Find urls and scrape websites agent",
        instructions=f"You find a specific url from the given input, "
                     f"Then scrape the website using given web scraper tool" 
                     f"for more information on {sessions[task_id]['query']}",
        tools=[web_scraping_tool],
    )

    result = await Runner.run(find_urls_and_scrape_agent, sessions[task_id]['agent1_result'])
    sessions[task_id]['agent2_result'] = result.final_output


async def create_and_store(task_id):

    tutorial_agent = Agent(
        name="Tutorial Generation Agent",
        instructions="Generate a tutorial from the given scraped content.",
        tools=[],
    )

    scraped_content = sessions[task_id]['agent2_result']
    tutorial_result = await Runner.run(tutorial_agent, scraped_content)

    tutorial_content = tutorial_result.final_output
    sessions[task_id]['agent3_result'] = tutorial_content

    try:
        scraped_url = sessions[task_id].get('scraped_url', 'N/A')

        collection.insert_one({
            'task_id': str(task_id),
            'query': sessions[task_id]['query'],
            'scraped_url': scraped_url,
            'tutorial': tutorial_content
        })

        print("Data successfully stored in database.")

    except Exception as e:
        print(f"Error occur while inserting db {e}")


#To run all the 3 task above
async def run_task(task_id: str):
  
    try:

        #Calling web browsing agent
        sessions[task_id]["status"] = "web_searching"
        await browse_web(task_id)

        sessions[task_id]["status"] = "web_search_complete"

        print("Agent 1: \n",sessions[task_id]['agent1_result'], '\n',flush=True)

        #Calling web scraping agent
        sessions[task_id]["status"] = "web_scraping"
        await find_and_scrape_web(task_id)
        sessions[task_id]["status"] = "web_scraping_complete"

        print("Agent 2: \n", sessions[task_id]['agent2_result'],'\n',flush=True)

        #Calling tutorial generator agent
        sessions[task_id]["status"] = "tutorial_generating"
        await create_and_store(task_id)
        sessions[task_id]["status"] = "tutorial_generated_and_saved_in_db"

        print("Agent 3: \n", sessions[task_id]['agent3_result'],'\n',flush=True)

        sessions[task_id]["status"] = "Done"

    except Exception as e:
        sessions[task_id]["staus"] = f"Error occurs: {str(e)}"

def create_new_task(request):

    task_id = str(uuid.uuid4())
    
    sessions[task_id] = {
        'query': request,
        'status': 'created'
    }

    return task_id

def get_status(task_id):
    return sessions[task_id]["status"]

