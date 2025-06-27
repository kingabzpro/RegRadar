"""
RegRadar - AI Regulatory Compliance Assistant

This application monitors and analyzes regulatory updates, providing
compliance guidance for various industries and regions.
"""

import warnings

import gradio as gr

from agents.ui_handler import UIHandler
from config.settings import AVATAR_IMAGES

warnings.filterwarnings("ignore", category=DeprecationWarning)


def create_demo():
    ui_handler = UIHandler()  # New user for each session
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
            ui_handler.streaming_chatbot,
            [msg, chatbot, user_id_state],
            [chatbot, msg, msg, user_id_state],
        )
        click_event = submit.click(
            ui_handler.streaming_chatbot,
            [msg, chatbot, user_id_state],
            [chatbot, msg, msg, user_id_state],
        )
        stop.click(None, cancels=[submit_event, click_event])
        clear.click(
            ui_handler.delayed_clear,
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


def main():
    """Initialize and launch the RegRadar application"""
    demo = create_demo()
    demo.launch()


if __name__ == "__main__":
    main()
