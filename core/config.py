import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

LUXEMBOURG_API_BASE = "https://data.public.lu/api/1"
MCP_SERVER = "https://mcp.data.public.lu/mcp"
GROQ_MODEL = "llama-3.1-8b-instant"
MAX_DATASETS_PER_RUN = 10

TOPICS = ["housing", "employment", "transport", "environment", "economy", "health"]
