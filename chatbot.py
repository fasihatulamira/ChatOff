import os
import ollama
from dotenv import load_dotenv

# Ensure dotenv is loaded
load_dotenv()


def get_response(prompt: str, model: str = None, system_prompt: str = ""):
    """
    Interact with Ollama and yield response text chunks (streaming).

    Parameters
    ----------
    prompt        : The user's message.
    model         : Ollama model name (e.g. 'llama3', 'mistral'). If None, resolves from OLLAMA_MODEL env var.
    system_prompt : Optional knowledge base context injected as a system message.
    """
    if model is None:
        model = os.getenv("OLLAMA_MODEL", "llama3")

    try:
        messages = []

        # Inject knowledge base as a system message if available
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        stream = ollama.chat(
            model=model,
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]

    except Exception as e:
        raise Exception(f"Chatbot logic error: {str(e)}")
