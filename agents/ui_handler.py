import threading
import time
import uuid

import gradio as gr
from gradio import ChatMessage

from agents.reg_radar import RegRadarAgent
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
            yield from self._handle_general_chat(message, history, user_id_state)
            return

        yield from self._handle_regulatory_chat(
            message, history, user_id_state, user_id, start_time
        )

    def _handle_general_chat(self, message, history, user_id_state):
        """Handle general (non-regulatory) chat flow."""
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

    def _handle_regulatory_chat(
        self, message, history, user_id_state, user_id, start_time
    ):
        """Handle regulatory chat flow."""
        # Show tool detection
        tool_key, tool_name = self.agent.determine_intended_tool(message)

        # Initial processing message with tool info (collapsible)
        status_msg = (
            f"Using **{tool_name}** to analyze your query (estimated 10-20 seconds)..."
        )
        history.append(
            ChatMessage(
                role="assistant",
                content=status_msg,
                metadata={"title": f"🛠️ Tool Selected: {tool_name}"},
            )
        )
        yield history, "", gr.update(interactive=False), user_id_state

        # Extract parameters and process query
        params = self.agent.extract_parameters(message)

        # Clear status and show parameter extraction (collapsible)
        history.pop()
        param_msg = f"- Industry: {params['industry']}\n- Region: {params['region']}\n- Keywords: {params['keywords']}"
        history.append(
            ChatMessage(
                role="assistant",
                content=param_msg,
                metadata={"title": "📍Parameter Extraction"},
            )
        )
        yield history, "", gr.update(interactive=False), user_id_state

        # Show tool execution steps (collapsible)
        tool_status = f"""
**Executing {tool_name}...**
⏳ _This process may take 40-90 seconds depending on the number of webpages being crawled._
"""
        history.append(
            ChatMessage(
                role="assistant",
                content=tool_status,
                metadata={"title": "📢 Tool Execution Status"},
            )
        )
        yield history, "", gr.update(interactive=False), user_id_state

        # Process the regulatory query
        results = self.agent.process_regulatory_query(message, params, user_id=user_id)
        crawl_results = results["crawl_results"]
        memory_results = results["memory_results"]

        # Show collapsible raw results
        if crawl_results["results"]:
            collapsible_results = self._format_crawl_results(crawl_results["results"])
            history.append(
                ChatMessage(
                    role="assistant",
                    content=collapsible_results,
                    metadata={"title": "🌐 Raw Regulatory Data", "status": "done"},
                )
            )
            yield history, "", gr.update(interactive=False), user_id_state

        # Display memory results if available
        if memory_results:
            memory_msg = self._format_memory_results(memory_results)
            history.append(
                ChatMessage(
                    role="assistant",
                    content=memory_msg,
                    metadata={"title": "💾 Past Memories", "status": "done"},
                )
            )
            yield history, "", gr.update(interactive=False), user_id_state

        # Generate final analysis (no metadata, standard message)
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

        # Show completion time appended to the final report (no metadata)
        elapsed = time.time() - start_time
        history[-1] = ChatMessage(
            role="assistant",
            content=streaming_content + f"\n\n✨ Analysis complete ({elapsed:.1f}s).",
        )
        # Re-enable input box at the end
        yield history, "", gr.update(interactive=True), user_id_state

        # Save to memory in the background
        threading.Thread(
            target=self.agent.memory_tools.save_to_memory,
            args=(user_id, message, streaming_content),
            daemon=True,
        ).start()

    def _format_crawl_results(self, results):
        """Format crawl results for display, removing duplicates by URL."""
        seen_urls = set()
        results_display = []
        count = 0
        for result in results:
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
            # Only return the content, let Gradio's metadata title handle the dropdown
            collapsible_results = "\n".join(results_display)
        else:
            collapsible_results = "No unique regulatory updates found."
        return collapsible_results

    def _format_memory_results(self, memory_results):
        """Format memory results for display."""
        top_memories = memory_results[:3]
        memory_details = ""
        for i, mem in enumerate(top_memories, 1):
            memory_text = mem.get("memory", "N/A")
            memory_details += f"\n**{i}. Memory:** {memory_text[:300]}...\n"
        memory_msg = f"Found {len(memory_results)} similar past queries in memory. \nTop 3 shown below:\n{memory_details}"
        return memory_msg

    def delayed_clear(self, user_id_state):
        time.sleep(0.1)  # 100ms delay to allow generator cancellation
        return [], "", gr.update(interactive=True), user_id_state
