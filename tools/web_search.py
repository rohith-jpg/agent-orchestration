import os
from tavily import TavilyClient
from dotenv import load_dotenv
from tools.registry import registry

load_dotenv()

_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))


@registry.register(
    name="web_search",
    description="Search the web for current information. Returns a list of results with title, url, and snippet.",
    allowed_agents=["research_specialist", "supervisor"],
)
def web_search(query: str, max_results: int = 5) -> list[dict]:
    response = _client.search(query=query, max_results=max_results)
    return [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content"),
        }
        for r in response.get("results", [])
    ]