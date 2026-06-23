"""Quick RAG reply test — run from project folder: python scripts/test_rag_reply.py"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from paths import load_env

load_env()

from chatbot import collapse_output_repetition, get_response, looks_like_gibberish, rag_num_predict
from rag import query_rag

PROMPT = "apa ada dalam pdf ni"
SOURCE = "Manual-Sistem-26.pdf"


def main():
    print(f"Testing: {PROMPT!r}  source={SOURCE}")
    result = query_rag(PROMPT, source_filter=SOURCE)
    if not result:
        print("FAIL: query_rag returned None (no match)")
        return 1

    print(f"match={result['best_score']:.0%}  context_chars={len(result['context'])}")

    chunks = []
    for part in get_response(
        PROMPT,
        system_prompt=result["system_prompt"],
        num_predict_override=rag_num_predict(PROMPT),
    ):
        chunks.append(part)

    text = collapse_output_repetition("".join(chunks))
    print(f"gibberish={looks_like_gibberish(text)}")
    print("--- reply ---")
    print(text[:1500])
    if len(text) > 1500:
        print("...")
    return 0 if text.strip() and not looks_like_gibberish(text) else 1


if __name__ == "__main__":
    raise SystemExit(main())
