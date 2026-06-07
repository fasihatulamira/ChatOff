import os
import json
import math
import ollama
import PyPDF2
import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure dotenv is loaded
load_dotenv()

DB_PATH = "rag_db.json"

def get_embedding(text):
    model = os.getenv("OLLAMA_EMBED_MODEL", os.getenv("OLLAMA_MODEL", "llama3"))
    res = ollama.embeddings(model=model, prompt=text)
    return res["embedding"]

def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    return dot_product / (magnitude_a * magnitude_b)

def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            if "metadata" not in db:
                db["metadata"] = {}
            return db
    return {"chunks": [], "embeddings": [], "sources": [], "metadata": {}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f)

def process_pdf(file_path, progress_callback=None):
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        return False, f"Failed to read PDF: {str(e)}"
        
    chunk_size = 2500
    overlap = 300
    
    source_name = os.path.basename(file_path)
    db = load_db()
    
    # Check if already processed
    if source_name in db["sources"]:
        return False, "This PDF is already in the Knowledge Base."
        
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
            
    if not chunks:
        return False, "No usable text found in PDF."
        
    # Generate embeddings concurrently using a thread pool
    embeddings = [None] * len(chunks)
    completed_count = 0
    
    def process_chunk(idx, chunk_text):
        return idx, get_embedding(chunk_text)
        
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
                # Cancel remaining tasks on failure
                for f in futures:
                    f.cancel()
                return False, f"Embedding generation failed: {str(e)}"
                
    # Save the generated chunks and embeddings in their correct order
    for idx, chunk in enumerate(chunks):
        db["chunks"].append(chunk)
        db["embeddings"].append(embeddings[idx])
        db["sources"].append(source_name)
        
    file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
    upload_date = datetime.datetime.now().strftime("%b %d, %Y")
    db["metadata"][source_name] = {"size": f"{file_size_mb} MB", "date": upload_date}
        
    save_db(db)
    return True, f"Successfully processed {len(chunks)} chunks from {source_name}."

def add_manual_entry(title, question, answer):
    db = load_db()
    source_name = f"Manual: {title}"
    if source_name in db["sources"]:
        return False, "An entry with this title already exists."
        
    chunk = f"Title: {title}\nQuestion: {question}\nAnswer: {answer}"
    
    # Generate embedding
    try:
        emb = get_embedding(chunk)
    except Exception as e:
        return False, f"Failed to generate embedding: {str(e)}"
        
    db["chunks"].append(chunk)
    db["embeddings"].append(emb)
    db["sources"].append(source_name)
    
    upload_date = datetime.datetime.now().strftime("%b %d, %Y")
    db["metadata"][source_name] = {"size": "Manual Entry", "date": upload_date}
    
    save_db(db)
    return True, f"Successfully added manual entry: {title}"

def query_rag(prompt, top_k=None, threshold=0.15, source_filter=None, prompt_emb_holder=None):
    if top_k is None:
        try:
            top_k = int(os.getenv("RAG_TOP_K", "4"))
        except:
            top_k = 4

    db = load_db()
    if not db["chunks"]:
        return None
        
    if prompt_emb_holder is not None and prompt_emb_holder[0] is not None:
        prompt_emb = prompt_emb_holder[0]
    else:
        prompt_emb = get_embedding(prompt)
        if prompt_emb_holder is not None:
            prompt_emb_holder[0] = prompt_emb
    
    scores = []
    for i, emb in enumerate(db["embeddings"]):
        # Option B: Support strict PDF filtering
        if source_filter and db["sources"][i] != source_filter:
            continue
        score = cosine_similarity(prompt_emb, emb)
        if score >= threshold:
            scores.append((score, db["chunks"][i]))
            
    if not scores:
        return None
        
    scores.sort(key=lambda x: x[0], reverse=True)
    
    top_chunks = [chunk for score, chunk in scores[:top_k]]
    
    # Build a system prompt based on retrieved chunks
    context = "\n\n---\n\n".join(top_chunks)
    system_prompt = (
        f"You are a helpful AI assistant. Use the following extracted document context to provide a "
        f"detailed, comprehensive, and complete answer to the user's question. Do not summarize too "
        f"briefly; ensure you capture technical specifications, rules, details, and context. "
        f"Please reply in the same language as the user's question (e.g., if the user asks in Malay, "
        f"reply in Malay). If the answer is not in the context, do your best to answer it normally.\n\n"
        f"### Document Context:\n{context}"
    )
    return system_prompt

def get_source_content(source_name):
    db = load_db()
    content_chunks = []
    for i, src in enumerate(db["sources"]):
        if src == source_name:
            content_chunks.append(db["chunks"][i])
    return "\n\n---\n\n".join(content_chunks)

def get_all_sources():
    db = load_db()
    unique_sources = list(set(db["sources"]))
    return [(src, db["metadata"].get(src, {"size": "Unknown", "date": "Unknown"})) for src in unique_sources]

def delete_source(source_name):
    db = load_db()
    indices_to_keep = [i for i, src in enumerate(db["sources"]) if src != source_name]
    db["chunks"] = [db["chunks"][i] for i in indices_to_keep]
    db["embeddings"] = [db["embeddings"][i] for i in indices_to_keep]
    db["sources"] = [db["sources"][i] for i in indices_to_keep]
    if source_name in db["metadata"]:
        del db["metadata"][source_name]
    save_db(db)

def clear_rag():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

UNANSWERED_DB_PATH = "unanswered_db.json"

def load_unanswered_db():
    if os.path.exists(UNANSWERED_DB_PATH):
        with open(UNANSWERED_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_unanswered_db(db):
    with open(UNANSWERED_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f)

def save_unanswered_question(question, username="Anonymous"):
    import uuid
    db = load_unanswered_db()
    # avoid duplicates
    if any(q["question"].lower().strip() == question.lower().strip() for q in db):
        return
    entry = {
        "id": str(uuid.uuid4()),
        "question": question,
        "username": username,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "unanswered",
        "answer": None,
        "question_emb": None
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

def find_answered_question_match(prompt, threshold=0.85, prompt_emb_holder=None):
    db = load_unanswered_db()
    answered_qs = [q for q in db if q.get("status") == "answered"]
    if not answered_qs:
        return None
        
    # 1. Exact case-insensitive match
    for q in answered_qs:
        if q["question"].lower().strip() == prompt.lower().strip():
            return q["answer"]
            
    # 2. Semantic similarity matching
    try:
        if prompt_emb_holder is not None and prompt_emb_holder[0] is not None:
            prompt_emb = prompt_emb_holder[0]
        else:
            prompt_emb = get_embedding(prompt)
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
        print(f"Error checking semantic similarity for Q&A: {e}")
        raise e
        
    return None
