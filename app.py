import hashlib
import json
import os
import time
from typing import Dict, List, Tuple

import gradio as gr
from gradio import ChatMessage
from mem0 import MemoryClient
from openai import OpenAI
from tavily import TavilyClient

# Initialize services
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
client = OpenAI(
    base_url="https://api.keywordsai.co/api/",
    api_key=os.getenv("KEYWORDS_API_KEY"),
)
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

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

# Avatar configuration
AVATAR_IMAGES = (
    None,
    "https://media.roboflow.com/spaces/gemini-icon.png",
)


class RegRadarChat:
    def __init__(self):
        self.cached_searches = {}

    def generate_cache_key(self, industry: str, region: str, keywords: str) -> str:
        """Generate a unique cache key"""
        key = f"{industry}:{region}:{keywords}".lower()
        return hashlib.md5(key.encode()).hexdigest()

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

    def stream_llm(self, prompt: str, temperature: float = 0.3):
        """Stream LLM response"""
        try:
            stream = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta:
                    yield delta
        except Exception as e:
            yield f"Error: {str(e)}"

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

    def save_to_memory(self, user_id: str, query: str, response: str):
        """Save interaction to memory"""
        try:
            messages = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": response},
            ]
            mem0_client.add(
                messages=messages,
                user_id=user_id,
                metadata={"type": "regulatory_query"},
            )
        except Exception as e:
            print(f"Memory save error: {e}")

    def search_memory(self, user_id: str, query: str) -> List[Dict]:
        """Search for similar past queries"""
        try:
            memories = mem0_client.search(query=query, user_id=user_id, limit=3)
            return memories
        except:
            return []


# Initialize chat instance
chat_instance = RegRadarChat()


def determine_intended_tool(message: str) -> Tuple[str, str]:
    """Determine which tool will be used based on the message"""
    message_lower = message.lower()

    if any(
        word in message_lower
        for word in ["crawl", "scan", "check", "latest", "update", "recent"]
    ):
        return "web_crawler", "Regulatory Web Crawler"
    elif any(
        word in message_lower for word in ["remember", "history", "past", "previous"]
    ):
        return "memory", "Memory Search"
    else:
        return "search", "Regulatory Search"


def streaming_chatbot(message, history):
    """Process messages with tool visibility"""
    if not message.strip():
        return history, ""

    # Add user message
    history.append(ChatMessage(role="user", content=message))

    # Start timer
    start_time = time.time()

    # Detect if this is a regulatory query
    intent_prompt = f"""
    Is the following user message a regulatory, compliance, or update-related question (yes/no)?
    Message: {message}
    Respond with only 'yes' or 'no'.
    """

    intent = chat_instance.call_llm(intent_prompt).strip().lower()

    if intent.startswith("n"):
        # General chat
        history.append(
            ChatMessage(role="assistant", content="💬 Processing general query...")
        )
        yield history, ""

        # Clear processing message and stream response
        history.pop()

        chat_prompt = (
            f"You are a friendly AI assistant. Respond conversationally to: {message}"
        )
        streaming_content = ""
        history.append(ChatMessage(role="assistant", content=""))

        for chunk in chat_instance.stream_llm(chat_prompt):
            streaming_content += chunk
            history[-1] = ChatMessage(role="assistant", content=streaming_content)
            yield history, ""

        return

    # Show tool detection
    tool_key, tool_name = determine_intended_tool(message)

    # Initial processing message with tool info
    status_msg = (
        f"🔍 Using **{tool_name}** to analyze your query (estimated 10-20 seconds)..."
    )
    history.append(ChatMessage(role="assistant", content=status_msg))
    yield history, ""

    # Extract parameters
    extract_prompt = f"""
    Extract industry, region, and keywords from this query:
    "{message}"
    
    Return as JSON with keys: industry, region, keywords
    If not specified, use General/US/main topic
    """

    extraction = chat_instance.call_llm(extract_prompt)
    try:
        params = json.loads(extraction)
    except:
        params = {"industry": "General", "region": "US", "keywords": message}

    # Clear status and show parameter extraction
    history.pop()

    # Show tool execution steps
    tool_status = f"""
🛠️ **Tool Execution Status**

📍 **Parameters Extracted:**
- Industry: {params["industry"]}
- Region: {params["region"]}
- Keywords: {params["keywords"]}

🔄 **Executing {tool_name}...**
"""
    history.append(ChatMessage(role="assistant", content=tool_status))
    yield history, ""

    # Execute tool (crawl sites)
    crawl_results = chat_instance.crawl_regulatory_sites(
        params["industry"], params["region"], params["keywords"]
    )

    # Update with results count
    history[-1] = ChatMessage(
        role="assistant",
        content=tool_status
        + f"\n\n✅ **Found {crawl_results['total_found']} regulatory updates**",
    )
    yield history, ""

    # Show collapsible raw results
    if crawl_results["results"]:
        # Format results for display
        results_display = []
        for i, result in enumerate(crawl_results["results"][:5], 1):
            results_display.append(f"""
**{i}. {result["source"]}**
- Title: {result["title"][:100]}...
- URL: {result["url"]}
""")

        collapsible_results = f"""
<details>
<summary><strong>📋 Raw Regulatory Data</strong> - Click to expand</summary>

{"".join(results_display)}

</details>
"""
        history.append(ChatMessage(role="assistant", content=collapsible_results))
        yield history, ""

    # Check memory for similar queries
    memory_results = chat_instance.search_memory("user", message)
    if memory_results:
        memory_msg = """
<details>
<summary><strong>💾 Related Past Queries</strong> - Click to expand</summary>

Found {len(memory_results)} similar past queries in memory.

</details>
"""
        history.append(ChatMessage(role="assistant", content=memory_msg))
        yield history, ""

    # Generate final analysis
    history.append(
        ChatMessage(role="assistant", content="📝 **Generating Compliance Report...**")
    )
    yield history, ""

    # Create analysis prompt
    if not crawl_results["results"]:
        summary_prompt = f"No regulatory updates found for {params['industry']} in {params['region']} with keywords: {params['keywords']}. Provide helpful suggestions on where to look or what to search for."
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

    # Clear generating message and stream final report
    history.pop()

    streaming_content = ""
    history.append(ChatMessage(role="assistant", content=""))

    for chunk in chat_instance.stream_llm(summary_prompt):
        streaming_content += chunk
        history[-1] = ChatMessage(role="assistant", content=streaming_content)
        yield history, ""

    # Save to memory
    chat_instance.save_to_memory("user", message, streaming_content)

    # Show completion time
    elapsed = time.time() - start_time
    history.append(
        ChatMessage(
            role="assistant", content=f"✨ **Analysis complete** ({elapsed:.1f}s)"
        )
    )
    yield history, ""


# Create Gradio interface
with gr.Blocks(
    title="RegRadar - AI Regulatory Compliance Assistant",
    theme=gr.themes.Soft(),
    css="""
    .tool-status { 
        background-color: #f0f4f8; 
        padding: 10px; 
        border-radius: 5px; 
        margin: 10px 0;
    }
    """,
) as demo:
    # Header
    gr.HTML("""
    <center>
        <h1 style="text-align: center;">🛡️ RegRadar</h1>
        <p><b>AI-powered regulatory compliance assistant that monitors global regulations</b></p>
    </center>
    """)

    # Main chat interface
    chatbot = gr.Chatbot(
        height=500,
        type="messages",
        avatar_images=AVATAR_IMAGES,
        show_copy_button=True,
        bubble_full_width=False,
    )

    with gr.Row(equal_height=True):
        msg = gr.Textbox(
            placeholder="Ask about regulatory updates, compliance requirements, or any industry regulations...",
            show_label=False,
            scale=18,
            autofocus=True,
        )
        submit = gr.Button("Send", variant="primary", scale=1, min_width=60)
        clear = gr.Button("Clear", scale=1, min_width=60)

    # Example queries
    example_queries = [
        "Show me the latest SEC regulations for fintech",
        "What are the new data privacy rules in the EU?",
        "Any updates on ESG compliance for energy companies?",
        "Scan for healthcare regulations in the US",
        "What are the global trends in AI regulation?",
    ]

    gr.Examples(examples=example_queries, inputs=msg, label="Example Queries")

    # Tool information panel
    with gr.Accordion("🛠️ Available Tools", open=False):
        gr.Markdown("""
        ### RegRadar uses these intelligent tools:
        
        **🔍 Regulatory Web Crawler**
        - Crawls official regulatory websites (SEC, FDA, FTC, etc.)
        - Searches for recent updates and compliance changes
        - Focuses on last 30 days of content
        
        **🌐 Regulatory Search Engine**
        - Searches across multiple sources for regulatory updates
        - Finds industry-specific compliance information
        - Aggregates results from various regulatory bodies
        
        **💾 Memory System**
        - Remembers past queries and responses
        - Learns from your compliance interests
        - Provides context from previous interactions
        
        **🤖 AI Analysis Engine**
        - Analyzes and summarizes regulatory findings
        - Generates actionable compliance recommendations
        - Creates executive summaries and action items
        """)

    # Event handlers
    submit_event = msg.submit(streaming_chatbot, [msg, chatbot], [chatbot, msg])
    click_event = submit.click(streaming_chatbot, [msg, chatbot], [chatbot, msg])
    clear.click(lambda: ([], ""), outputs=[chatbot, msg])

    # Footer
    gr.HTML("""
    <div style="text-align: center; padding: 20px; color: #666; font-size: 0.9rem;">
        <p>RegRadar monitors regulatory updates from SEC, FDA, FTC, EU Commission, and more.</p>
        <p>All analysis is AI-generated. Always verify with official sources.</p>
    </div>
    """)

if __name__ == "__main__":
    demo.launch()
