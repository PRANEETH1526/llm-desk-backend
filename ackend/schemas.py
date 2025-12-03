from pydantic import BaseModel
from typing import List, Optional

class AgentConfig(BaseModel):
    name: str
    api_key: str
    model: str

class KeyTestRequest(BaseModel):
    api_key: str
    model: str = "openai/gpt-3.5-turbo"

class CouncilRequest(BaseModel):
    content: str
    council: List[AgentConfig]
    chairman: AgentConfig
    task: str
