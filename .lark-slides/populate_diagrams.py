#!/usr/bin/env python3
"""Populate ChatOff diagram slides using native Lark shapes and lines."""
import json
import subprocess
import sys

PRES_ID = "X8UDs5FialThKwd8V1XjTXGipfg"


def run(cmd, check=True):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout


def apply_parts(slide_id: str, parts: list):
    path = f".lark-slides/parts_{slide_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(parts, f, ensure_ascii=False)
    run([
        "lark-cli", "slides", "+replace-slide", "--as", "user",
        "--presentation", PRES_ID,
        "--slide-id", slide_id,
        "--parts", f"@{path}",
    ])


def rect(x, y, w, h, color):
    return (
        f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
        f'<fill><fillColor color="{color}"/></fill><content/></shape>'
    )


def label(x, y, w, h, text, size=11, color="rgba(15,23,42,1)", align="center", bold=False):
    bold_attr = ' bold="true"' if bold else ""
    return (
        f'<shape type="text" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
        f'<content fontSize="{size}" color="{color}" textAlign="{align}"{bold_attr}>'
        f"<p>{text}</p></content></shape>"
    )


def line(x1, y1, x2, y2):
    return (
        f'<line startX="{x1}" startY="{y1}" endX="{x2}" endY="{y2}">'
        f'<border color="rgba(100,116,139,1)" width="2"/></line>'
    )


def box(x, y, w, h, fill, text, text_color="rgba(255,255,255,1)"):
    return rect(x, y, w, h, fill) + label(x, y + 8, w, h - 10, text, 11, text_color)


def replace_bg(block_id: str):
    return {
        "action": "block_replace",
        "block_id": block_id,
        "replacement": rect(40, 105, 880, 410, "rgba(255,255,255,0.95)"),
    }


def architecture_parts(block_id: str):
    parts = [replace_bg(block_id)]
    inserts = [
        label(60, 112, 840, 24, "Three-layer offline architecture", 13, "rgba(71,85,105,1)", "center"),
        rect(60, 140, 250, 340, "rgba(0,151,167,0.08)"),
        label(60, 148, 250, 22, "Desktop Client", 14, "rgba(0,151,167,1)", "center", True),
        box(85, 180, 200, 44, "rgba(0,151,167,0.9)", "Login / Sign Up"),
        box(85, 240, 200, 44, "rgba(0,151,167,0.9)", "Chat Screen"),
        box(85, 300, 200, 44, "rgba(0,151,167,0.9)", "Admin Console"),
        label(85, 360, 200, 40, "CustomTkinter GUI", 10, "rgba(71,85,105,1)"),
        rect(355, 140, 250, 340, "rgba(142,36,170,0.08)"),
        label(355, 148, 250, 22, "Python Application", 14, "rgba(142,36,170,1)", "center", True),
        box(380, 180, 200, 40, "rgba(142,36,170,0.9)", "auth.py"),
        box(380, 230, 200, 40, "rgba(142,36,170,0.9)", "chatbot.py"),
        box(380, 280, 200, 40, "rgba(142,36,170,0.9)", "rag.py / rag_index.py"),
        box(380, 330, 200, 40, "rgba(142,36,170,0.9)", "pdf_utils.py"),
        label(380, 380, 200, 40, "Business logic + RAG", 10, "rgba(71,85,105,1)"),
        rect(650, 140, 250, 340, "rgba(37,99,235,0.08)"),
        label(650, 148, 250, 22, "Local Services", 14, "rgba(37,99,235,1)", "center", True),
        box(675, 180, 200, 44, "rgba(37,99,235,0.9)", "Ollama LLM"),
        box(675, 240, 200, 44, "rgba(37,99,235,0.9)", "Embeddings"),
        box(675, 300, 200, 44, "rgba(37,99,235,0.9)", "MySQL DB"),
        box(675, 360, 200, 44, "rgba(37,99,235,0.9)", "JSON Stores"),
        label(675, 410, 200, 30, "Fully offline on Windows", 10, "rgba(71,85,105,1)"),
        line(310, 260, 355, 260),
        line(605, 260, 650, 260),
        label(300, 245, 60, 18, "calls", 9, "rgba(71,85,105,1)", "center"),
        label(595, 245, 60, 18, "uses", 9, "rgba(71,85,105,1)", "center"),
        label(120, 470, 720, 24, "rag_db.json + unanswered_db.json store vectors and admin review queue", 11, "rgba(71,85,105,1)", "center"),
    ]
    parts.extend({"action": "block_insert", "insertion": item} for item in inserts)
    return parts


def usecase_parts(block_id: str):
    parts = [replace_bg(block_id)]
    inserts = [
        rect(180, 130, 700, 300, "rgba(255,255,255,1)"),
        label(180, 135, 700, 24, "ChatOff System — Use Cases", 16, "rgba(15,23,42,1)", "center", True),
        box(60, 170, 110, 48, "rgba(0,151,167,1)", "End User"),
        box(60, 260, 110, 48, "rgba(142,36,170,1)", "Admin"),
        box(210, 165, 150, 36, "rgba(226,232,240,1)", "Login / Sign Up", "rgba(15,23,42,1)"),
        box(380, 165, 150, 36, "rgba(226,232,240,1)", "Ask via Chat", "rgba(15,23,42,1)"),
        box(550, 165, 150, 36, "rgba(226,232,240,1)", "Quick Topics", "rgba(15,23,42,1)"),
        box(720, 165, 150, 36, "rgba(226,232,240,1)", "Chat History", "rgba(15,23,42,1)"),
        box(210, 220, 150, 36, "rgba(255,237,213,1)", "Upload PDF", "rgba(15,23,42,1)"),
        box(380, 220, 150, 36, "rgba(255,237,213,1)", "Topic Builder", "rgba(15,23,42,1)"),
        box(550, 220, 150, 36, "rgba(255,237,213,1)", "Manage Topics", "rgba(15,23,42,1)"),
        box(720, 220, 150, 36, "rgba(255,237,213,1)", "Answer Queue", "rgba(15,23,42,1)"),
        box(380, 275, 150, 36, "rgba(255,237,213,1)", "Preview User Chat", "rgba(15,23,42,1)"),
        box(550, 275, 150, 36, "rgba(255,237,213,1)", "View / Delete Docs", "rgba(15,23,42,1)"),
        line(170, 194, 210, 183),
        line(170, 284, 210, 238),
        line(170, 194, 380, 183),
        line(170, 284, 465, 220),
        label(200, 340, 660, 40, "Gray = User use cases  |  Orange = Admin use cases", 11, "rgba(71,85,105,1)", "center"),
    ]
    parts.extend({"action": "block_insert", "insertion": item} for item in inserts)
    return parts


def workflow_parts(block_id: str):
    parts = [replace_bg(block_id)]
    inserts = [
        box(380, 125, 200, 40, "rgba(0,151,167,1)", "1. User sends question"),
        line(480, 165, 480, 180),
        box(380, 180, 200, 40, "rgba(37,99,235,1)", "2. Embed question"),
        line(480, 220, 480, 235),
        box(340, 235, 280, 40, "rgba(245,158,11,1)", "3. Previously answered?", "rgba(15,23,42,1)"),
        box(120, 300, 180, 40, "rgba(16,185,129,1)", "Yes: Saved answer"),
        box(620, 300, 200, 40, "rgba(142,36,170,1)", "No: Search PDF chunks"),
        box(620, 360, 200, 40, "rgba(245,158,11,1)", "Match above threshold?", "rgba(15,23,42,1)"),
        box(400, 420, 200, 40, "rgba(16,185,129,1)", "Yes: Stream + Sources"),
        box(700, 420, 170, 40, "rgba(239,68,68,1)", "No: Unanswered queue"),
        line(430, 167, 210, 300),
        label(260, 280, 40, 18, "Yes", 10, "rgba(71,85,105,1)"),
        line(530, 167, 680, 300),
        label(590, 280, 30, 18, "No", 10, "rgba(71,85,105,1)"),
        line(680, 340, 680, 360),
        line(630, 400, 500, 420),
        label(540, 405, 30, 18, "Yes", 10, "rgba(71,85,105,1)"),
        line(730, 400, 775, 420),
        label(748, 405, 30, 18, "No", 10, "rgba(71,85,105,1)"),
        label(90, 470, 780, 24, "All responses are saved to MySQL chat history", 11, "rgba(71,85,105,1)", "center"),
    ]
    parts.extend({"action": "block_insert", "insertion": item} for item in inserts)
    return parts


def erd_parts(block_id: str):
    parts = [replace_bg(block_id)]
    inserts = [
        label(60, 112, 840, 20, "MySQL relational schema + JSON knowledge stores", 12, "rgba(71,85,105,1)", "center"),
        rect(60, 140, 190, 150, "rgba(0,151,167,0.12)"),
        label(60, 145, 190, 20, "users", 13, "rgba(0,151,167,1)", "center", True),
        label(70, 168, 170, 110, "id PK<br/>username UK<br/>email UK<br/>password<br/>must_change_password", 10, "rgba(15,23,42,1)", "left"),
        rect(280, 140, 210, 170, "rgba(142,36,170,0.12)"),
        label(280, 145, 210, 20, "chat_history", 13, "rgba(142,36,170,1)", "center", True),
        label(290, 168, 190, 130, "id PK<br/>user_id FK<br/>session_id<br/>session_title<br/>prompt_text<br/>response_text", 10, "rgba(15,23,42,1)", "left"),
        rect(520, 140, 190, 150, "rgba(37,99,235,0.12)"),
        label(520, 145, 190, 20, "chat_topics", 13, "rgba(37,99,235,1)", "center", True),
        label(530, 168, 170, 110, "id PK<br/>parent_id FK<br/>topic_name<br/>reply_message<br/>pdf_source", 10, "rgba(15,23,42,1)", "left"),
        rect(740, 140, 170, 120, "rgba(16,185,129,0.12)"),
        label(740, 145, 170, 20, "option", 13, "rgba(16,185,129,1)", "center", True),
        label(750, 168, 150, 80, "id PK<br/>title<br/>content", 10, "rgba(15,23,42,1)", "left"),
        line(250, 210, 280, 210),
        label(255, 195, 50, 16, "1:N", 10, "rgba(71,85,105,1)", "center"),
        line(570, 170, 600, 170),
        label(575, 152, 50, 16, "parent", 9, "rgba(71,85,105,1)", "center"),
        rect(120, 330, 320, 150, "rgba(245,158,11,0.12)"),
        label(120, 335, 320, 20, "rag_db.json", 13, "rgba(245,158,11,1)", "center", True),
        label(130, 358, 300, 110, "chunks[] — PDF text segments<br/>embeddings[] — vector data<br/>metadata — file, size, date", 10, "rgba(15,23,42,1)", "left"),
        rect(520, 330, 320, 150, "rgba(239,68,68,0.12)"),
        label(520, 335, 320, 20, "unanswered_db.json", 13, "rgba(239,68,68,1)", "center", True),
        label(530, 358, 300, 110, "question, username, status<br/>Admin review queue for low-confidence queries", 10, "rgba(15,23,42,1)", "left"),
        line(410, 290, 280, 330),
        line(650, 290, 680, 330),
        label(430, 300, 80, 16, "RAG index", 9, "rgba(71,85,105,1)"),
        label(620, 300, 80, 16, "Admin queue", 9, "rgba(71,85,105,1)"),
    ]
    parts.extend({"action": "block_insert", "insertion": item} for item in inserts)
    return parts


def delete_test_slides():
    for sid in ("plS", "plM"):
        run([
            "lark-cli", "slides", "xml_presentation.slide", "delete",
            "--as", "user", "--yes",
            "--params", json.dumps({"xml_presentation_id": PRES_ID, "slide_id": sid}),
        ], check=False)


def main():
    delete_test_slides()
    diagrams = [
        ("plG", "bvg", architecture_parts),
        ("plP", "bvN", usecase_parts),
        ("pld", "bvQ", workflow_parts),
        ("plY", "bvI", erd_parts),
    ]
    for slide_id, block_id, builder in diagrams:
        print(f"Applying diagram to {slide_id}...")
        apply_parts(slide_id, builder(block_id))
    print("Done.")
    print(f"https://sukaduasukadotco.jp.larksuite.com/slides/{PRES_ID}")


if __name__ == "__main__":
    main()
