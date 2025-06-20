import json
from typing import Dict, Tuple

from tools.llm import call_llm, stream_llm
from tools.memory_tools import MemoryTools
from tools.web_tools import WebTools


class RegRadarAgent:
    def __init__(self):
        self.web_tools = WebTools()
        self.memory_tools = MemoryTools()

    def determine_intended_tool(self, message: str) -> Tuple[str, str]:
        """Determine which tool will be used based on the message"""
        message_lower = message.lower()

        if any(
            word in message_lower
            for word in ["crawl", "scan", "check", "latest", "update", "recent"]
        ):
            return "web_crawler", "Regulatory Web Crawler"
        elif any(
            word in message_lower
            for word in ["remember", "history", "past", "previous"]
        ):
            return "memory", "Memory Search"
        else:
            return "search", "Regulatory Search"

    def extract_parameters(self, message: str) -> Dict:
        """Extract industry, region, and keywords from the query using LLM (no function calling)."""
        prompt = f"""
        Extract the following information from the user query below and return ONLY a valid JSON object with keys: industry, region, keywords.
        - industry: The industry mentioned or implied (e.g., fintech, healthcare, energy, general).
        - region: The region or country explicitly mentioned (e.g., US, EU, UK, Asia, Global).
        - keywords: The most important regulatory topics or terms, separated by commas. Do NOT include generic words or verbs.
        
        User query: {message}
        
        Example output:
        {{"industry": "fintech", "region": "US", "keywords": "SEC regulations"}}
        """
        response = call_llm(prompt)
        try:
            params = json.loads(response)
        except Exception:
            # fallback: return empty/defaults if parsing fails
            params = {"industry": "General", "region": "US", "keywords": ""}
        return params

    def is_regulatory_query(self, message: str) -> bool:
        """Detect if this is a regulatory, compliance, or update-related question"""
        intent_prompt = f"""
        Is the following user message a regulatory, compliance, or update-related question (yes/no)?
        Message: {message}
        Respond with only 'yes' or 'no'.
        """

        intent = call_llm(intent_prompt).strip().lower()
        return not intent.startswith("n")

    def process_regulatory_query(
        self, message: str, params: dict = None, user_id: str = "user"
    ):
        """Process a regulatory query and return results"""
        # Determine the intended tool
        tool_key, tool_name = self.determine_intended_tool(message)

        # Extract parameters only if not provided
        if params is None:
            params = self.extract_parameters(message)

        # Execute tool (crawl sites)
        crawl_results = self.web_tools.crawl_regulatory_sites(
            params["industry"], params["region"], params["keywords"]
        )

        # Check memory for similar queries
        memory_results = self.memory_tools.search_memory(user_id, message)

        return {
            "tool_name": tool_name,
            "params": params,
            "crawl_results": crawl_results,
            "memory_results": memory_results,
        }

    def generate_report(self, params, crawl_results):
        """Generate a comprehensive regulatory report"""
        if not crawl_results["results"]:
            summary_prompt = (
                f"No regulatory updates found for {params['industry']} in {params['region']} "
                f"with keywords: {params['keywords']}. Provide helpful suggestions on where to "
                f"look or what to search for."
            )
        else:
            by_source = {}
            for result in crawl_results["results"][:8]:
                source = result.get("source", "Unknown")
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(result)

            summary_prompt = f"""
            Create a comprehensive regulatory compliance report for {params["industry"]} industry in {params["region"]} region.
            
            Analyze these regulatory updates:
            {json.dumps(by_source, indent=2)}
            
            Include:
            # 📋 Executive Summary
            (2-3 sentences overview)
            
            # 🔍 Key Findings
            • Finding 1
            • Finding 2
            • Finding 3
            
            # ⚠️ Compliance Requirements
            - List main requirements with priorities
            
            # ✅ Action Items
            - Specific actions with suggested timelines
            
            # 📚 Resources
            - Links and references
            
            Use emojis, bullet points, and clear formatting. Keep it professional but readable.
            """

        return stream_llm(summary_prompt)
