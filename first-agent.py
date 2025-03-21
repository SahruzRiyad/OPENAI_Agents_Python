from agents import Agent, set_default_openai_key
from agents import Runner, InputGuardrail, GuardrailFunctionOutput
from pydantic import BaseModel
import asyncio
import os 
from  dotenv import load_dotenv

# Setting Up api key 
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
set_default_openai_key(api_key)


class HomeworkOutput(BaseModel):
    is_homework: bool
    reasoning: str


guradrail_agent = Agent(
    name="Guardrail Check",
    instructions="Check if user is asking about homework.",
    output_type=HomeworkOutput,
)


math_tutor_agent = Agent(
    name="Math Tutor",
    handoff_description="Specialist agent for math questions",
    instructions="You provide help with math problems."
    " Explain your reasoning at each step and include examples",
)

history_tutor_agent = Agent(
    name="History Tutor",
    handoff_description="Specialist agent for historical questions",
    instructions="You provide help with history questions."
    " Explain your reasoning at each step and include examples",
)

async def homework_guardrail(ctx, agent, input_data):
    result = await Runner.run(guradrail_agent,input_data,context=ctx.context)
    final_output = result.final_output_as(HomeworkOutput)
    tripwire = not final_output.is_homework

    if tripwire:
        raise ValueError("I can only assist with homework.")

    return GuardrailFunctionOutput(
        output_info = final_output,
        tripwire_triggered= not final_output.is_homework
    )

triage_agent = Agent(
    name="Triage Agent",
    instructions="You determine which agent to use based on the user's homework question",
    handoffs=[history_tutor_agent, math_tutor_agent],
    input_guardrails=[
        InputGuardrail(guardrail_function=homework_guardrail),
    ],
)

async def main(msg):
    try:
        result = await Runner.run(triage_agent, msg)
        print(result.final_output)

    except ValueError as e:
        print(e)

    # msg = "Who is the first"
    # result = await Runner.run(triage_agent, msg)

if __name__ == "__main__":
    # msg = "Who is the first president of United States?"
    msg = input("Enter your query: ")

    asyncio.run(main(msg))