import os
import gradio as gr
from datetime import datetime
from typing import Dict, List, Any
from openai import OpenAI
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
from mem0 import MemoryClient
import json

# Initialize services
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Initialize Mem0 with API key
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# Initialize OpenAI client with Keywords AI endpoint
client = OpenAI(
    base_url="https://api.keywordsai.co/api/",
    api_key=os.getenv("KEYWORDS_AI_API_KEY"),
)

# Regulatory websites mapping
REGULATORY_SOURCES = {
    "US": {
        "SEC": "https://www.sec.gov/news/pressreleases",
        "FDA": "https://www.fda.gov/news-events/fda-newsroom/press-announcements",
        "FTC": "https://www.ftc.gov/news-events/news/press-releases",
        "CFTC": "https://www.cftc.gov/PressRoom/PressReleases",
        "Federal Register": "https://www.federalregister.gov/documents/current",
    },
    "EU": {
        "European Commission": "https://ec.europa.eu/commission/presscorner/home/en",
        "ESMA": "https://www.esma.europa.eu/press-news/esma-news",
        "EBA": "https://www.eba.europa.eu/news-press/news",
        "ECB": "https://www.ecb.europa.eu/press/pr/html/index.en.html",
    },
    "Global": {
        "BIS": "https://www.bis.org/press/index.htm",
        "IOSCO": "https://www.iosco.org/news/",
        "FSB": "https://www.fsb.org/press/",
    },
}


# Define the state for our workflow
class RegRadarState(dict):
    """State management for regulatory monitoring workflow"""

    industry: str
    region: str
    keywords: str
    crawl_results: List[Dict]
    search_results: List[Dict]
    summaries: List[Dict]
    action_items: List[Dict]
    user_id: str


# Helper function to make LLM calls
def call_llm(prompt: str, temperature: float = 0) -> str:
    """Make a call to the LLM and return the response content"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM call error: {e}")
        return ""


# Define agent functions
def crawl_regulatory_sites(state: RegRadarState) -> RegRadarState:
    """Crawl regulatory websites for updates using Tavily's crawl feature"""
    region = state.get("region", "US")
    industry = state.get("industry", "")
    keywords = state.get("keywords", "")

    # Get relevant regulatory URLs based on region
    urls_to_crawl = REGULATORY_SOURCES.get(region, REGULATORY_SOURCES["US"])
    all_crawl_results = []

    # Construct crawl instructions
    crawl_instructions = f"""
    Find pages about:
    - Recent regulatory updates, changes, or announcements
    - New compliance requirements or guidelines
    - Industry: {industry}
    - Keywords: {keywords}
    - Focus on content from the last 30 days
    - Exclude navigation pages and general information
    """

    for source_name, url in urls_to_crawl.items():
        try:
            print(f"Crawling {source_name}...")

            # Execute crawl with focused instructions
            crawl_response = tavily_client.crawl(
                url=url,
                max_depth=2,  # Don't go too deep
                limit=10,  # Limit results per source
                instructions=crawl_instructions,
            )

            # Process crawl results
            for result in crawl_response.get("results", []):
                all_crawl_results.append(
                    {
                        "source": source_name,
                        "url": result.get("url", ""),
                        "title": result.get("title", ""),
                        "content": result.get("raw_content", "")[
                            :2000
                        ],  # Limit content length
                        "crawled_at": datetime.now().isoformat(),
                    }
                )

        except Exception as e:
            print(f"Crawl error for {source_name}: {e}")

    state["crawl_results"] = all_crawl_results
    return state


def search_additional_sources(state: RegRadarState) -> RegRadarState:
    """Supplement crawl results with targeted searches"""
    industry = state.get("industry", "")
    region = state.get("region", "")
    keywords = state.get("keywords", "")

    # Construct search query
    search_query = (
        f"{industry} {region} regulatory changes compliance updates 2024 {keywords}"
    )

    try:
        # Perform additional search for recent news
        search_results = tavily_client.search(
            query=search_query, max_results=5, include_raw_content=True
        )

        state["search_results"] = search_results.get("results", [])
    except Exception as e:
        state["search_results"] = []
        print(f"Search error: {e}")

    return state


def analyze_and_summarize(state: RegRadarState) -> RegRadarState:
    """Analyze crawl and search results to create summaries"""
    crawl_results = state.get("crawl_results", [])
    search_results = state.get("search_results", [])

    # Combine all results
    all_results = []

    # Add crawl results
    for result in crawl_results:
        all_results.append(
            {
                "type": "crawl",
                "source": result.get("source", ""),
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
            }
        )

    # Add search results
    for result in search_results:
        all_results.append(
            {
                "type": "search",
                "source": "Web Search",
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
            }
        )

    summaries = []

    for result in all_results[:10]:  # Limit to top 10 results
        prompt = f"""
        Analyze this regulatory update and provide:
        1. A concise summary (2-3 sentences)
        2. Key compliance implications
        3. Affected entities/sectors
        4. Effective date or timeline
        
        Source: {result.get("source")}
        Title: {result.get("title")}
        Content: {result.get("content", "")[:1500]}
        URL: {result.get("url", "")}
        """

        response_content = call_llm(prompt)

        if response_content:
            summaries.append(
                {
                    "source": result.get("source", ""),
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "summary": response_content,
                    "date": datetime.now().isoformat(),
                    "type": result.get("type", ""),
                }
            )

    state["summaries"] = summaries
    return state


def generate_action_items(state: RegRadarState) -> RegRadarState:
    """Generate actionable compliance tasks based on findings"""
    summaries = state["summaries"]
    industry = state.get("industry", "")

    if not summaries:
        state["action_items"] = []
        return state

    prompt = f"""
    Based on these regulatory updates for the {industry} industry, generate specific action items for compliance teams.
    
    Updates found:
    {json.dumps(summaries, indent=2)}
    
    For each significant update, provide:
    1. Priority level (🔴 High / 🟡 Medium / 🟢 Low)
    2. Specific action required
    3. Timeline/deadline
    4. Responsible party/department
    5. Resources needed
    
    Format as a structured, actionable list. Group by priority.
    """

    response_content = call_llm(prompt)

    if response_content:
        state["action_items"] = [
            {"content": response_content, "generated_at": datetime.now().isoformat()}
        ]
    else:
        state["action_items"] = []

    return state


def store_in_memory(state: RegRadarState) -> RegRadarState:
    """Store important updates in Mem0 for future reference"""
    user_id = state.get("user_id", "default_user")

    # Store summaries in memory
    for summary in state["summaries"]:
        try:
            mem0_client.add(
                messages=[
                    {
                        "role": "system",
                        "content": f"Regulatory update from {summary['source']}: {summary['title']} - {summary['summary']}",
                    }
                ],
                user_id=user_id,
                metadata={
                    "type": "regulatory_update",
                    "source": summary["source"],
                    "date": summary["date"],
                    "url": summary["url"],
                },
            )
        except Exception as e:
            print(f"Memory storage error: {e}")

    return state


# Build the workflow graph
def create_workflow():
    workflow = StateGraph(RegRadarState)

    # Add nodes
    workflow.add_node("crawl", crawl_regulatory_sites)
    workflow.add_node("search", search_additional_sources)
    workflow.add_node("analyze", analyze_and_summarize)
    workflow.add_node("generate_actions", generate_action_items)
    workflow.add_node("store_memory", store_in_memory)

    # Define flow
    workflow.set_entry_point("crawl")
    workflow.add_edge("crawl", "search")
    workflow.add_edge("search", "analyze")
    workflow.add_edge("analyze", "generate_actions")
    workflow.add_edge("generate_actions", "store_memory")
    workflow.add_edge("store_memory", END)

    return workflow.compile()


# Initialize workflow
app_workflow = create_workflow()


# Gradio interface functions
def scan_regulations(industry, region, keywords, deep_scan):
    """Main function to scan for regulatory updates"""

    # Execute workflow
    initial_state = RegRadarState(
        industry=industry,
        region=region,
        keywords=keywords,
        crawl_results=[],
        search_results=[],
        summaries=[],
        action_items=[],
        user_id="compliance_team",
    )

    result = app_workflow.invoke(initial_state)

    # Format output
    output = f"### 📋 Regulatory Update Report\n"
    output += f"**Industry:** {industry} | **Region:** {region}\n"
    output += f"**Scan Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

    # Show crawl statistics
    crawl_count = len(result.get("crawl_results", []))
    search_count = len(result.get("search_results", []))
    output += f"📊 **Sources Analyzed:** {crawl_count} regulatory pages crawled, {search_count} additional sources searched\n\n"

    if result["summaries"]:
        output += "#### 🔍 Recent Regulatory Updates:\n\n"

        # Group by source
        by_source = {}
        for summary in result["summaries"]:
            source = summary["source"]
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(summary)

        for source, items in by_source.items():
            output += f"**📌 {source}**\n\n"
            for idx, summary in enumerate(items, 1):
                output += f"**{idx}. {summary['title']}**\n"
                output += f"{summary['summary']}\n"
                output += f"[🔗 Source Link]({summary['url']})\n\n"
    else:
        output += "No recent regulatory updates found for your criteria.\n\n"

    if result["action_items"]:
        output += "#### ✅ Recommended Action Items:\n\n"
        output += result["action_items"][0]["content"]

    return output


def get_memory_insights(user_id="compliance_team", query=""):
    """Retrieve historical regulatory updates from memory"""
    try:
        search_query = query if query else "regulatory updates"
        memories = mem0_client.search(query=search_query, user_id=user_id, limit=20)

        output = "### 📚 Historical Regulatory Updates\n\n"

        if memories:
            for idx, memory in enumerate(memories, 1):
                output += f"**{idx}.** {memory.get('content', '')}\n"
                if memory.get("metadata"):
                    output += (
                        f"   - Source: {memory['metadata'].get('source', 'N/A')}\n"
                    )
                    output += f"   - Date: {memory['metadata'].get('date', 'N/A')}\n\n"
        else:
            output += "No historical updates found matching your query.\n"

        return output
    except Exception as e:
        return f"Error retrieving memories: {e}"


def analyze_custom_document(document_text):
    """Analyze a custom regulatory document"""
    if not document_text:
        return "Please provide document text to analyze."

    prompt = f"""
    Analyze this regulatory document and provide:
    1. Executive summary (3-4 sentences)
    2. Key compliance requirements
    3. Affected parties
    4. Implementation timeline
    5. Potential challenges
    6. Recommended actions
    
    Document:
    {document_text[:3000]}  # Limit to prevent token overflow
    """

    response_content = call_llm(prompt)

    if response_content:
        return f"### 📄 Document Analysis\n\n{response_content}"
    else:
        return "Error analyzing document. Please try again."


# Create Gradio interface
with gr.Blocks(
    title="RegRadar - Regulatory Compliance Copilot", theme=gr.themes.Soft()
) as demo:
    gr.Markdown("""
    # 🚨 RegRadar - Autonomous Regulatory-Change Copilot
    
    **AI-powered regulatory monitoring with intelligent web crawling**
    """)

    with gr.Tab("🔍 Scan Regulations"):
        with gr.Row():
            with gr.Column(scale=1):
                industry_input = gr.Dropdown(
                    label="Industry/Sector",
                    choices=[
                        "Finance",
                        "Healthcare",
                        "Technology",
                        "Energy",
                        "Manufacturing",
                        "Retail",
                        "Other",
                    ],
                    value="Finance",
                )
                region_input = gr.Dropdown(
                    label="Region", choices=["US", "EU", "Global"], value="US"
                )

            with gr.Column(scale=2):
                keywords_input = gr.Textbox(
                    label="Keywords (optional)",
                    placeholder="e.g., AI, crypto, data privacy, ESG, cybersecurity",
                    lines=2,
                )
                deep_scan = gr.Checkbox(
                    label="Deep Scan (crawl regulatory websites)", value=True
                )

        scan_button = gr.Button(
            "🚀 Start Regulatory Scan", variant="primary", size="lg"
        )

        output_display = gr.Markdown()

        scan_button.click(
            fn=scan_regulations,
            inputs=[industry_input, region_input, keywords_input, deep_scan],
            outputs=output_display,
        )

    with gr.Tab("📄 Analyze Document"):
        document_input = gr.Textbox(
            label="Paste regulatory document text",
            placeholder="Paste the full text of a regulatory document, announcement, or compliance guideline...",
            lines=10,
        )
        analyze_button = gr.Button("🔍 Analyze Document", variant="primary")
        document_output = gr.Markdown()

        analyze_button.click(
            fn=analyze_custom_document, inputs=document_input, outputs=document_output
        )

    with gr.Tab("📚 Memory & History"):
        search_memory = gr.Textbox(
            label="Search historical updates",
            placeholder="e.g., GDPR, SEC rules, FDA guidelines",
        )
        history_button = gr.Button("📖 Search Historical Updates")
        history_display = gr.Markdown()

        history_button.click(
            fn=get_memory_insights,
            inputs=[gr.State("compliance_team"), search_memory],
            outputs=history_display,
        )

    with gr.Tab("ℹ️ About"):
        gr.Markdown("""
        ### About RegRadar
        
        RegRadar uses **advanced web crawling** to monitor regulatory changes:
        
        #### 🕸️ Intelligent Crawling
        - **Crawls official regulatory websites** (SEC, FDA, EU Commission, etc.)
        - **Follows links up to 2 levels deep** to find relevant updates
        - **Filters content** based on your industry and keywords
        
        #### 🤖 AI-Powered Analysis
        - **Powered by GPT-4o-mini** via Keywords AI
        - **Summarizes complex regulations** into clear insights
        - **Identifies compliance implications** specific to your industry
        - **Generates prioritized action items** with deadlines
        
        #### 🧠 Persistent Memory
        - **Remembers all findings** for future reference
        - **Searchable history** of regulatory changes
        - **Tracks compliance trends** over time
        
        #### 📄 Document Analysis
        - **Analyze any regulatory document** you upload
        - **Extract key requirements** and timelines
        - **Get actionable recommendations**
        
        **Technologies:**
        - 🕷️ Tavily Crawl API for intelligent web traversal
        - 🤖 OpenAI GPT-4o-mini via Keywords AI
        - 🧠 Mem0 for persistent memory
        - 🔄 LangGraph for orchestration
        """)

# Launch the app
if __name__ == "__main__":
    demo.launch()
