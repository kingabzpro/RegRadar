import hashlib
from typing import Dict
from tavily import TavilyClient
from config.settings import TAVILY_API_KEY, REGULATORY_SOURCES

# Initialize Tavily client
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

class WebTools:
    def __init__(self):
        self.cached_searches = {}

    def generate_cache_key(self, industry: str, region: str, keywords: str) -> str:
        """Generate a unique cache key"""
        key = f"{industry}:{region}:{keywords}".lower()
        return hashlib.md5(key.encode()).hexdigest()

    def crawl_regulatory_sites(self, industry: str, region: str, keywords: str) -> Dict:
        """Crawl regulatory websites for updates"""
        # Check cache first
        cache_key = self.generate_cache_key(industry, region, keywords)
        if cache_key in self.cached_searches:
            return self.cached_searches[cache_key]

        urls_to_crawl = REGULATORY_SOURCES.get(region, REGULATORY_SOURCES["US"])
        all_results = []

        crawl_instructions = f"""
        Find pages about:
        - Recent regulatory updates for {industry}
        - New compliance requirements
        - Keywords: {keywords}
        - Focus on recent content (last 30 days)
        """

        # Crawl regulatory sites
        for source_name, url in list(urls_to_crawl.items())[:3]:
            try:
                crawl_response = tavily_client.crawl(
                    url=url, max_depth=2, limit=5, instructions=crawl_instructions
                )
                for result in crawl_response.get("results", []):
                    all_results.append(
                        {
                            "source": source_name,
                            "url": url,
                            "title": result.get("title", ""),
                            "content": result.get("raw_content", "")[:1500],
                        }
                    )
            except Exception as e:
                print(f"Crawl error for {source_name}: {e}")

        # General search
        try:
            search_results = tavily_client.search(
                query=f"{industry} {region} regulatory updates compliance {keywords} 2024 2025",
                max_results=5,
                include_raw_content=True,
            )
            for result in search_results.get("results", []):
                all_results.append(
                    {
                        "source": "Web Search",
                        "url": result.get("url", ""),
                        "title": result.get("title", ""),
                        "content": result.get("content", ""),
                    }
                )
        except Exception as e:
            print(f"Search error: {e}")

        results = {"results": all_results, "total_found": len(all_results)}
        self.cached_searches[cache_key] = results
        return results

