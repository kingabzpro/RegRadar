from openai import OpenAI

from config.settings import (
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TEMPERATURE,
    KEYWORDS_API_KEY,
    OPENAI_BASE_URL,
)

# Initialize OpenAI client
client = OpenAI(
    base_url=OPENAI_BASE_URL,
    api_key=KEYWORDS_API_KEY,
)


def call_llm(prompt: str, temperature: float = DEFAULT_LLM_TEMPERATURE) -> str:
    """Make a call to the LLM"""
    try:
        response = client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM call error: {e}")
        return "I apologize, but I encountered an error processing your request."


def stream_llm(
    prompt: str,
    temperature: float = DEFAULT_LLM_TEMPERATURE,
    system_prompt: str = "You are an expert AI assistant specializing in regulatory updates. Provide thorough, insightful, and actionable analysis based on the user's request, focusing on compliance, recent changes, and best practices.",
):
    """Stream LLM response with an expert regulatory system prompt"""
    try:
        stream = client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                yield delta
    except Exception as e:
        yield f"Error: {str(e)}"
