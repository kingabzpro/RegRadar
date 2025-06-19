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


def stream_llm(prompt: str, temperature: float = DEFAULT_LLM_TEMPERATURE):
    """Stream LLM response"""
    try:
        stream = client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
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


def call_llm_with_function(
    user_message: str,
    function_schema: dict,
    temperature: float = DEFAULT_LLM_TEMPERATURE,
) -> dict:
    """Call the LLM with function calling and return extracted arguments as a dict."""
    try:
        response = client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            messages=[{"role": "user", "content": user_message}],
            functions=[function_schema],
            function_call="auto",
            temperature=temperature,
        )
        function_call = response.choices[0].message.function_call
        if function_call and hasattr(function_call, "arguments"):
            import json

            return json.loads(function_call.arguments)
        else:
            return {}
    except Exception as e:
        print(f"LLM function call error: {e}")
        return {}
