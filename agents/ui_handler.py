import time

import gradio as gr
from gradio import ChatMessage

from agents.reg_radar import RegRadarAgent
from config.settings import AVATAR_IMAGES
from tools.llm import stream_llm


class UIHandler:
    def __init__(self):
        self.agent = RegRadarAgent()

    def streaming_chatbot(self, message, history):
        """Process messages with tool visibility and lock input during response generation"""
        if not message.strip():
            return history, "", gr.update(interactive=True)

        # Add user message
        history.append(ChatMessage(role="user", content=message))

        # Start timer
        start_time = time.time()

        # Disable input box at the start
        yield history, "", gr.update(interactive=False)

        # Detect if this is a regulatory query
        is_regulatory = self.agent.is_regulatory_query(message)

        if not is_regulatory:
            # General chat
            history.append(
                ChatMessage(role="assistant", content="💬 Processing general query...")
            )
            yield history, "", gr.update(interactive=False)

            # Clear processing message and stream response
            history.pop()

            chat_prompt = f"You are a friendly AI assistant. Respond conversationally to: {message}"
            streaming_content = ""
            history.append(ChatMessage(role="assistant", content=""))

            for chunk in stream_llm(chat_prompt):
                streaming_content += chunk
                history[-1] = ChatMessage(role="assistant", content=streaming_content)
                yield history, "", gr.update(interactive=False)

            # Re-enable input box at the end
            yield history, "", gr.update(interactive=True)
            return

        # Show tool detection
        tool_key, tool_name = self.agent.determine_intended_tool(message)

        # Initial processing message with tool info
        status_msg = f"🔍 Using **{tool_name}** to analyze your query (estimated 10-20 seconds)..."
        history.append(ChatMessage(role="assistant", content=status_msg))
        yield history, "", gr.update(interactive=False)

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
"""
        history.append(ChatMessage(role="assistant", content=tool_status))
        yield history, "", gr.update(interactive=False)

        # Process the regulatory query
        results = self.agent.process_regulatory_query(message)
        crawl_results = results["crawl_results"]
        memory_results = results["memory_results"]

        # Update with results count
        history[-1] = ChatMessage(
            role="assistant",
            content=tool_status
            + f"\n\n✅ **Found {crawl_results['total_found']} regulatory updates**",
        )
        yield history, "", gr.update(interactive=False)

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
                if count >= 5:
                    break
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
            yield history, "", gr.update(interactive=False)

        # Display memory results if available
        if memory_results:
            memory_msg = f"""
<details>
<summary><strong>💾 Related Past Queries</strong> - Click to expand</summary>

Found {len(memory_results)} similar past queries in memory.

</details>
"""
            history.append(ChatMessage(role="assistant", content=memory_msg))
            yield history, "", gr.update(interactive=False)

        # Generate final analysis
        history.append(
            ChatMessage(
                role="assistant", content="📝 **Generating Compliance Report...**"
            )
        )
        yield history, "", gr.update(interactive=False)

        # Clear generating message and stream final report
        history.pop()

        streaming_content = ""
        history.append(ChatMessage(role="assistant", content=""))

        for chunk in self.agent.generate_report(params, crawl_results):
            streaming_content += chunk
            history[-1] = ChatMessage(role="assistant", content=streaming_content)
            yield history, "", gr.update(interactive=False)

        # Save to memory
        self.agent.memory_tools.save_to_memory("user", message, streaming_content)

        # Show completion time
        elapsed = time.time() - start_time
        history.append(
            ChatMessage(
                role="assistant", content=f"✨ **Analysis complete** ({elapsed:.1f}s)"
            )
        )
        # Re-enable input box at the end
        yield history, "", gr.update(interactive=True)

    def delayed_clear(self):
        time.sleep(0.1)  # 100ms delay to allow generator cancellation
        return [], "", gr.update(interactive=True)

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
                <h1 style="text-align: center;">🛡️ RegRadar</h1>
                <p><b>AI-powered regulatory compliance assistant that monitors global regulations</b></p>
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
            submit_event = msg.submit(
                self.streaming_chatbot, [msg, chatbot], [chatbot, msg, msg]
            )
            click_event = submit.click(
                self.streaming_chatbot, [msg, chatbot], [chatbot, msg, msg]
            )
            stop.click(None, cancels=[submit_event, click_event])
            clear.click(self.delayed_clear, outputs=[chatbot, msg, msg])

            # Footer
            gr.HTML("""
            <div style="text-align: center; padding: 20px; color: #666; font-size: 0.9rem;">
                <p>RegRadar monitors regulatory updates from SEC, FDA, FTC, EU Commission, and more.</p>
                <p>All analysis is AI-generated. Always verify with official sources.</p>
            </div>
            """)

        return demo
