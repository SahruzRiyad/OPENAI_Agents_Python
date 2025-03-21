from agents import Agent, Runner 

agent = Agent(name="Assistant", instructions="Your are a helpful asssitant")

result = Runner.run_sync(agent,"write a haiku about recurssion programming.")

print(result.final_output)