# ===== CHATBOT LOGIC =====
# Sends prompts to Ollama and streams the response.
# Accepts an optional system_prompt to inject knowledge base context.

import ollama


def get_response(prompt: str, model: str = "llama3", system_prompt: str = ""):
    """
    Interact with Ollama and yield response text chunks (streaming).

    Parameters
    ----------
    prompt        : The user's message.
    model         : Ollama model name (e.g. 'llama3', 'mistral').
    system_prompt : Optional knowledge base context injected as a system message.
    """
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
