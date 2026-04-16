#logic (Ollama, response)
import ollama

def get_response(prompt, model="llama3"):
    """
    Interacts with Ollama and yields word-by-word content from the AI response.
    """
    try:
        stream = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            stream=True,
        )

        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                yield chunk['message']['content']
    except Exception as e:
        raise Exception(f"Chatbot logic error: {str(e)}")
