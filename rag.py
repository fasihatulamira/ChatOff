import os
import json
import math
import ollama
import PyPDF2
import datetime
import json
import math
import ollama
import PyPDF2

DB_PATH = "rag_db.json"

def get_embedding(text):
    res = ollama.embeddings(model="llama3", prompt=text)
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
        
    chunk_size = 500
    overlap = 100
    
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
        
    # Generate embeddings
    for idx, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(idx + 1, len(chunks))
        emb = get_embedding(chunk)
        db["chunks"].append(chunk)
        db["embeddings"].append(emb)
        db["sources"].append(source_name)
        
    file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
    upload_date = datetime.datetime.now().strftime("%b %d, %Y")
    db["metadata"][source_name] = {"size": f"{file_size_mb} MB", "date": upload_date}
        
    save_db(db)
    return True, f"Successfully processed {len(chunks)} chunks from {source_name}."

def query_rag(prompt, top_k=3):
    db = load_db()
    if not db["chunks"]:
        return ""
        
    prompt_emb = get_embedding(prompt)
    
    scores = []
    for i, emb in enumerate(db["embeddings"]):
        score = cosine_similarity(prompt_emb, emb)
        scores.append((score, db["chunks"][i]))
        
    scores.sort(key=lambda x: x[0], reverse=True)
    
    top_chunks = [chunk for score, chunk in scores[:top_k]]
    
    # Build a system prompt based on retrieved chunks
    context = "\n\n---\n\n".join(top_chunks)
    system_prompt = f"You are a helpful AI assistant. Use the following extracted document context to answer the user's question accurately. If the answer is not in the context, do your best to answer it normally.\n\n### Document Context:\n{context}"
    return system_prompt

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
