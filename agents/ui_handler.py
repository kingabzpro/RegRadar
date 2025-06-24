import threading
import time
import uuid

import gradio as gr
from gradio import ChatMessage

from agents.reg_radar import RegRadarAgent
from config.settings import AVATAR_IMAGES
from tools.llm import stream_llm


class UIHandler:
    def __init__(self):
        self.agent = RegRadarAgent()

    def streaming_chatbot(self, message, history, user_id_state):
        """Process messages with tool visibility and lock input during response generation"""
        # Initialize user_id if not set
        if not user_id_state:
            user_id_state = f"user-{uuid.uuid4().hex[:4]}"
        user_id = user_id_state

        if not message.strip():
            return history, "", gr.update(interactive=True), user_id_state

        # Add user message
        history.append(ChatMessage(role="user", content=message))

        # Start timer
        start_time = time.time()

        # Disable input box at the start
        yield history, "", gr.update(interactive=False), user_id_state

        # Detect if this is a regulatory query
        is_regulatory = self.agent.is_regulatory_query(message)

        if not is_regulatory:
            # General chat
            history.append(
                ChatMessage(role="assistant", content="💬 Processing general query...")
            )
            yield history, "", gr.update(interactive=False), user_id_state

            # Clear processing message and stream response
            history.pop()
            streaming_content = ""
            history.append(ChatMessage(role="assistant", content=""))

            for chunk in stream_llm(message):
                streaming_content += chunk
                history[-1] = ChatMessage(role="assistant", content=streaming_content)
                yield history, "", gr.update(interactive=False), user_id_state

            # Re-enable input box at the end
            yield history, "", gr.update(interactive=True), user_id_state
            return

        # Show tool detection
        tool_key, tool_name = self.agent.determine_intended_tool(message)

        # Initial processing message with tool info
        status_msg = f"🔍 Using **{tool_name}** to analyze your query (estimated 10-20 seconds)..."
        history.append(ChatMessage(role="assistant", content=status_msg))
        yield history, "", gr.update(interactive=False), user_id_state

        # Extract parameters and process query
        params = self.agent.extract_parameters(message)

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

⏳ _This process may take 30-60 seconds depending on the number of webpages being crawled._
"""
        history.append(ChatMessage(role="assistant", content=tool_status))
        yield history, "", gr.update(interactive=False), user_id_state

        # Process the regulatory query
        results = self.agent.process_regulatory_query(message, params, user_id=user_id)
        crawl_results = results["crawl_results"]
        memory_results = results["memory_results"]

        # Update with results count
        history[-1] = ChatMessage(
            role="assistant",
            content=tool_status
            + f"\n\n✅ **Found {crawl_results['total_found']} regulatory updates**",
        )
        yield history, "", gr.update(interactive=False), user_id_state

        # Show collapsible raw results
        if crawl_results["results"]:
            # Format results for display, remove duplicates by URL
            seen_urls = set()
            results_display = []
            count = 0
            for result in crawl_results["results"]:
                url = result["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                title = result["title"][:100] if result["title"] else "No Title"
                count += 1
                results_display.append(f"""
**{count}. {result["source"]}**
- Title: {title}...
- URL: {url}
""")
            if results_display:
                collapsible_results = f"""
<details>
<summary><strong>📋 Raw Regulatory Data</strong> - Click to expand</summary>

{"".join(results_display)}

</details>
"""
            else:
                collapsible_results = "<details><summary><strong>📋 Raw Regulatory Data</strong> - Click to expand</summary>\nNo unique regulatory updates found.\n</details>"
            history.append(ChatMessage(role="assistant", content=collapsible_results))
            yield history, "", gr.update(interactive=False), user_id_state

        # Display memory results if available
        if memory_results:
            top_memories = memory_results[:3]
            memory_details = ""
            for i, mem in enumerate(top_memories, 1):
                memory_text = mem.get("memory", "N/A")
                memory_details += f"\n**{i}. Memory:** {memory_text[:300]}...\n"
            memory_msg = f"""
<details>
<summary><strong>💾 Related Past Queries</strong> - Click to expand</summary>

Found {len(memory_results)} similar past queries in memory. Top 3 shown below:
{memory_details}
</details>
"""
            history.append(ChatMessage(role="assistant", content=memory_msg))
            yield history, "", gr.update(interactive=False), user_id_state

        # Generate final analysis
        history.append(
            ChatMessage(
                role="assistant", content="📝 **Generating Compliance Report...**"
            )
        )
        yield history, "", gr.update(interactive=False), user_id_state

        # Clear generating message and stream final report
        history.pop()

        streaming_content = ""
        history.append(ChatMessage(role="assistant", content=""))

        for chunk in self.agent.generate_report(params, crawl_results, memory_results):
            streaming_content += chunk
            history[-1] = ChatMessage(role="assistant", content=streaming_content)
            yield history, "", gr.update(interactive=False), user_id_state

        # Show completion time (before saving to memory)
        elapsed = time.time() - start_time
        history.append(
            ChatMessage(
                role="assistant", content=f"✨ **Analysis complete** ({elapsed:.1f}s)"
            )
        )
        # Re-enable input box at the end
        yield history, "", gr.update(interactive=True), user_id_state

        # Save to memory in the background
        threading.Thread(
            target=self.agent.memory_tools.save_to_memory,
            args=(user_id, message, streaming_content),
            daemon=True,
        ).start()

    def delayed_clear(self, user_id_state):
        time.sleep(0.1)  # 100ms delay to allow generator cancellation
        return [], "", gr.update(interactive=True), user_id_state

    def create_ui(self):
        """Create Gradio interface"""
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
                <h1>🛡️ RegRadar</h1>
                AI-powered regulatory compliance assistant that monitors global regulations
            </center>
            """)

            # Main chat interface
            chatbot = gr.Chatbot(
                height=400,
                type="messages",
                avatar_images=AVATAR_IMAGES,
                show_copy_button=True,
            )

            with gr.Row(equal_height=True):
                msg = gr.Textbox(
                    placeholder="Ask about regulatory updates, compliance requirements, or any industry regulations...",
                    show_label=False,
                    scale=18,
                    autofocus=True,
                )
                submit = gr.Button("Send", variant="primary", scale=1, min_width=60)
                stop = gr.Button("Stop", variant="stop", scale=1, min_width=60)
                clear = gr.Button("Clear", scale=1, min_width=60)

            # Add user_id_state for session
            user_id_state = gr.State()

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
                
                **🧠 Query Type Detection**
                - Automatically detects if your message is a regulatory compliance query or a general question
                - Selects the appropriate tools and response style based on your intent
                
                **📩 Information Extraction**
                - Extracts key details (industry, region, keywords) from your command
                - Ensures accurate and relevant regulatory analysis
                
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
                - Each session creates a new user for personalization
                
                **🤖 AI Analysis Engine**
                - Analyzes and summarizes regulatory findings
                - Generates actionable compliance recommendations
                - Creates executive summaries and action items
                """)

            # Event handlers
            submit_event = msg.submit(
                self.streaming_chatbot,
                [msg, chatbot, user_id_state],
                [chatbot, msg, msg, user_id_state],
            )
            click_event = submit.click(
                self.streaming_chatbot,
                [msg, chatbot, user_id_state],
                [chatbot, msg, msg, user_id_state],
            )
            stop.click(None, cancels=[submit_event, click_event])
            clear.click(
                self.delayed_clear,
                inputs=[user_id_state],
                outputs=[chatbot, msg, msg, user_id_state],
            )

            # Footer
            gr.HTML("""
            <div style="text-align: center; padding: 20px; color: #666; font-size: 0.9rem;">
                <p>RegRadar monitors regulatory updates from the SEC, EU Commission, and other leading global authorities.</p>
                <p>All analyses are AI-generated. Please verify findings with official regulatory sources.</p>
            </div>
            """)

        return demo
