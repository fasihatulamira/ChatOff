"""Automated release-readiness checks (no GUI interaction)."""
import datetime
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from paths import load_env, get_app_dir

load_env()

FAILURES: list[str] = []
WARNINGS: list[str] = []


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    if not ok:
        FAILURES.append(f"{name}: {detail}" if detail else name)


def warn(name: str, detail: str):
    print(f"[WARN] {name} — {detail}")
    WARNINGS.append(f"{name}: {detail}")


def main() -> int:
    app_dir = get_app_dir()

    print("=== ChatOff Release Check ===\n")

    required = [
        "app.py",
        "GUI.py",
        "auth.py",
        "login.py",
        "chatbot.py",
        "rag.py",
        "rag_index.py",
        "schema.sql",
        ".env.example",
        "requirements.txt",
        "requirements-ocr.txt",
        "SETUP.txt",
        "QA_CHECKLIST.txt",
        "README.md",
        "password_utils.py",
        "paths.py",
        "pdf_utils.py",
        "change_password.py",
        "setup.ps1",
        "build.ps1",
        "ChatOff_Setup.iss",
        "test.py",
        "scripts/system_test.py",
        "scripts/benchmark_ollama.py",
        "scripts/release_check.py",
        "gui/app.py",
        "gui/chat.py",
        "gui/admin.py",
        "gui/dialogs.py",
        "gui/home.py",
        "gui/sidebar.py",
        "gui/theme.py",
        "gui/processing.py",
    ]
    for f in required:
        check(f"file {f}", os.path.isfile(os.path.join(app_dir, f)))

    check("no split_gui.py dev script", not os.path.isfile(os.path.join(app_dir, "split_gui.py")))

    gitignore = open(os.path.join(app_dir, ".gitignore"), encoding="utf-8").read()
    for pattern in (".env", "rag_db.json", "unanswered_db.json", "dist/", "build/"):
        check(f".gitignore has {pattern}", pattern in gitignore)

    schema = open(os.path.join(app_dir, "schema.sql"), encoding="utf-8").read()
    check("schema: must_change_password", "must_change_password" in schema)
    check("schema: password VARCHAR(255)", "VARCHAR(255)" in schema)

    env_example = open(os.path.join(app_dir, ".env.example"), encoding="utf-8").read()
    for key in ("OLLAMA_MODEL", "RAG_MAX_CONTEXT_CHARS", "OLLAMA_NUM_CTX", "OLLAMA_TITLE_NUM_PREDICT"):
        check(f".env.example has {key}", key in env_example)

    iss = open(os.path.join(app_dir, "ChatOff_Setup.iss"), encoding="utf-8").read()
    req = open(os.path.join(app_dir, "requirements.txt"), encoding="utf-8").read()
    req_ocr = open(os.path.join(app_dir, "requirements-ocr.txt"), encoding="utf-8").read()

    check("installer pulls llama3.2:3b", "llama3.2:3b" in iss)
    check("installer version 2.2", "AppVersion=2.2" in iss)
    check("requirements.txt excludes pytesseract", "pytesseract" not in req)
    check("requirements-ocr.txt has pytesseract", "pytesseract" in req_ocr)

    gui_py = open(os.path.join(app_dir, "GUI.py"), encoding="utf-8").read()
    check(
        "GUI.py is thin re-export",
        "from gui.app import OfflineChatbot" in gui_py and len(gui_py.splitlines()) < 25,
    )

    try:
        from auth import check_database, ensure_schema

        ensure_schema()
        db_ok, db_msg = check_database()
        check("database reachable", db_ok, db_msg)
    except Exception as e:
        check("database reachable", False, str(e))

    try:
        from password_utils import hash_password, verify_password

        h = hash_password("release_test")
        check("bcrypt works", verify_password("release_test", h))
    except Exception as e:
        check("bcrypt works", False, str(e))

    try:
        from rag import load_db, _build_rag_context, _rag_max_context_chars
        from rag_index import ensure_norm_embeddings

        db = load_db()
        ensure_norm_embeddings(db)
        check(
            "rag norm index",
            "norm_embeddings" in db and len(db["norm_embeddings"]) == len(db["embeddings"]),
        )
        check("rag db loads", True, f"{len(db.get('chunks', []))} chunks")
        cap = _rag_max_context_chars()
        ctx = _build_rag_context(["x" * 2000, "y" * 2000])
        check("rag context capped", len(ctx) <= cap + 10, f"len={len(ctx)} cap={cap}")
    except Exception as e:
        check("rag db loads", False, str(e))

    try:
        import ollama

        models = ollama.list().get("models", [])
        names = [m.get("name", m.get("model", "")) for m in models]
        chat = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        embed = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        check("ollama reachable", True, f"{len(names)} models")
        if not any(chat in n for n in names):
            warn("chat model", f"{chat} not installed — run: ollama pull {chat}")
        if not any(embed in n for n in names):
            warn("embed model", f"{embed} not installed")
    except Exception as e:
        check("ollama reachable", False, str(e))

    dist_exe = os.path.join(app_dir, "dist", "app.exe")
    if os.path.isfile(dist_exe):
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(dist_exe))
        warn("dist/app.exe", f"built {mtime:%Y-%m-%d %H:%M} — rebuild with .\\build.ps1 before shipping")
    else:
        warn("dist/app.exe", "missing — run .\\build.ps1 before creating installer")

    print(f"\n=== Summary: {len(FAILURES)} failed, {len(WARNINGS)} warnings ===")
    for f in FAILURES:
        print(f"  FAIL: {f}")
    for w in WARNINGS:
        print(f"  WARN: {w}")
    if not FAILURES:
        print("\nRelease check PASSED (review warnings before shipping).")
        return 0
    print("\nRelease check FAILED — fix issues above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
