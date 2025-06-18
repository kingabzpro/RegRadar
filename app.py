import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import gradio as gr
from mem0 import MemoryClient
from openai import OpenAI
from tavily import TavilyClient

# Initialize services
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# Initialize OpenAI client with Keywords AI endpoint
client = OpenAI(
    base_url="https://api.keywordsai.co/api/",
    api_key=os.getenv("KEYWORDS_API_KEY"),
)

# Regulatory websites mapping
REGULATORY_SOURCES = {
    "US": {
        "SEC": "https://www.sec.gov/news/pressreleases",
        "FDA": "https://www.fda.gov/news-events/fda-newsroom/press-announcements",
        "FTC": "https://www.ftc.gov/news-events/news/press-releases",
        "Federal Register": "https://www.federalregister.gov/documents/current",
    },
    "EU": {
        "European Commission": "https://ec.europa.eu/commission/presscorner/home/en",
        "ESMA": "https://www.esma.europa.eu/press-news/esma-news",
        "EBA": "https://www.eba.europa.eu/news-press/news",
    },
    "Global": {
        "BIS": "https://www.bis.org/press/index.htm",
        "IOSCO": "https://www.iosco.org/news/",
    },
}


class RegRadarChat:
    def __init__(self):
        self.conversation_state = {}
        self.cached_searches = {}

    def generate_cache_key(self, industry: str, region: str, keywords: str) -> str:
        """Generate a unique cache key for search parameters"""
        content = f"{industry.lower()}_{region.lower()}_{keywords.lower()}"
        return hashlib.md5(content.encode()).hexdigest()

    def call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """Make a call to the LLM"""
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM call error: {e}")
            return "I apologize, but I encountered an error processing your request."

    def check_cache(self, cache_key: str) -> Optional[Dict]:
        """Check if we have cached results for this search"""
        try:
            # Search in Mem0 for cached results
            memories = mem0_client.search(
                query=f"cache_key:{cache_key}", user_id="cache_system", limit=1
            )

            if memories and len(memories) > 0:
                # Parse the cached data
                memory_content = memories[0].get("content", "")
                if "cached_data:" in memory_content:
                    cached_json = memory_content.split("cached_data:")[1]
                    return json.loads(cached_json)
        except Exception as e:
            print(f"Cache check error: {e}")

        return None

    def save_to_cache(self, cache_key: str, data: Dict):
        """Save crawled data to cache"""
        try:
            cache_data = {
                "cache_key": cache_key,
                "timestamp": datetime.now().isoformat(),
                "data": data,
            }

            mem0_client.add(
                messages=[
                    {
                        "role": "system",
                        "content": f"cache_key:{cache_key} cached_data:{json.dumps(cache_data)}",
                    }
                ],
                user_id="cache_system",
                metadata={"type": "cache", "cache_key": cache_key},
            )
        except Exception as e:
            print(f"Cache save error: {e}")

    def crawl_regulatory_sites(self, industry: str, region: str, keywords: str) -> Dict:
        """Crawl regulatory websites for updates"""
        urls_to_crawl = REGULATORY_SOURCES.get(region, REGULATORY_SOURCES["US"])
        all_results = []

        crawl_instructions = f"""
        Find pages about:
        - Recent regulatory updates for {industry}
        - New compliance requirements
        - Keywords: {keywords}
        - Focus on recent content (last 30 days)
        """

        for source_name, url in list(urls_to_crawl.items())[
            :3
        ]:  # Limit to 3 sources for speed
            try:
                crawl_response = tavily_client.crawl(
                    url=url, max_depth=2, limit=5, instructions=crawl_instructions
                )

                for result in crawl_response.get("results", []):
                    all_results.append(
                        {
                            "source": source_name,
                            "url": result.get("url", ""),
                            "title": result.get("title", ""),
                            "content": result.get("raw_content", "")[:1500],
                        }
                    )

            except Exception as e:
                print(f"Crawl error for {source_name}: {e}")

        # Also do a general search
        try:
            search_results = tavily_client.search(
                query=f"{industry} {region} regulatory updates compliance {keywords} 2024",
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

        return {"results": all_results}

    def summarize_results(self, results: List[Dict]) -> str:
        """Summarize crawled results into a readable format"""
        if not results:
            return "No regulatory updates found for your criteria."

        # Group by source
        by_source = {}
        for result in results[:8]:  # Limit to top 8 results
            source = result.get("source", "Unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(result)

        # Create summary prompt
        prompt = f"""
        Analyze these regulatory updates and provide:
        1. A brief overview of the key findings
        2. The most important compliance changes
        3. Action items for compliance teams
        
        Updates:
        {json.dumps(by_source, indent=2)}
        
        Format your response in a conversational way, using bullet points for clarity.
        """

        return self.call_llm(prompt)

    def process_message(
        self, message: str, history: List[Dict]
    ) -> Tuple[List[Dict], str]:
        """Process user message and generate response"""
        # Initialize conversation state if needed
        if len(history) == 0:
            self.conversation_state = {
                "stage": "greeting",
                "industry": None,
                "region": None,
                "keywords": None,
            }

        # Handle different conversation stages
        if self.conversation_state["stage"] == "greeting":
            response = """👋 Hello! I'm RegRadar, your AI regulatory compliance assistant.

I can help you find the latest regulatory updates for your industry. To get started, please tell me:

**What industry are you in?** (e.g., Finance, Healthcare, Technology, Energy, etc.)"""
            self.conversation_state["stage"] = "awaiting_industry"

        elif self.conversation_state["stage"] == "awaiting_industry":
            self.conversation_state["industry"] = message
            response = f"""Great! I'll help you find regulatory updates for the **{message}** industry.

**Which region's regulations are you interested in?**
• US - United States regulations
• EU - European Union regulations  
• Global - International regulations"""
            self.conversation_state["stage"] = "awaiting_region"

        elif self.conversation_state["stage"] == "awaiting_region":
            if message.upper() in ["US", "EU", "GLOBAL"]:
                self.conversation_state["region"] = message.upper()
                response = """Perfect! One last question:

**Are there any specific keywords or topics you're particularly interested in?**
(e.g., "data privacy", "AI", "ESG", "cybersecurity", or just type "none" for general updates)"""
                self.conversation_state["stage"] = "awaiting_keywords"
            else:
                response = "Please choose from: US, EU, or Global"

        elif self.conversation_state["stage"] == "awaiting_keywords":
            keywords = "" if message.lower() == "none" else message
            self.conversation_state["keywords"] = keywords

            # Generate cache key
            cache_key = self.generate_cache_key(
                self.conversation_state["industry"],
                self.conversation_state["region"],
                keywords,
            )

            # Check cache first
            cached_data = self.check_cache(cache_key)

            if cached_data:
                response = f"""✅ **Found recent scan results!** (cached from {cached_data["timestamp"][:10]})

I found existing results for {self.conversation_state["industry"]} regulations in {self.conversation_state["region"]}. Here's what I found:

{self.summarize_results(cached_data["data"]["results"])}

Would you like me to:
• **Refresh** - Get the latest updates (new crawl)
• **Details** - See specific regulatory documents
• **New Search** - Start a different search"""
            else:
                response = f"""🔍 **Scanning regulatory sources...**

Looking for {self.conversation_state["industry"]} regulations in {self.conversation_state["region"]}...
Keywords: {keywords if keywords else "General updates"}

*This may take a moment as I crawl regulatory websites...*"""

                # Perform the crawl
                crawl_data = self.crawl_regulatory_sites(
                    self.conversation_state["industry"],
                    self.conversation_state["region"],
                    keywords,
                )

                # Save to cache
                self.save_to_cache(cache_key, crawl_data)

                # Generate summary
                summary = self.summarize_results(crawl_data["results"])

                response = f"""✅ **Scan Complete!**

Here's what I found for {self.conversation_state["industry"]} regulations in {self.conversation_state["region"]}:

{summary}

**What would you like to do next?**
• Type **"details"** to see specific documents
• Type **"new"** to start a new search
• Ask me any questions about these regulations"""

            self.conversation_state["stage"] = "results_shown"

        elif self.conversation_state["stage"] == "results_shown":
            if "new" in message.lower():
                self.conversation_state = {"stage": "greeting"}
                response = self.process_message("", [])[1]
            elif "refresh" in message.lower():
                self.conversation_state["stage"] = "awaiting_keywords"
                response = self.process_message(
                    self.conversation_state.get("keywords", "none"), history
                )[1]
            elif "details" in message.lower():
                response = """Please specify which regulatory area you'd like more details about, or paste a URL from the results above for me to analyze in depth."""
            else:
                # Answer questions about the regulations
                prompt = f"""
                Based on the regulatory information for {self.conversation_state["industry"]} in {self.conversation_state["region"]},
                answer this question: {message}
                
                Be helpful and specific. If you don't have enough information, say so.
                """
                response = self.call_llm(prompt)

        else:
            response = (
                "I'm not sure how to help with that. Type 'new' to start a new search."
            )

        # Update history with new message format
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})

        return history, ""

    def stream_llm(self, prompt: str, temperature: float = 0.3):
        """Stream LLM response using OpenAI's streaming API."""
        try:
            stream = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True,
            )
            partial = ""
            for chunk in stream:
                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta:
                    partial += delta
                    yield partial
        except Exception as e:
            yield f"I apologize, but I encountered an error processing your request: {e}"


# Initialize the chat instance
chat_instance = RegRadarChat()

# Streaming generator for regulatory Q&A
import types


def streaming_chatbot(message, history):
    # Add the user message to history
    history = history + [{"role": "user", "content": message}]
    # Get the prompt for the LLM (simulate what process_message does for 'results_shown')
    prompt = f"""
    Based on the regulatory information for {chat_instance.conversation_state.get("industry")} in {chat_instance.conversation_state.get("region")},
    answer this question: {message}
    
    Be helpful and specific. If you don't have enough information, say so.
    """
    # Start with an empty assistant message
    history = history + [{"role": "assistant", "content": ""}]
    for chunk in chat_instance.stream_llm(prompt):
        history[-1]["content"] = chunk
        yield history, ""


# Create Gradio interface
with gr.Blocks(title="RegRadar Chat", theme=gr.themes.Soft()) as demo:
    gr.HTML("""
    <center>
        <h1 style="text-align: center;">🛰️RegRadar</h1>
        <p>Your intelligent assistant for real-time regulatory monitoring</p>
    </center>
    """)

    chatbot = gr.Chatbot(
        height=400,
        type="messages",
        avatar_images=(None, "https://media.roboflow.com/spaces/gemini-icon.png"),
        show_copy_button=True,
    )

    example_queries = [
        "Show me the latest SEC regulations for fintech.",
        "What are the new data privacy rules in the EU?",
        "Any updates on ESG compliance for energy companies?",
        "Scan for healthcare regulations in the US.",
        "What are the global trends in AI regulation?",
    ]

    with gr.Row(equal_height=True):
        msg = gr.Textbox(
            placeholder="Ask about regulatory updates, compliance, or any related topic...",
            show_label=False,
            scale=19,
            autofocus=True,
        )
        submit = gr.Button("Send", variant="primary", scale=1, min_width=60)

    gr.Examples(examples=example_queries, inputs=msg, label="Example Queries")

    with gr.Row():
        clear = gr.Button("🔄 Clear Chat", size="sm")

    # Event handlers
    def user_submit(message, history):
        if not message.strip():
            # Do not add empty messages, just return the current history and clear the input
            return history, "", gr.update(interactive=True), gr.update(interactive=True)
        # Use streaming only for regulatory Q&A (results_shown)
        if chat_instance.conversation_state.get("stage") == "results_shown":
            # Return a generator for streaming
            return types.GeneratorType, streaming_chatbot(message, history)
        # Otherwise, use the normal synchronous handler
        new_history, _ = chat_instance.process_message(message, history)
        return new_history, "", gr.update(interactive=True), gr.update(interactive=True)

    def enable_input():
        return gr.update(interactive=True), gr.update(interactive=True)

    submit_event = msg.submit(
        user_submit, [msg, chatbot], [chatbot, msg, msg, submit]
    ).then(enable_input, [], [msg, submit])
    click_event = submit.click(
        user_submit, [msg, chatbot], [chatbot, msg, msg, submit]
    ).then(enable_input, [], [msg, submit])

    clear.click(lambda: ([], ""), outputs=[chatbot, msg])

    # Initial greeting
    demo.load(
        lambda: chat_instance.process_message("", [])[0:2], outputs=[chatbot, msg]
    )

    gr.Markdown("""
    ---
    **Features:**
    • 🔍 Intelligent web crawling of regulatory sites
    • 💾 Cached results to avoid duplicate crawling
    • 🤖 AI-powered analysis and summaries
    • 💬 Natural conversation interface
    """)

# Set up event loop properly for Gradio
if __name__ == "__main__":
    demo.launch()
