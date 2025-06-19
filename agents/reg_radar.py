import json
from typing import Dict, Tuple

from tools.llm import call_llm, call_llm_with_function, stream_llm
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
        """Extract industry, region, and keywords from the query using LLM function calling"""
        function_schema = {
            "name": "extract_parameters",
            "description": (
                "Extract industry, region, and keywords from a user query.\n"
                "- 'industry': If not explicitly mentioned, infer the most relevant industry from the context (e.g., if the query is about SEC regulations, infer 'fintech' or 'finance').\n"
                "- 'region': The country or region explicitly mentioned (e.g., US, EU, UK, Asia, Global).\n"
                "- 'keywords': Only the most important regulatory topics or terms (e.g., 'data privacy', 'GDPR', 'ESG compliance', 'SEC regulations'), not generic words or verbs.\n"
                "Examples:\n"
                "- 'Show me the latest SEC regulations for fintech' => industry: 'fintech', region: 'US', keywords: 'SEC regulations'\n"
                "- 'What are the new data privacy rules in the EU?' => industry: 'General', region: 'EU', keywords: 'data privacy'\n"
                "- 'Scan for healthcare regulations in the US' => industry: 'healthcare', region: 'US', keywords: 'healthcare regulations'\n"
                "- 'Any updates on ESG compliance for energy companies?' => industry: 'energy', region: 'US', keywords: 'ESG compliance'\n"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "The industry mentioned or implied in the query (e.g., fintech, healthcare, energy, general).",
                    },
                    "region": {
                        "type": "string",
                        "description": "The region or country explicitly mentioned in the query (e.g., US, EU, UK, Asia).",
                    },
                    "keywords": {
                        "type": "string",
                        "description": "A concise list of the most important regulatory topics or terms from the query, separated by commas. Do NOT return the full user question, generic words, or verbs.",
                    },
                },
                "required": ["industry", "region", "keywords"],
            },
        }
        params = call_llm_with_function(message, function_schema)
        # Fallback: context-aware extraction if LLM fails
        if not params or not all(
            k in params for k in ("industry", "region", "keywords")
        ):
            import re

            # Infer industry from context
            industry = "General"
            industry_map = {
                "fintech": ["fintech", "finance", "sec", "bank", "investment"],
                "healthcare": ["healthcare", "medical", "pharma", "hospital"],
                "energy": ["energy", "oil", "gas", "renewable", "power"],
                "technology": ["technology", "tech", "ai", "software", "it", "cyber"],
                "retail": ["retail", "ecommerce", "shopping", "store"],
                "general": [],
            }
            for ind, keywords in industry_map.items():
                if any(word in message.lower() for word in keywords):
                    industry = ind
                    break
            # Extract region
            region_match = re.search(
                r"\b(EU|US|UK|Asia|Europe|America|Canada|Australia|India|China|Japan|Global)\b",
                message,
                re.IGNORECASE,
            )
            region = region_match.group(1).upper() if region_match else "US"
            # Extract keywords: regulatory terms and meaningful noun phrases only
            regulatory_terms = [
                "regulation",
                "regulations",
                "compliance",
                "GDPR",
                "data privacy",
                "SEC",
                "ESG",
                "law",
                "rules",
                "requirements",
            ]
            found_terms = [
                term for term in regulatory_terms if term.lower() in message.lower()
            ]
            # Multi-word capitalized noun phrases (e.g., 'data privacy', 'SEC regulations')
            noun_phrases = re.findall(r"([A-Z][a-z]+(?: [a-z]+)+)", message)
            # Remove question words and generic words
            question_words = {
                "what",
                "which",
                "who",
                "whom",
                "whose",
                "when",
                "where",
                "why",
                "how",
            }
            generic_words = {
                "rules",
                "regulation",
                "regulations",
                "requirement",
                "requirements",
                "law",
                "laws",
            }
            filtered_phrases = [
                phrase
                for phrase in noun_phrases
                if phrase.split()[0].lower() not in question_words
                and phrase.lower() not in generic_words
            ]
            # Combine and deduplicate
            keywords_set = set(found_terms + filtered_phrases)
            # Remove single generic words
            keywords_set = {
                kw
                for kw in keywords_set
                if kw.lower() not in question_words and kw.lower() not in generic_words
            }
            keywords = ", ".join(keywords_set)
            if not keywords and found_terms:
                keywords = found_terms[0]
            params = {"industry": industry, "region": region, "keywords": keywords}
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

    def process_regulatory_query(self, message: str):
        """Process a regulatory query and return results"""
        # Determine the intended tool
        tool_key, tool_name = self.determine_intended_tool(message)

        # Extract parameters
        params = self.extract_parameters(message)

        # Execute tool (crawl sites)
        crawl_results = self.web_tools.crawl_regulatory_sites(
            params["industry"], params["region"], params["keywords"]
        )

        # Check memory for similar queries
        memory_results = self.memory_tools.search_memory("user", message)

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
