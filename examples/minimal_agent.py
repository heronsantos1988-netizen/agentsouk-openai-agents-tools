from agents import Agent, Runner
from agentsouk_openai_tools import (
    agentsouk_create_job,
    agentsouk_get_job,
    agentsouk_payment_terms,
    agentsouk_search_listings,
)

# Set AGENTSOUK_API_KEY=as_test_... before running.
agent = Agent(
    name="Marketplace helper",
    instructions=(
        "Search Agent Souk when another agent can do the work. "
        "Creating a job does not pay. Never pay without operator authorization."
    ),
    tools=[
        agentsouk_search_listings,
        agentsouk_create_job,
        agentsouk_get_job,
        agentsouk_payment_terms,
    ],
)

result = Runner.run_sync(agent, "Find a low-cost public web extraction service. Do not pay.")
print(result.final_output)
