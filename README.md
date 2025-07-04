---
title: RegRadar
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.35.0
app_file: app.py
pinned: true
license: apache-2.0
short_description: RegRadar watches the worlds regulators so you dont have to.
---

# RegRadar

RegRadar is an AI-powered regulatory compliance assistant that monitors global regulations so you don't have to. It helps compliance professionals, legal teams, and businesses stay up-to-date with the latest regulatory changes across industries and regions.

[![RegRadar (100 Agents Hackathon)](./images/image.png)](https://www.youtube.com/watch?v=v0lZMx_Yt2I)

## 🚀 Features
- **Improved Regulatory Query Detection**: Now distinguishes between new regulatory/compliance/update questions and follow-up or general questions. Only new regulatory questions trigger compliance workflows; follow-ups and general queries are handled as general chat.
- **Automatic Query Type Detection**: Understands if your message is a regulatory compliance query or a general question, and selects the right tools.
- **Information Extraction**: Extracts key details (industry, region, keywords, and report type) from your queries for precise analysis.
- **Smart Report Type Detection**: Automatically determines if you want a quick answer, a summary, or a full compliance report based on your query. The detected report type is shown in the parameter extraction step and controls the style and length of the AI's response.
- **Regulatory Web Crawler**: Crawls official regulatory websites (e.g., SEC, FDA, FTC, ESMA, BIS) for recent updates and compliance changes (last 30 days).
- **Regulatory Search Engine**: Searches across multiple sources for industry-specific compliance information and aggregates results.
- **Memory System**: Remembers past queries and responses, personalizing results for each session/user.
- **AI Analysis Engine**: Summarizes findings and generates actionable compliance recommendations and executive summaries.

## 🚦 How It Works
When you submit a query, RegRadar:
1. Detects if your message is a **new** regulatory/compliance question (not a follow-up or general question).
2. If yes, extracts industry, region, keywords, and report type.
3. If no, processes your message as a general or follow-up query.
4. Runs the appropriate regulatory search/crawl and memory lookup if regulatory.
5. Shows the extracted parameters, including the report type, in the UI for transparency.
5. Generates a response matching your intent:
   - **Quick**: Direct, brief answer to specific questions.
   - **Summary**: Short summary for summary requests.
   - **Full**: Comprehensive report (default for vague or broad queries).

## 🏁 Getting Started

Follow these steps to set up and run RegRadar locally:

1. **Create a virtual environment (recommended):**
   
   On Windows:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
   On macOS/Linux:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app:**
   ```bash
   python app.py
   ```

The app will start and you can access it via the provided local URL in your browser.

## 🔑 Setting Up API Keys

Before running RegRadar, you must set up API keys for the required services as environment variables.

**On Windows (PowerShell):**
```powershell
$env:TAVILY_API_KEY="your-tavily-api-key"
$env:KEYWORDS_API_KEY="your-keywordsai-api-key"
$env:MEM0_API_KEY="your-mem0-api-key"
```

**On macOS/Linux (bash):**
```bash
export TAVILY_API_KEY="your-tavily-api-key"
export KEYWORDS_API_KEY="your-keywordsai-api-key"
export MEM0_API_KEY="your-mem0-api-key"
```

You can add these lines to your `.env` file or your shell profile for convenience.

## 🤖 Adding Your OpenAI API Key to KeywordsAI

RegRadar uses the KeywordsAI platform, which requires an OpenAI API key for LLM access. Here's how to add your OpenAI API key:

1. **Get your OpenAI API key:**
   - Go to [OpenAI Platform](https://platform.openai.com/).
   - Log in and navigate to your profile > **View API Keys**.
   - Click **Create new secret key** and copy the generated key.

2. **Add your OpenAI API key to KeywordsAI:**
   - Log in to your KeywordsAI account.
   - Go to the [KeywordsAI Providers page](https://platform.keywordsai.co/platform/api/providers).
   - Find the OpenAI provider and paste your OpenAI API key into the provided field.
   - Save your changes.

> For more details, see the [KeywordsAI Providers documentation](https://platform.keywordsai.co/platform/api/providers).

## 🛠️ Tools Used
- **Gradio**: For the interactive web UI.
- **OpenAI/KeywordsAI LLM**: For natural language understanding, information extraction, summarization, and LLM tracking.
- **Tavily**: For regulatory web crawling and search.
- **Mem0**: For session-based memory and personalization.