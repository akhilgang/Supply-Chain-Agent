# tools/search.py (unified version)

import os
import json
from typing import List, Dict, Any, Optional
from semantic_kernel.functions import kernel_function
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential


class SearchTools:
    def __init__(self):
        self.project_endpoint = os.getenv("PROJECT_ENDPOINT")
        self.agent_id = os.getenv("AGENT_ID")
        self.connection_id = os.getenv("BING_CONNECTION_ID")
        self.cred = DefaultAzureCredential()

    @kernel_function(
        name="web_search",
        description="General-purpose web search via Azure AI Agent with Bing grounding"
    )
    def web_search(self, query: str, max_results: int = 5, filter_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Run a web search using Bing grounding via Azure AI Agent.
        Args:
            query: the raw user query (e.g., 'luxury hotels in Dubai under $300/night')
            max_results: max number of results to return
            filter_keywords: optional list of keywords to enforce in results
        Returns:
            List of dicts with {title, url, snippet}
        """
        if not all([self.project_endpoint, self.agent_id, self.connection_id]):
            return [{
                "title": "Missing configuration",
                "url": "https://bing.com",
                "snippet": "Missing PROJECT_ENDPOINT, AGENT_ID, or BING_CONNECTION_ID"
            }]

        try:
            client = AgentsClient(endpoint=self.project_endpoint, credential=self.cred)
            thread = client.threads.create()

            # Create a message instructing the agent to return ONLY a JSON array
            client.messages.create(
                thread_id=thread.id,
                role="user",
                content=(
                    f"Use Bing web search to find results for: {query}\n\n"
                    f"Return ONLY a JSON array (no prose, no markdown) of up to {max_results} "
                    f"results. Each element must have exactly these fields: "
                    f'"title", "url", and "snippet".\n\n'
                    f'Example format:\n'
                    f'[{{"title": "Example", "url": "https://example.com", '
                    f'"snippet": "A short description."}}]'
                )
            )

            # Run the agent to process the message using Bing grounding
            client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self.agent_id
            )

            messages = list(client.messages.list(thread_id=thread.id))
            assistant_msgs = [m for m in messages if m.role == "assistant"]
            content_blocks = assistant_msgs[-1].content if assistant_msgs else []

            raw_json = None
            # Extract the text value from the first text content block
            if content_blocks:
                first_block = content_blocks[0]
                block_type = getattr(first_block, "type", None)
                if block_type == "text":
                    text_obj = getattr(first_block, "text", None)
                    if text_obj is not None:
                        raw_json = getattr(text_obj, "value", None)

            client.threads.delete(thread_id=thread.id)

            if not raw_json:
                return [{
                    "title": "No results",
                    "url": "",
                    "snippet": "No JSON returned by Bing grounding"
                }]

            print("\n🧪 RAW Bing Assistant Response (first 1000 chars):\n", raw_json[:1000])
            print(f"\n📊 Total response length: {len(raw_json)} chars")
            raw_json = raw_json.strip()

            if raw_json.startswith("```"):
                lines = raw_json.split('\n')
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_json = '\n'.join(lines).strip()

            if not raw_json.startswith('['):
                start_idx = raw_json.find('[')
                end_idx = raw_json.rfind(']')
                if start_idx != -1 and end_idx != -1:
                    raw_json = raw_json[start_idx:end_idx+1]
                else:
                    raise ValueError(f"No JSON array found in response. Got: {raw_json[:200]}")

            results = json.loads(raw_json)
            if not isinstance(results, list):
                results = [results]

            # Normalize
            normalized = [{
                "title": r.get("title", "Unknown"),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", "")
            } for r in results]

            # Optional post-filter
            if filter_keywords:
                filtered = [
                    r for r in normalized
                    if any(kw.lower() in (r["title"] + r["snippet"]).lower() for kw in filter_keywords)
                ]
                return filtered[:max_results] or normalized[:max_results]

            return normalized[:max_results]

        except Exception as e:
            import traceback
            print(f"\n❌ Search tool error: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return [{
                "title": "Search error",
                "url": "",
                "snippet": f"Failed to retrieve search results: {e}"
            }]
