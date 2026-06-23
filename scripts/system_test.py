"""End-to-end smoke tests for ChatOff (no GUI interaction)."""
import os
import sys
import traceback

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from paths import load_env

load_env()

PASS = 0
FAIL = 0
WARN = 0
results = []


def ok(name, detail=""):
    global PASS
    PASS += 1
    results.append(("PASS", name, detail))


def fail(name, detail=""):
    global FAIL
    FAIL += 1
    results.append(("FAIL", name, detail))


def warn(name, detail=""):
    global WARN
    WARN += 1
    results.append(("WARN", name, detail))


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main():
    db_ok = False

    section("1. Core imports")
    try:
        from paths import get_app_dir

        ok("paths", get_app_dir())
    except Exception as e:
        fail("paths", str(e))
        print_results()
        return 1

    for mod in (
        "password_utils",
        "json_utils",
        "pdf_utils",
        "chatbot",
        "rag",
        "rag_index",
        "auth",
        "login",
        "change_password",
        "gui.processing",
    ):
        try:
            __import__(mod)
            ok(f"import {mod}")
        except Exception as e:
            fail(f"import {mod}", str(e))

    try:
        from GUI import OfflineChatbot

        ok("import GUI.OfflineChatbot")
    except Exception as e:
        fail("import GUI.OfflineChatbot", str(e))

    section("2. Password utils")
    try:
        from password_utils import hash_password, verify_password, is_bcrypt_hash

        h = hash_password("test123")
        assert verify_password("test123", h)
        assert not verify_password("wrong", h)
        assert is_bcrypt_hash(h)
        ok("bcrypt hash/verify")
    except Exception as e:
        fail("bcrypt hash/verify", str(e))

    section("3. Database")
    try:
        from auth import check_database, login_user, ensure_schema

        ensure_schema()
        db_ok, db_msg = check_database()
        if db_ok:
            ok("check_database", db_msg)
        else:
            fail("check_database", db_msg)
    except Exception as e:
        fail("database setup", traceback.format_exc())

    if db_ok:
        try:
            ok_login, login_result = login_user("admin", "admin123")
            if ok_login:
                if isinstance(login_result, dict):
                    warn(
                        "admin login with default password",
                        f"must_change_password={login_result.get('must_change_password')}",
                    )
                else:
                    ok("admin login", str(login_result))
            else:
                warn("admin default login", login_result)
                ok_login2, _ = login_user("admin", "wrong")
                if not ok_login2:
                    ok("admin rejects wrong password")
        except Exception as e:
            fail("admin login test", str(e))

    section("4. RAG")
    try:
        from rag import load_db, get_embed_model_warning, query_rag, get_all_sources

        db = load_db()
        ok("load_db", f"{len(db.get('chunks', []))} chunks")
        embed_warn = get_embed_model_warning()
        if embed_warn:
            warn("embed model", embed_warn)
        else:
            ok("embed model check")
        sources = get_all_sources()
        ok("get_all_sources", f"{len(sources)} source(s)")
    except Exception as e:
        fail("RAG load", str(e))

    section("5. Ollama connectivity")
    model_names = []
    try:
        import ollama

        models = ollama.list()
        model_names = [m.get("name", m.get("model", "")) for m in models.get("models", [])]
        if model_names:
            ok("ollama list", f"{len(model_names)} model(s)")
        else:
            warn("ollama list", "no models installed")
    except Exception as e:
        fail("ollama connection", str(e))

    chat_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    if model_names:
        if not any(chat_model in n for n in model_names):
            warn("chat model", f"{chat_model} not in ollama list")
        else:
            ok("chat model present", chat_model)
        if not any(embed_model in n for n in model_names):
            warn("embed model", f"{embed_model} not in ollama list")
        else:
            ok("embed model present", embed_model)

    section("6. Ollama embedding + RAG query")
    try:
        from rag import get_embedding, query_rag

        emb = get_embedding("test query for smoke test")
        ok("get_embedding", f"dims={len(emb)}")

        result = query_rag("What is the company policy?", cancel_event=None)
        if result is None:
            warn("query_rag", "no match (expected if KB empty or low score)")
        else:
            ok(
                "query_rag",
                f"best_score={result.get('best_score', 0):.2f} sources={len(result.get('sources', []))}",
            )
    except Exception as e:
        fail("embedding/query_rag", str(e))

    section("7. Chat streaming (short)")
    try:
        from chatbot import get_response, format_ai_error

        if not model_names or not any(chat_model in n for n in model_names):
            warn("chat stream", f"skipped — {chat_model} not installed")
        else:
            chunks = []
            for chunk in get_response("Say hi in one word.", model=chat_model):
                chunks.append(chunk)
                if len("".join(chunks)) > 5:
                    break
            text = "".join(chunks).strip()
            if text:
                ok("chat stream", repr(text[:40]))
            else:
                fail("chat stream", "empty response")
    except Exception as e:
        fail("chat stream", format_ai_error(e))

    section("8. GUI instantiation (headless)")
    try:
        from GUI import OfflineChatbot

        app_user = OfflineChatbot(user_name="Test User", username="testuser")
        app_user.destroy()
        ok("OfflineChatbot user frame")
        app_admin = OfflineChatbot(user_name="Administrator", username="admin")
        app_admin.destroy()
        ok("OfflineChatbot admin frame")
    except Exception as e:
        fail("GUI instantiation", traceback.format_exc())

    section("9. PDF utils")
    try:
        from pdf_utils import chunk_text

        chunks = chunk_text("Section One\n\nSome text.\n\nSection Two\n\nMore text." * 50)
        ok("chunk_text", f"{len(chunks)} chunk(s)")
    except Exception as e:
        fail("pdf_utils", str(e))

    print_results()
    return 0 if FAIL == 0 else 1


def print_results():
    section("SUMMARY")
    for status, name, detail in results:
        line = f"[{status}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)
    print(f"\nTotal: {PASS} passed, {WARN} warnings, {FAIL} failed")
    if FAIL:
        print("\n*** SYSTEM HAS FAILURES — see above ***")
    elif WARN:
        print("\nSystem OK with warnings.")
    else:
        print("\nAll checks passed.")


if __name__ == "__main__":
    sys.exit(main())
