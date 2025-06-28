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
        """Extract industry, region, keywords, and report_type from the query using LLM (no function calling)."""
        # Expanded lists for industries and regions
        industries = [
            "fintech",
            "healthcare",
            "energy",
            "general",
            "IT",
            "AI",
            "manufacturing",
            "telecommunications",
            "transportation",
            "education",
            "retail",
            "finance",
            "insurance",
            "pharmaceuticals",
            "agriculture",
            "media",
            "entertainment",
            "legal",
            "real estate",
            "construction",
            "logistics",
            "food & beverage",
            "automotive",
            "aerospace",
            "defense",
        ]
        regions = [
            "US",
            "EU",
            "UK",
            "Asia",
            "Global",
            "Africa",
            "Middle East",
            "South America",
            "North America",
            "Australia",
            "Canada",
            "China",
            "India",
            "Japan",
            "Russia",
            "Brazil",
            "Mexico",
            "Germany",
            "France",
            "Italy",
            "Spain",
            "Nordics",
            "Southeast Asia",
        ]
        industries_str = ", ".join(industries)
        regions_str = ", ".join(regions)
        prompt = f"""
        Extract the following information from the user query below and return ONLY a valid JSON object with keys: industry, region, keywords, report_type.
        - industry: The industry mentioned or implied. Choose from: {industries_str} (or specify if different).
        - region: The region or country explicitly mentioned. Choose from: {regions_str} (or specify if different).
        - keywords: The most important regulatory topics or terms, separated by commas. Do NOT include generic words or verbs.
        - report_type: Only set to 'quick' if the user is asking for a highly specific fact, date, number, or detail (e.g., "When did the GDPR take effect?", "What is the fine for X?"). For general regulatory questions (even if phrased as 'what are', 'what is', etc.), or if the user asks for a full report or the question is vague, set to 'full'. Use 'summary' only if the user explicitly asks for a summary.
        
        User query: {message}
        
        Example outputs:
        {{"industry": "AI", "region": "EU", "keywords": "AI Act, data privacy", "report_type": "summary"}}
        {{"industry": "fintech", "region": "US", "keywords": "SEC regulations", "report_type": "quick"}}
        {{"industry": "healthcare", "region": "Global", "keywords": "HIPAA, patient data", "report_type": "full"}}
        """
        response = call_llm(prompt)
        try:
            params = json.loads(response)
        except Exception:
            # fallback: use heuristics for report_type
            msg_lower = message.lower()
            if any(
                word in msg_lower for word in ["summary", "summarize", "short summary"]
            ):
                report_type = "summary"
            elif any(
                word in msg_lower for word in ["report", "full report", "comprehensive"]
            ):
                report_type = "full"
            elif any(
                word in msg_lower
                for word in [
                    "when is",
                    "who is",
                    "how much",
                    "how many",
                    "specific",
                    "exact",
                    "detail",
                    "quick",
                    "brief",
                    "answer",
                    "fact",
                    "date",
                    "number",
                    "tell me more",
                    "give me more",
                    "more details",
                    "more info",
                    "expand on",
                    "elaborate on",
                ]
            ):
                report_type = "quick"
            else:
                report_type = "full"
            params = {
                "industry": "General",
                "region": "US",
                "keywords": "",
                "report_type": report_type,
            }
        # Ensure report_type is always present and valid
        if params.get("report_type") not in ["quick", "summary", "full"]:
            params["report_type"] = "full"
        return params

    def format_parameter_extraction(self, params: dict) -> str:
        """Format the parameter extraction display, including report type."""
        return (
            f"Industry: {params.get('industry', 'N/A')}\n"
            f"Region: {params.get('region', 'N/A')}\n"
            f"Keywords: {params.get('keywords', 'N/A')}\n"
            f"Report Type: {params.get('report_type', 'full').capitalize()}"
        )

    def is_regulatory_query(self, message: str) -> bool:
        """Detect if this is a new regulatory, compliance, or update-related question (not a follow-up or general question).
        Returns True only if the message is a new regulatory/compliance/update question. Returns False for follow-up regulatory or general questions.
        """
        intent_prompt = f"""
        Is the following user message a new regulatory, compliance, or update-related question? Respond 'yes' ONLY if the user is asking a new regulatory, compliance, or update-related question, not a follow-up or general question. If the message is a follow-up to a previous regulatory discussion (e.g., 'Can you expand on that?', 'What about healthcare?'), or a general/non-regulatory question, respond 'no'.
        
        Message: {message}
        Respond with only 'yes' or 'no'.
        """

        intent = call_llm(intent_prompt).strip().lower()
        return intent.startswith("y")

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
            "report_type": params.get("report_type", "full"),
        }

    def generate_report(self, params, crawl_results, memory_results=None):
        """Generate a regulatory report (quick, summary, or full) including memory context if available"""
        report_type = params.get("report_type", "full")
        memory_context = ""
        if memory_results:
            # Format memory results for inclusion in the prompt (limit to 3 for brevity)
            memory_context = "\n\n# 💾 Related Past Queries and Insights\n"
            for i, mem in enumerate(memory_results[:3], 1):
                memory_text = mem.get("memory", "N/A")
                memory_context += f"\n**{i}. Memory:** {memory_text[:300]}...\n"
            memory_context += "\nIncorporate any relevant insights from these past queries into your analysis.\n"

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

            if report_type == "quick":
                summary_prompt = f"""
                Provide a very brief (1-2 sentences) answer with the most important regulatory update for {params["industry"]} in {params["region"]} (keywords: {params["keywords"]}).
                {memory_context}
                Data:
                {json.dumps(by_source, indent=2)}
                """
            elif report_type == "summary":
                summary_prompt = f"""
                Provide a concise summary (1 short paragraph) of the most important regulatory updates for {params["industry"]} in {params["region"]} (keywords: {params["keywords"]}).
                {memory_context}
                Data:
                {json.dumps(by_source, indent=2)}
                """
            else:  # full
                summary_prompt = f"""
                Create a comprehensive regulatory compliance report for {params["industry"]} industry in {params["region"]} region.
                {memory_context}
                Analyze these regulatory updates:
                {json.dumps(by_source, indent=2)}
                
                Include:
                
                ---
                
                ## 🏛️ Executive Summary 
                (2-3 sentences overview)

                ## 🔍 Key Findings
                • Finding 1
                • Finding 2
                • Finding 3

                ## 🛡️ Compliance Requirements
                - List main requirements with priorities

                ## ✅ Action Items
                - Specific actions with suggested timelines

                ## 📚 Resources
                - Links and references
                
                Use emojis, bullet points, and clear formatting. Keep it professional but readable.
                """

        return stream_llm(summary_prompt)
