import os
import re
import time
import threading
import ollama
from paths import load_env

load_env()


_MALAY_STRONG_MARKERS = [
    r"\bapa(?:kah)?\b",
    r"\bsiapa(?:kah)?\b",
    r"\bbagaimana\b",
    r"\bmengapa\b",
    r"\bkenapa\b",
    r"\bberapa\b",
    r"\bbila\b",
    r"\bnyatakan\b",
    r"\bsenaraikan\b",
    r"\bbagitau\b",
    r"\bberitahu\b",
    r"\bterangkan\b",
    r"\bjelaskan\b",
    r"\btentang\b",
    r"\bcadangkan\b",
    r"\bhuraikan\b",
]

_MALAY_MARKERS = [
    r"\bapa\b", r"\bbagaimana\b", r"\bboleh\b", r"\bsaya\b", r"\bkamu\b",
    r"\banda\b", r"\bsila\b", r"\btolong\b", r"\bdi\b", r"\bke\b",
    r"\bdari\b", r"\buntuk\b", r"\bdengan\b", r"\byang\b", r"\bdan\b",
    r"\batau\b", r"\btidak\b", r"\btak\b", r"\bini\b", r"\bitu\b",
    r"\bada\b", r"\bkena\b", r"\bsudah\b", r"\bbelum\b", r"\bsemua\b",
    r"\bbila\b", r"\bsiapa\b", r"\bmana\b", r"\bberapa\b", r"\bkenapa\b",
    r"\bmengapa\b", r"\bseperti\b", r"\bjuga\b", r"\bpada\b", r"\bhanya\b",
    r"\bkomplain\b", r"\bnilai\b", r"\bpanduan\b", r"\bkerja\b", r"\bbagan\b",
    r"\balir\b", r"\bmahasiswa\b", r"\bpelajar\b", r"\bsoalan\b", r"\bjawapan\b",
]


def detect_language(text: str, context: str = "") -> str:
    lower = text.lower()
    if any(re.search(pat, lower) for pat in _MALAY_STRONG_MARKERS):
        return "malay"
    hits = sum(1 for pat in _MALAY_MARKERS if re.search(pat, lower))
    if hits >= 2:
        return "malay"
    if hits >= 1 and context and context_looks_malay(context):
        return "malay"
    return "english"


def context_looks_malay(context: str) -> bool:
    """Heuristic: RAG PDF chunk is mostly Bahasa Melayu."""
    if not context or len(context.strip()) < 80:
        return False
    lower = context.lower()
    hits = sum(1 for pat in _MALAY_MARKERS if re.search(pat, lower))
    return hits >= 8


def _build_language_instruction(prompt: str) -> str:
    lang = detect_language(prompt)
    if lang == "malay":
        return (
            "PENTING: Soalan pengguna dalam Bahasa Melayu. "
            "Anda MESTI menjawab sepenuhnya dalam Bahasa Malaysia yang jelas dan formal. "
            "Gunakan istilah Malaysia (contoh: mempunyai, keupayaan), bukan Indonesia (memiliki, kemampuan). "
            "Jangan gunakan Bahasa Inggeris. Jangan keluarkan teks rawak, kod, atau simbol pelik."
        )
    return (
        "IMPORTANT: The user's question is in English. "
        "You MUST reply entirely in clear English. Do NOT use Malay. "
        "Do not output random tokens, code, or garbled text."
    )


def _ollama_keep_alive() -> str | int | None:
    raw = os.getenv("OLLAMA_KEEP_ALIVE", "30m").strip()
    return raw or None


def _ollama_num_ctx(is_rag: bool) -> int | None:
    """Resolve context window. Leave RAG unset to use the model default (most stable)."""
    if is_rag:
        raw_ctx = os.getenv("OLLAMA_RAG_NUM_CTX", "").strip()
        if not raw_ctx:
            return None
    else:
        raw_ctx = os.getenv("OLLAMA_NUM_CTX", "4096").strip()
    try:
        num_ctx = int(raw_ctx)
        return num_ctx if num_ctx > 0 else None
    except ValueError:
        return None


def _ollama_options(num_predict_override: int | None = None, is_rag: bool = False) -> dict:
    options = {}
    try:
        default_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "1280"))
        options["num_predict"] = num_predict_override if num_predict_override is not None else default_predict
    except ValueError:
        options["num_predict"] = num_predict_override or 1280
    num_ctx = _ollama_num_ctx(is_rag)
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    num_thread = os.getenv("OLLAMA_NUM_THREAD", "").strip()
    if num_thread:
        try:
            options["num_thread"] = int(num_thread)
        except ValueError:
            pass
    try:
        options["temperature"] = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
    except ValueError:
        options["temperature"] = 0.3
    repeat_env = "OLLAMA_RAG_REPEAT_PENALTY" if is_rag else "OLLAMA_REPEAT_PENALTY"
    repeat_default = "1.0" if is_rag else "1.2"
    try:
        repeat_penalty = float(os.getenv(repeat_env, os.getenv("OLLAMA_REPEAT_PENALTY", repeat_default)))
        if repeat_penalty > 1.0:
            options["repeat_penalty"] = repeat_penalty
    except ValueError:
        if not is_rag:
            options["repeat_penalty"] = 1.2
    try:
        repeat_last_n = int(os.getenv("OLLAMA_REPEAT_LAST_N", "64"))
        if repeat_last_n > 0 and options.get("repeat_penalty", 1.0) > 1.0:
            options["repeat_last_n"] = repeat_last_n
    except ValueError:
        pass
    return options


def rag_num_predict(prompt: str = "") -> int:
    """Token budget for RAG answers — longer for overview/list-style PDF questions."""
    try:
        rag_predict = int(os.getenv("OLLAMA_RAG_NUM_PREDICT", "2048"))
    except ValueError:
        rag_predict = 2048
    try:
        default_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "1280"))
    except ValueError:
        default_predict = 1280
    base = max(rag_predict, default_predict)

    if prompt:
        from rag import needs_long_rag_answer

        if needs_long_rag_answer(prompt):
            try:
                long_predict = int(os.getenv("OLLAMA_LIST_NUM_PREDICT", "3072"))
            except ValueError:
                long_predict = 3072
            return max(base, long_predict)
    return base


_warmup_lock = threading.Lock()
_warmup_done = False


def warm_ollama_models() -> None:
    """Pre-load the embedding model so the first RAG lookup is faster."""
    global _warmup_done
    with _warmup_lock:
        if _warmup_done:
            return
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        try:
            ollama.embeddings(model=embed_model, prompt="warmup")
        except Exception:
            pass
        _warmup_done = True


def looks_truncated(text: str) -> bool:
    """Heuristic: model likely hit num_predict before finishing."""
    stripped = (text or "").strip()
    if len(stripped) < 80:
        return False
    tail = stripped[-120:]
    if re.search(r"[.!?…)\]\"']\s*$", tail):
        return False
    if stripped.endswith((":", "-", "—", ",", ";")):
        return True
    if re.search(r"(\*|\+|-)\s+[^\n]+$", tail):
        return True
    return not stripped.endswith((".", "!", "?", "。"))


def looks_like_gibberish(text: str) -> bool:
    """Detect incoherent model output (common when num_ctx is too small)."""
    if not text or len(text.strip()) < 40:
        return False
    letters = sum(1 for c in text if c.isalpha())
    spaces = text.count(" ")
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if not words:
        return True
    avg_word_len = sum(len(w) for w in words) / len(words)
    weird = sum(1 for c in text if ord(c) > 127 and not c.isalpha())
    # Long random tokens, low word boundaries, or lots of symbol soup.
    if avg_word_len > 14:
        return True
    if letters > 0 and weird / len(text) > 0.08:
        return True
    if spaces < len(text) / 80:
        return True
    return letters / len(text) < 0.45


def _normalize_for_dedup(text: str) -> str:
    text = re.sub(r"^[\s]*(?:[-*•]|\d+[.)])\s*", "", text.strip())
    return re.sub(r"\s+", " ", text.lower())


def collapse_output_repetition(text: str) -> str:
    """Remove duplicate words, lines, and sentences from model output."""
    if not text:
        return text

    text = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)

    lines = text.splitlines()
    seen: set[str] = set()
    out: list[str] = []
    prev_norm = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append(line)
            prev_norm = ""
            continue
        norm = _normalize_for_dedup(stripped)
        if norm and (norm == prev_norm or (len(norm) >= 8 and norm in seen)):
            continue
        if norm:
            seen.add(norm)
            prev_norm = norm
        out.append(line)

    result = "\n".join(out)
    para_lines: list[str] = []
    for line in result.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith(("-", "*", "•"))
            or re.match(r"^\d+[.)]", stripped)
        ):
            para_lines.append(line)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", stripped)
        seen_sents: set[str] = set()
        kept: list[str] = []
        for sent in sentences:
            norm = _normalize_for_dedup(sent)
            if norm and len(norm) >= 20 and norm in seen_sents:
                continue
            if norm and len(norm) >= 20:
                seen_sents.add(norm)
            kept.append(sent)
        para_lines.append(" ".join(kept) if kept else line)

    return "\n".join(para_lines)


def format_ai_error(exc: Exception) -> str:
    """Return a user-friendly message for common Ollama failures."""
    msg = str(exc).lower()
    if "forcibly closed" in msg or "status code: 500" in msg or "wsarecv" in msg:
        return (
            "Ollama stopped unexpectedly while generating the answer.\n\n"
            "Try these steps:\n"
            "1. Restart Ollama from the system tray\n"
            "2. Use a smaller model in .env (e.g. llama3.2:3b)\n"
            "3. Lower RAG_TOP_K or wait if a PDF upload is running"
        )
    if "connection refused" in msg or "connect" in msg and "failed" in msg:
        return "Cannot connect to Ollama. Please start Ollama and try again."
    if "model" in msg and "not found" in msg:
        return "The configured Ollama model is not installed. Run: ollama pull <model-name>"
    return f"AI error: {exc}"


def get_response(
    prompt: str,
    model: str = None,
    system_prompt: str = "",
    cancel_event=None,
    json_mode: bool = False,
    max_retries: int = None,
    num_predict_override: int | None = None,
):
    """
    Interact with Ollama and yield response text chunks (streaming).
    Retries once by default on transient Ollama connection failures.
    """
    if model is None:
        model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    if max_retries is None:
        try:
            max_retries = int(os.getenv("OLLAMA_MAX_RETRIES", "1"))
        except ValueError:
            max_retries = 1

    if json_mode:
        combined_system = system_prompt.strip() or "You only output valid JSON. No markdown or extra text."
    elif system_prompt.strip():
        # RAG prompt already sets language and document rules — do not stack a second instruction.
        combined_system = system_prompt.strip()
    else:
        lang_instruction = _build_language_instruction(prompt)
        combined_system = (
            f"{lang_instruction}\n\n"
            "You are a helpful AI assistant. Give thorough, detailed answers with clear explanations and examples when helpful."
        )

    messages = [
        {"role": "system", "content": combined_system},
        {"role": "user", "content": prompt},
    ]
    is_rag = bool(system_prompt.strip())
    options = _ollama_options(num_predict_override, is_rag=is_rag)
    keep_alive = _ollama_keep_alive()
    chat_kwargs = {"keep_alive": keep_alive} if keep_alive else {}
    last_error = None

    for attempt in range(max_retries + 1):
        if cancel_event is not None and cancel_event.is_set():
            return
        try:
            stream = ollama.chat(
                model=model,
                messages=messages,
                stream=True,
                options=options,
                **chat_kwargs,
            )
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    return
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
            return
        except Exception as e:
            if cancel_event is not None and cancel_event.is_set():
                return
            last_error = e
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise Exception(format_ai_error(last_error)) from last_error
