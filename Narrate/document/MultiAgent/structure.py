from pydantic import BaseModel
from typing import Optional

# Define Pydantic models for request validation
class Agent(BaseModel):
    agentId: str
    recommendation: str
    numberOfNodes: Optional[int] = None  # Optional field

class SystemRequest(BaseModel):
    infrastructureDescription: str
    infrastructureCategory: str
    networkAgent: Agent
    energyAgent: Agent
    cyberSecurityAgent: Agent

class Agent:
    def __init__(self, agent_id: str, recommendation: str, number_of_nodes: Optional[int] = None):
        self.agent_id = agent_id
        self.recommendation = recommendation
        self.number_of_nodes = number_of_nodes

    def __repr__(self):
        return f"Agent(agent_id={self.agent_id}, recommendation={self.recommendation}, number_of_nodes={self.number_of_nodes})"

    @classmethod
    def from_dict(cls, data: dict):
        """Creates an Agent instance from a dictionary."""
        return cls(
            agent_id=data["agentId"],
            recommendation=data["recommendation"],
            number_of_nodes=data.get("numberOfNodes")  # Optional field
        )