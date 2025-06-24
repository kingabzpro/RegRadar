import hashlib
from typing import Dict

from tavily import TavilyClient

from config.settings import REGULATORY_SOURCES, SOURCE_FULL_NAMES, TAVILY_API_KEY
from tools.llm import call_llm

# Initialize Tavily client
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


class WebTools:
    def __init__(self):
        self.cached_searches = {}

    def generate_cache_key(self, industry: str, region: str, keywords: str) -> str:
        """
        Generate a unique cache key based on industry, region, and keywords.
        """
        key = f"{industry}:{region}:{keywords}".lower()
        return hashlib.md5(key.encode()).hexdigest()

    def crawl_regulatory_sites(self, industry: str, region: str, keywords: str) -> Dict:
        """
        Crawl regulatory websites for updates.
        """
        cache_key = self.generate_cache_key(industry, region, keywords)
        if cache_key in self.cached_searches:
            return self.cached_searches[cache_key]

        urls_to_crawl = REGULATORY_SOURCES.get(region, REGULATORY_SOURCES["US"])
        all_results = []
        crawl_instructions = (
            f"Recent {industry} {region} regulatory updates: {keywords}, 30 days"
        )

        # Crawl regulatory sites (limit to 3 sources)
        for source_name, url in list(urls_to_crawl.items())[:3]:
            crawl_results = self._get_crawl_results(
                source_name, url, crawl_instructions
            )
            all_results.extend(crawl_results)

        # General search
        search_results = self._get_search_results(industry, region, keywords)
        all_results.extend(search_results)

        results = {"results": all_results, "total_found": len(all_results)}
        self.cached_searches[cache_key] = results
        return results

    def _get_crawl_results(self, source_name: str, url: str, instructions: str) -> list:
        """
        Crawl a single regulatory source and return formatted results.
        """
        results = []
        try:
            crawl_response = tavily_client.crawl(
                url=url, max_depth=2, limit=5, instructions=instructions
            )
            for result in crawl_response.get("results", []):
                title = result.get("title")
                if not title or title == "No Title...":
                    title = SOURCE_FULL_NAMES.get(source_name, source_name)
                results.append(
                    {
                        "source": source_name,
                        "url": result.get("url", url),
                        "title": title,
                        "content": result.get("raw_content", "")[:1500],
                    }
                )
        except Exception as e:
            print(f"Crawl error for {source_name}: {e}")
        return results

    def _get_search_results(self, industry: str, region: str, keywords: str) -> list:
        """
        Perform a general web search and return formatted results.
        """
        results = []
        try:
            search_results = tavily_client.search(
                query=f"{industry} {region} regulatory updates compliance {keywords} 2024 2025",
                max_results=5,
                include_raw_content=True,
            )
            for result in search_results.get("results", []):
                results.append(
                    {
                        "source": "Web Search",
                        "url": result.get("url", ""),
                        "title": result.get("title", ""),
                        "content": result.get("content", ""),
                    }
                )
        except Exception as e:
            print(f"Search error: {e}")
        return results

    def extract_parameters(self, message: str) -> Dict:
        """
        Extract industry, region, and keywords from the query using LLM (no function calling).
        """
        prompt = (
            """
            Extract the following information from the user query below and return ONLY a valid JSON object with keys: industry, region, keywords.
            - industry: The industry mentioned or implied (e.g., fintech, healthcare, energy, general).
            - region: The region or country explicitly mentioned (e.g., US, EU, UK, Asia, Global).
            - keywords: The most important regulatory topics or terms, separated by commas. Do NOT include generic words or verbs.
            
            User query: {message}
            
            Example output:
            {{"industry": "fintech", "region": "US", "keywords": "SEC regulations"}}
            """
        ).replace("{message}", message)

        import json

        response = call_llm(prompt)
        try:
            params = json.loads(response)
        except Exception:
            params = {"industry": "", "region": "", "keywords": ""}
        return params
