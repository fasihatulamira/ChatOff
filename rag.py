import os
import re
import json
import math
import threading
import ollama
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from paths import get_app_dir, load_env
from pdf_utils import extract_pdf_text, chunk_text
from rag_index import ensure_norm_embeddings, normalize, search_similar
from chatbot import detect_language

load_env()

APP_DIR = get_app_dir()
DB_PATH = os.path.join(APP_DIR, "rag_db.json")
UNANSWERED_DB_PATH = os.path.join(APP_DIR, "unanswered_db.json")

_db_lock = threading.Lock()


def get_embedding(text):
    from chatbot import _ollama_keep_alive

    model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    keep_alive = _ollama_keep_alive()
    kwargs = {"keep_alive": keep_alive} if keep_alive else {}
    res = ollama.embeddings(model=model, prompt=text, **kwargs)
    return res["embedding"]


def precompute_prompt_embedding(prompt, prompt_emb_holder=None, cancel_event=None):
    """Compute the query embedding once so RAG lookups can run in parallel."""
    if cancel_event is not None and cancel_event.is_set():
        return None
    if prompt_emb_holder is not None and prompt_emb_holder[0] is not None:
        return prompt_emb_holder[0]
    try:
        emb = get_embedding(prompt)
        if prompt_emb_holder is not None:
            prompt_emb_holder[0] = emb
        return emb
    except Exception as e:
        print(f"Embedding precompute failed: {e}")
        return None


def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    return dot_product / (magnitude_a * magnitude_b)


def load_db():
    with _db_lock:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                if "metadata" not in db:
                    db["metadata"] = {}
                return db
        return {"chunks": [], "embeddings": [], "norm_embeddings": [], "sources": [], "metadata": {}}


def save_db(db):
    with _db_lock:
        ensure_norm_embeddings(db)
        db["embed_model"] = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        temp_path = DB_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(db, f)
        os.replace(temp_path, DB_PATH)


def get_embed_model_warning() -> str | None:
    db = load_db()
    if not db.get("chunks"):
        return None
    stored = db.get("embed_model")
    current = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    if stored and stored != current:
        return (
            f"Knowledge base was indexed with '{stored}' but .env uses '{current}'. "
            "Re-upload PDFs (or Clear All) for accurate search results."
        )
    if not stored:
        return (
            "Knowledge base may have been indexed before the embed model was tracked. "
            "Re-upload PDFs if search results seem inaccurate."
        )
    return None


def _rag_min_score() -> float:
    try:
        return float(os.getenv("RAG_MIN_SCORE", "0.35"))
    except ValueError:
        return 0.35


def _rag_best_min_score() -> float:
    """Minimum score for the best matching chunk; below this we skip RAG entirely."""
    try:
        return float(os.getenv("RAG_BEST_MIN_SCORE", "0.42"))
    except ValueError:
        return 0.42


def _rag_max_context_chars() -> int:
    try:
        configured = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "3500"))
    except ValueError:
        configured = 3500
    try:
        num_ctx = int(os.getenv("OLLAMA_RAG_NUM_CTX", os.getenv("OLLAMA_NUM_CTX", "8192")))
    except ValueError:
        num_ctx = 8192
    try:
        reserve_tokens = int(os.getenv("RAG_CTX_TOKEN_RESERVE", "900"))
    except ValueError:
        reserve_tokens = 900
    # Rough chars/token budget so prompt + PDF context fits Ollama num_ctx.
    char_budget = max(1200, int((num_ctx - reserve_tokens) * 3.2))
    return min(configured, char_budget)


def _rag_neighbor_radius() -> int:
    try:
        return int(os.getenv("RAG_NEIGHBOR_RADIUS", "1"))
    except ValueError:
        return 1


def _is_list_style_question(prompt: str) -> bool:
    lower = prompt.lower()
    patterns = [
        r"\ball\b", r"\bevery\b", r"\blist\b", r"\bpoints?\b", r"\bsteps?\b",
        r"\bitem", r"\bsenaraikan\b", r"\bsemua\b", r"\bberapa\b", r"\blengkap\b",
        r"\bcomplete\b", r"\bfull\b", r"\bentire\b", r"\bnyatakan\b", r"\bterangkan\b",
    ]
    return any(re.search(p, lower) for p in patterns)


def _is_explanatory_question(prompt: str) -> bool:
    """User asks for explanation, description, or deeper detail."""
    lower = prompt.lower()
    patterns = [
        r"\bexplain\b", r"\bdescribe\b", r"\bdetail", r"\bwhy\b", r"\bhow\b",
        r"\bwhat is\b", r"\btell me about\b", r"\belaborate\b",
        r"\bterangkan\b", r"\bjelaskan\b", r"\bhuraikan\b", r"\bkenapa\b",
        r"\bbagaimana\b", r"\bapa itu\b", r"\bceritakan\b",
    ]
    return any(re.search(p, lower) for p in patterns)


def needs_long_rag_answer(prompt: str) -> bool:
    """Broad, list-style, or explanatory questions need more tokens and more PDF chunks."""
    return (
        _is_list_style_question(prompt)
        or _is_pdf_meta_question(prompt)
        or _is_explanatory_question(prompt)
    )


def _adaptive_top_k(prompt: str, base_top_k: int) -> int:
    if not needs_long_rag_answer(prompt):
        return base_top_k
    try:
        list_top_k = int(os.getenv("RAG_LIST_TOP_K", "6"))
    except ValueError:
        list_top_k = 6
    return max(base_top_k, list_top_k)


def _expand_chunk_indices(db: dict, matched_indices: list[int], radius: int) -> list[int]:
    """Include neighboring chunks from the same source so numbered lists stay complete."""
    expanded: set[int] = set()
    source_positions: dict[str, list[int]] = {}
    for i, src in enumerate(db["sources"]):
        source_positions.setdefault(src, []).append(i)

    for idx in matched_indices:
        src = db["sources"][idx]
        positions = source_positions[src]
        try:
            pos = positions.index(idx)
        except ValueError:
            expanded.add(idx)
            continue
        for offset in range(-radius, radius + 1):
            neighbor_pos = pos + offset
            if 0 <= neighbor_pos < len(positions):
                expanded.add(positions[neighbor_pos])

    return sorted(expanded)


def _chunk_quality_score(text: str) -> float:
    """Estimate how readable a chunk is (0–1). Low scores often cause model gibberish."""
    if not text or len(text.strip()) < 40:
        return 0.0
    letters = len(re.findall(r"[A-Za-zÀ-ÿ]", text))
    digits = len(re.findall(r"\d", text))
    weird = len(re.findall(r"[^\w\s.,;:!?()\-/'\"%\n]", text))
    total = max(len(text), 1)
    letter_ratio = letters / total
    weird_ratio = weird / total
    if letter_ratio < 0.35:
        return 0.0
    return max(0.0, min(1.0, letter_ratio - weird_ratio * 2))


def _is_pdf_meta_question(prompt: str) -> bool:
    """User asks how to read/understand the linked PDF rather than a specific fact."""
    lower = prompt.lower()
    has_doc_ref = any(
        token in lower
        for token in ("pdf", "dokumen", "document", "manual", "fail", "lampiran")
    )
    has_understand = any(
        re.search(pat, lower)
        for pat in (
            r"\bfaham\b", r"\bmemahami\b", r"\bbaca\b", r"\bunderstand\b", r"\bread\b",
            r"\bmacam mana\b", r"\bbagaimana\b", r"\bhow\b", r"\bapa\b",
            r"\bada\s+apa\b", r"\bapa\s+ada\b", r"\bkandungan\b", r"\bisi\b",
        )
    )
    return has_doc_ref and has_understand


def _rag_instruction_block(user_prompt: str, context: str) -> str:
    lang = detect_language(user_prompt, context=context)
    completeness = ""
    if _is_list_style_question(user_prompt):
        completeness = (
            " PENTING: Senaraikan SEMUA item/point yang berkaitan dalam konteks. "
            "Jangan tinggalkan atau ringkaskan senarai berangka/bullet."
        ) if lang == "malay" else (
            " IMPORTANT: Include ALL relevant items/points from the context. "
            "Do not skip or summarize numbered or bulleted lists."
        )

    meta = ""
    if _is_pdf_meta_question(user_prompt):
        meta = (
            " Pengguna bertanya tentang kandungan keseluruhan dokumen/PDF ini. "
            "Terangkan SEMUA bahagian, modul, dan perkara penting dari konteks. "
            "Lengkapkan setiap senarai bullet — jangan berhenti di tengah. "
            "Tamatkan jawapan dengan ayat penutup yang jelas. "
            "JANGAN beritahu pengguna anda tidak boleh membaca PDF — teks sudah disediakan."
        ) if lang == "malay" else (
            " The user wants a full overview of this document/PDF. "
            "Explain ALL major sections and key points from the context. "
            "Complete every bullet list — do not stop mid-list. "
            "End with a clear closing sentence. "
            "Do NOT say you cannot read PDFs — the text is already provided."
        )

    if lang == "malay":
        return (
            "Anda ialah pembantu AI untuk manual/latihan sistem. "
            "Teks dokumen PDF sudah diekstrak dan disediakan dalam konteks di bawah. "
            "JANGAN sekali-kali beritahu pengguna anda tidak boleh membaca PDF, fail, atau dokumen. "
            "JANGAN minta pengguna memuat naik fail atau menampal teks. "
            "Jawab soalan HANYA berdasarkan konteks dokumen di bawah. "
            "Jawab dalam Bahasa Malaysia yang jelas (bukan Indonesia): gunakan mempunyai, keupayaan, anda. "
            "Beri jawapan yang LENGKAP, TERPERINCI, dan berstruktur — jelaskan konsep, langkah, dan contoh jika ada dalam konteks. "
            "Gunakan perenggan dan bullet point jika sesuai; elakkan jawapan satu ayat sahaja. "
            "Jangan ulang ayat atau perkataan yang sama. Jangan campur bahasa lain."
            f"{completeness}{meta} "
            "Jika jawapan tiada dalam konteks, nyatakan dengan jelas perkara yang tiada."
        )
    return (
        "You are an AI assistant for system/training manuals. "
        "The PDF document text has already been extracted and is provided in the context below. "
        "NEVER tell the user you cannot read PDFs, files, or documents. "
        "NEVER ask the user to upload files or paste text. "
        "Answer ONLY using the document context below. "
        "Give COMPLETE, DETAILED, and well-structured answers — explain concepts, steps, and examples when present in the context. "
        "Use paragraphs and bullet points where helpful; avoid one-sentence replies. Do not repeat sentences."
        f"{completeness}{meta} "
        "If the answer is not in the context, say clearly what is missing."
    )


def _build_rag_system_prompt(user_prompt: str, context: str) -> str:
    """Legacy single-string prompt (kept for tests); prefer build_rag_messages()."""
    instructions = _rag_instruction_block(user_prompt, context)
    heading = "### Konteks Dokumen:" if detect_language(user_prompt, context=context) == "malay" else "### Document Context:"
    return f"{instructions}\n\n{heading}\n{context}"


def build_rag_messages(user_prompt: str, context: str) -> list[dict]:
    """
    Build Ollama messages for RAG. Document text goes in the user turn so smaller
    models (e.g. llama3.2:3b) follow context instead of refusing PDF questions.
    """
    lang = detect_language(user_prompt, context=context)
    context_heading = "### Konteks Dokumen:" if lang == "malay" else "### Document Context:"
    question_heading = "### Soalan:" if lang == "malay" else "### Question:"
    user_content = f"{context_heading}\n{context}\n\n{question_heading}\n{user_prompt}"
    return [
        {"role": "system", "content": _rag_instruction_block(user_prompt, context)},
        {"role": "user", "content": user_content},
    ]


def _estimate_tokens(text: str) -> int:
    """Conservative token estimate for Malay/mixed PDF text."""
    return max(1, int(len(text) / 2.8))


def fit_rag_messages(
    user_prompt: str,
    context: str,
    num_ctx: int,
    num_predict: int,
) -> tuple[list[dict], str]:
    """
    Shrink context if needed so prompt + generation fits num_ctx.
    Returns (messages, context_used).
    """
    try:
        reserve = int(os.getenv("RAG_CTX_TOKEN_RESERVE", "900"))
    except ValueError:
        reserve = 900
    token_budget = max(800, num_ctx - num_predict - reserve)

    trimmed = context
    messages = build_rag_messages(user_prompt, trimmed)
    while _estimate_tokens("".join(m["content"] for m in messages)) > token_budget and len(trimmed) > 400:
        trimmed = trimmed[: int(len(trimmed) * 0.75)].rstrip() + "..."
        messages = build_rag_messages(user_prompt, trimmed)
    return messages, trimmed


def _normalize_chunk(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _trim_adjacent_overlap(chunks: list[str]) -> list[str]:
    """Trim repeated text between neighboring chunks from the same PDF."""
    if len(chunks) <= 1:
        return chunks
    result = [chunks[0]]
    for chunk in chunks[1:]:
        prev = result[-1]
        overlap = 0
        max_check = min(len(prev), len(chunk), 400)
        for size in range(max_check, 30, -1):
            if _normalize_chunk(prev[-size:]) == _normalize_chunk(chunk[:size]):
                overlap = size
                break
        result.append(chunk[overlap:].lstrip() if overlap else chunk)
    return result


def _dedupe_chunks(chunks: list[str]) -> list[str]:
    """Drop duplicate or redundant chunks before sending context to the model."""
    if len(chunks) <= 1:
        return chunks
    unique: list[str] = []
    seen_norms: set[str] = set()
    for chunk in chunks:
        norm = _normalize_chunk(chunk)
        if not norm or norm in seen_norms:
            continue
        if any(len(norm) > 80 and norm in _normalize_chunk(existing) for existing in unique):
            continue
        seen_norms.add(norm)
        unique.append(chunk)
    return _trim_adjacent_overlap(unique)


def _build_rag_context(chunks: list[str]) -> str:
    """Join top chunks but cap total size so Ollama prefill stays fast."""
    chunks = _dedupe_chunks(chunks)
    max_chars = _rag_max_context_chars()
    parts: list[str] = []
    total = 0
    separator = "\n\n---\n\n"

    for chunk in chunks:
        if _chunk_quality_score(chunk) < 0.25:
            continue
        if parts:
            total += len(separator)
        if total >= max_chars:
            break
        remaining = max_chars - total
        if len(chunk) > remaining:
            if remaining > 80:
                parts.append(chunk[: remaining - 3] + "...")
            break
        parts.append(chunk)
        total += len(chunk)

    return separator.join(parts)


def process_pdf(file_path, progress_callback=None):
    text, extract_method = extract_pdf_text(file_path)
    if not text.strip():
        return False, "No usable text found in PDF. Enable RAG_OCR_ENABLED=true for scanned documents."

    source_name = os.path.basename(file_path)
    db = load_db()

    if source_name in db["sources"]:
        return False, "This PDF is already in the Knowledge Base."

    chunks = chunk_text(text)
    if not chunks:
        return False, "No usable text found in PDF after chunking."

    embeddings = [None] * len(chunks)
    completed_count = 0

    def process_chunk(idx, chunk_text_item):
        return idx, get_embedding(chunk_text_item)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_chunk, idx, chunk): idx for idx, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            try:
                idx, emb = future.result()
                embeddings[idx] = emb
                completed_count += 1
                if progress_callback:
                    if progress_callback(completed_count, len(chunks)) is False:
                        for f in futures:
                            f.cancel()
                        return False, "Upload cancelled by user."
            except Exception as e:
                for f in futures:
                    f.cancel()
                return False, f"Embedding generation failed: {str(e)}"

    for idx, chunk in enumerate(chunks):
        db["chunks"].append(chunk)
        db["embeddings"].append(embeddings[idx])
        db.setdefault("norm_embeddings", [])
        db["norm_embeddings"].append(normalize(embeddings[idx]))
        db["sources"].append(source_name)

    file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
    now = datetime.datetime.now()
    upload_date = now.strftime("%b %d, %Y")
    db["metadata"][source_name] = {
        "size": f"{file_size_mb} MB",
        "date": upload_date,
        "added_at": now.isoformat(timespec="seconds"),
        "extractor": extract_method,
        "chunks": len(chunks),
    }

    save_db(db)
    return True, (
        f"Successfully processed {len(chunks)} chunks from {source_name} "
        f"(extracted via {extract_method})."
    )


def add_manual_entry(title, question, answer):
    db = load_db()
    source_name = f"Manual: {title}"
    if source_name in db["sources"]:
        return False, "An entry with this title already exists."

    chunk = f"Title: {title}\nQuestion: {question}\nAnswer: {answer}"

    try:
        emb = get_embedding(chunk)
    except Exception as e:
        return False, f"Failed to generate embedding: {str(e)}"

    db["chunks"].append(chunk)
    db["embeddings"].append(emb)
    db.setdefault("norm_embeddings", [])
    db["norm_embeddings"].append(normalize(emb))
    db["sources"].append(source_name)

    upload_date = datetime.datetime.now()
    db["metadata"][source_name] = {
        "size": "Manual Entry",
        "date": upload_date.strftime("%b %d, %Y"),
        "added_at": upload_date.isoformat(timespec="seconds"),
    }

    save_db(db)
    return True, f"Successfully added manual entry: {title}"


def query_rag(prompt, top_k=None, threshold=None, source_filter=None, prompt_emb_holder=None, cancel_event=None):
    """
    Search the knowledge base. Returns a dict:
      { system_prompt, sources: [{name, score}], best_score }
    or None if no confident match.
    """
    if top_k is None:
        try:
            top_k = int(os.getenv("RAG_TOP_K", "5"))
        except ValueError:
            top_k = 5
    top_k = _adaptive_top_k(prompt, top_k)
    if threshold is None:
        threshold = _rag_min_score()

    if cancel_event is not None and cancel_event.is_set():
        return None

    db = load_db()
    ensure_norm_embeddings(db)
    if not db["chunks"]:
        return None

    try:
        if prompt_emb_holder is not None and prompt_emb_holder[0] is not None:
            prompt_emb = prompt_emb_holder[0]
        else:
            if cancel_event is not None and cancel_event.is_set():
                return None
            prompt_emb = get_embedding(prompt)
            if cancel_event is not None and cancel_event.is_set():
                return None
            if prompt_emb_holder is not None:
                prompt_emb_holder[0] = prompt_emb
    except Exception as e:
        print(f"RAG embedding failed: {e}")
        return None

    if source_filter:
        indices = [i for i, src in enumerate(db["sources"]) if src == source_filter]
    else:
        indices = None

    ranked = search_similar(prompt_emb, db["norm_embeddings"], indices)
    all_scores = [(score, i) for score, i in ranked]

    if not all_scores:
        return None

    best_score = all_scores[0][0]

    if best_score < _rag_best_min_score():
        print(
            f"RAG skipped: best score {best_score:.3f} below "
            f"RAG_BEST_MIN_SCORE ({_rag_best_min_score()})"
        )
        return None

    filtered = [(s, i) for s, i in all_scores if s >= threshold][:top_k]
    if not filtered:
        return None

    matched_indices = [i for _, i in filtered]
    expanded_indices = _expand_chunk_indices(db, matched_indices, _rag_neighbor_radius())
    top_chunks = [db["chunks"][i] for i in expanded_indices]

    source_best: dict[str, float] = {}
    for score, idx in filtered:
        src = db["sources"][idx]
        source_best[src] = max(source_best.get(src, 0), score)
    sources_meta = [
        {"name": name, "score": score}
        for name, score in sorted(source_best.items(), key=lambda x: x[1], reverse=True)
    ]

    context = _build_rag_context(top_chunks)
    if not context.strip():
        print("RAG skipped: matched chunks failed quality check (possible bad PDF extraction)")
        return None

    system_prompt = _build_rag_system_prompt(prompt, context)

    return {
        "system_prompt": system_prompt,
        "context": context,
        "sources": sources_meta,
        "best_score": best_score,
    }


def get_source_content(source_name):
    db = load_db()
    content_chunks = []
    for i, src in enumerate(db["sources"]):
        if src == source_name:
            content_chunks.append(db["chunks"][i])
    return "\n\n---\n\n".join(content_chunks)


def build_topic_builder_excerpt(source_name: str, max_chars: int | None = None) -> tuple[str, bool, int]:
    """
    Build a representative excerpt for Topic Builder from indexed PDF chunks.
    Returns (text, was_trimmed, full_length).
    """
    if max_chars is None:
        try:
            max_chars = int(os.getenv("TOPIC_BUILDER_MAX_CHARS", "12000"))
        except ValueError:
            max_chars = 12000

    db = load_db()
    chunks = [db["chunks"][i] for i, src in enumerate(db["sources"]) if src == source_name]
    if not chunks:
        return "", False, 0

    full = "\n\n---\n\n".join(chunks)
    full_len = len(full)
    if full_len <= max_chars:
        return full, False, full_len

    if len(chunks) == 1:
        return chunks[0][:max_chars], True, full_len

    # Sample from each chunk so later sections (B, C, D…) are not missed.
    per_chunk = max(350, max_chars // len(chunks))
    parts: list[str] = []
    for i, chunk in enumerate(chunks):
        budget = per_chunk * 2 if i in (0, len(chunks) - 1) else per_chunk
        parts.append(chunk[: min(len(chunk), budget)])

    excerpt = "\n\n---\n\n".join(parts)
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars]
    return excerpt, True, full_len


def get_all_sources():
    db = load_db()
    unique_sources = list(set(db["sources"]))
    return [(src, db["metadata"].get(src, {"size": "Unknown", "date": "Unknown"})) for src in unique_sources]


def delete_source(source_name):
    db = load_db()
    indices_to_keep = [i for i, src in enumerate(db["sources"]) if src != source_name]
    db["chunks"] = [db["chunks"][i] for i in indices_to_keep]
    db["embeddings"] = [db["embeddings"][i] for i in indices_to_keep]
    if "norm_embeddings" in db:
        db["norm_embeddings"] = [db["norm_embeddings"][i] for i in indices_to_keep]
    db["sources"] = [db["sources"][i] for i in indices_to_keep]
    if source_name in db["metadata"]:
        del db["metadata"][source_name]
    save_db(db)


def clear_rag():
    with _db_lock:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)


def load_unanswered_db():
    with _db_lock:
        if os.path.exists(UNANSWERED_DB_PATH):
            with open(UNANSWERED_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return []


def save_unanswered_db(db):
    with _db_lock:
        temp_path = UNANSWERED_DB_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(db, f)
        os.replace(temp_path, UNANSWERED_DB_PATH)


def save_unanswered_question(question, username="Anonymous"):
    import uuid
    db = load_unanswered_db()
    if any(q["question"].lower().strip() == question.lower().strip() for q in db):
        return
    entry = {
        "id": str(uuid.uuid4()),
        "question": question,
        "username": username,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "unanswered",
        "answer": None,
        "question_emb": None,
    }
    db.append(entry)
    save_unanswered_db(db)


def get_unanswered_questions():
    return load_unanswered_db()


def delete_unanswered_question(q_id):
    db = load_unanswered_db()
    db = [q for q in db if q["id"] != q_id]
    save_unanswered_db(db)


def submit_admin_answer(q_id, answer):
    db = load_unanswered_db()
    for q in db:
        if q["id"] == q_id:
            q["status"] = "answered"
            q["answer"] = answer
            try:
                q["question_emb"] = get_embedding(q["question"])
            except Exception as e:
                print(f"Failed to generate embedding for answered question: {e}")
                q["question_emb"] = None
            break
    save_unanswered_db(db)


def find_answered_question_match(prompt, threshold=0.85, prompt_emb_holder=None, cancel_event=None):
    if cancel_event is not None and cancel_event.is_set():
        return None

    db = load_unanswered_db()
    answered_qs = [q for q in db if q.get("status") == "answered"]
    if not answered_qs:
        return None

    for q in answered_qs:
        if q["question"].lower().strip() == prompt.lower().strip():
            return q["answer"]

    try:
        if prompt_emb_holder is not None and prompt_emb_holder[0] is not None:
            prompt_emb = prompt_emb_holder[0]
        else:
            if cancel_event is not None and cancel_event.is_set():
                return None
            prompt_emb = get_embedding(prompt)
            if cancel_event is not None and cancel_event.is_set():
                return None
            if prompt_emb_holder is not None:
                prompt_emb_holder[0] = prompt_emb
        best_score = 0
        best_answer = None
        for q in answered_qs:
            emb = q.get("question_emb")
            if emb:
                score = cosine_similarity(prompt_emb, emb)
                if score > best_score:
                    best_score = score
                    best_answer = q["answer"]
        if best_score >= threshold:
            return best_answer
    except Exception as e:
        print(f"Semantic Q&A match skipped (Ollama unavailable): {e}")
        return None

    return None
