"""Benchmark Ollama chat and RAG performance."""
import os
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from paths import load_env

load_env()

import ollama  # noqa: E402

PROMPT = "What is the company policy on leave?"


def bench_chat(model, messages, label, num_predict=None):
    from chatbot import _ollama_options

    t0 = time.perf_counter()
    first_token = None
    chars = 0
    options = _ollama_options(num_predict)
    stream = ollama.chat(model=model, messages=messages, stream=True, options=options)
    for chunk in stream:
        if first_token is None:
            first_token = time.perf_counter() - t0
        chars += len(chunk.get("message", {}).get("content", ""))
    total = time.perf_counter() - t0
    print(f"{label}: ttft={first_token:.2f}s total={total:.2f}s chars={chars}")


def main():
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    print(f"chat_model={model} embed_model={embed_model}")
    print(f"RAG_TOP_K={os.getenv('RAG_TOP_K', '2')} RAG_MAX_CONTEXT_CHARS={os.getenv('RAG_MAX_CONTEXT_CHARS', '3000')}")

    from rag import load_db, _build_rag_context
    from rag_index import ensure_norm_embeddings, search_similar

    t0 = time.perf_counter()
    db = load_db()
    ensure_norm_embeddings(db)
    print(f"rag_db_load: {time.perf_counter() - t0:.3f}s chunks={len(db['chunks'])}")

    if not db["chunks"]:
        print("No RAG chunks — upload PDFs first for full benchmark.")
        return

    t0 = time.perf_counter()
    emb = ollama.embeddings(model=embed_model, prompt=PROMPT)["embedding"]
    print(f"embedding: {time.perf_counter() - t0:.3f}s dims={len(emb)}")

    t0 = time.perf_counter()
    ranked = search_similar(emb, db["norm_embeddings"])
    print(f"vector_search_{len(db['embeddings'])}: {time.perf_counter() - t0:.3f}s")

    top_k = int(os.getenv("RAG_TOP_K", "2"))
    top_idx = [idx for _, idx in ranked[:top_k]]
    context = _build_rag_context([db["chunks"][i] for i in top_idx])
    sys_prompt = (
        "Answer the user's question using the document context below. "
        "Be clear and structured.\n\n"
        f"### Document Context:\n{context}"
    )
    print(f"rag_context_chars={len(sys_prompt)}")

    bench_chat(
        model,
        [{"role": "system", "content": "You are helpful."}, {"role": "user", "content": PROMPT}],
        "chat_no_rag",
    )
    bench_chat(
        model,
        [{"role": "system", "content": sys_prompt}, {"role": "user", "content": PROMPT}],
        "chat_with_rag",
    )
    bench_chat(
        model,
        [
            {"role": "system", "content": "Reply with a short 3-word title only."},
            {"role": "user", "content": f"Title for: {PROMPT}"},
        ],
        "title_generation",
        num_predict=int(os.getenv("OLLAMA_TITLE_NUM_PREDICT", "32")),
    )


if __name__ == "__main__":
    main()
