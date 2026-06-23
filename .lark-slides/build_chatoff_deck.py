#!/usr/bin/env python3
"""Build ChatOff presentation slides in Lark."""
import html
import json
import re
import subprocess
import sys

GRADIENT_COVER = "linear-gradient(135deg,rgba(15,23,42,1) 0%,rgba(0,97,167,1) 55%,rgba(142,36,170,1) 100%)"
GRADIENT_LIGHT = "linear-gradient(180deg,rgba(248,250,252,1) 0%,rgba(226,232,240,1) 100%)"
TEAL = "rgba(0,151,167,1)"
PURPLE = "rgba(142,36,170,1)"
DARK = "rgba(15,23,42,1)"
GRAY = "rgba(71,85,105,1)"
WHITE = "rgba(255,255,255,1)"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def esc_amp(text: str) -> str:
    return re.sub(r"&(?!([a-zA-Z]+|#[0-9]+);)", "&amp;", text)


def slide_wrap(style_fill: str, body: str) -> str:
    return (
        '<slide xmlns="http://www.larkoffice.com/sml/2.0">'
        f"<style><fill><fillColor color=\"{style_fill}\"/></fill></style>"
        f"<data>{body}</data>"
        "</slide>"
    )


def text_shape(x, y, w, h, text_type, paragraphs, color=DARK, size=None, align="left", rich=False):
    size_attr = f' fontSize="{size}"' if size else ""
    color_attr = f' color="{color}"'
    align_attr = f' textAlign="{align}"'
    fmt = esc_amp if rich else esc
    ps = "".join(f"<p>{fmt(p)}</p>" for p in paragraphs)
    return (
        f'<shape type="text" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
        f'<content textType="{text_type}"{size_attr}{color_attr}{align_attr}>{ps}</content>'
        "</shape>"
    )


def rect(x, y, w, h, color, radius=12):
    return (
        f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
        f'<fill><fillColor color="{color}"/></fill>'
        f"</shape>"
    )


def icon(x, y, size, icon_type, color=None):
    color_attr = f' color="{color}"' if color else ""
    return f'<icon iconType="{icon_type}" topLeftX="{x}" topLeftY="{y}" width="{size}" height="{size}"{color_attr}/>'


def card(x, y, w, h, title, body, accent=TEAL, rich=False):
    return (
        rect(x, y, w, h, "rgba(255,255,255,1)", 14)
        + rect(x, y, w, 6, accent, 0)
        + text_shape(x + 18, y + 18, w - 36, 34, "headline", [title], DARK, 18)
        + text_shape(x + 18, y + 52, w - 36, h - 70, "body", body, GRAY, 14, rich=rich)
    )


def mermaid_board(x, y, w, h, diagram: str) -> str:
    return (
        f'<whiteboard topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
        "<mermaid><![CDATA[\n"
        f"{diagram}\n"
        "]]></mermaid></whiteboard>"
    )


SLIDES = [
    slide_wrap(
        GRADIENT_COVER,
        rect(0, 0, 960, 540, GRADIENT_COVER, 0)
        + rect(0, 470, 960, 70, "rgba(0,0,0,0.18)", 0)
        + icon(80, 120, 72, "iconpark/Hardware/robot-one.svg", WHITE)
        + text_shape(170, 110, 700, 70, "title", ["ChatOff AI"], WHITE, 48)
        + text_shape(170, 175, 700, 50, "sub-headline", ["Offline Knowledge Assistant with RAG"], "rgba(226,232,240,1)", 24)
        + text_shape(80, 300, 800, 90, "body", [
            "Desktop system that lets employees ask questions in natural language",
            "and get accurate answers from company PDFs — fully offline.",
        ], "rgba(241,245,249,1)", 18)
        + text_shape(80, 488, 500, 30, "caption", ["Version 2.2  |  Final Year / Industrial Project Presentation"], "rgba(203,213,225,1)", 12),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        rect(0, 0, 120, 540, TEAL, 0)
        + text_shape(150, 48, 760, 50, "title", ["Agenda"], DARK, 40)
        + text_shape(150, 100, 760, 30, "caption", ["What we will cover in this presentation"], GRAY, 14)
        + text_shape(150, 150, 760, 340, "body", [
            "01  Problem Statement",
            "02  Project Objectives",
            "03  Solution Overview",
            "04  Use Case Diagram",
            "05  Technology Stack",
            "06  System Workflow (RAG Pipeline)",
            "07  Database Design",
            "08  Key Features (User and Admin)",
            "09  Limitations & Future Work",
        ], DARK, 20),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        rect(0, 0, 960, 90, "rgba(0,151,167,0.12)", 0)
        + text_shape(60, 28, 840, 50, "title", ["Problem Statement"], DARK, 38)
        + icon(60, 120, 40, "iconpark/Communicate/message-security.svg", TEAL)
        + text_shape(110, 118, 780, 40, "headline", ["Employees struggle to find answers in large document sets"], DARK, 22)
        + card(60, 175, 260, 150, "Slow Search", ["Manual PDF reading wastes time when policies, manuals, and SOPs are long and scattered."], "rgba(239,68,68,1)")
        + card(340, 175, 260, 150, "Inconsistent Answers", ["Different staff give different interpretations without a single trusted source."], "rgba(245,158,11,1)")
        + card(620, 175, 260, 150, "Privacy Risk", ["Uploading internal documents to cloud AI tools exposes company data."], "rgba(142,36,170,1)")
        + rect(60, 360, 820, 120, "rgba(255,255,255,1)", 16)
        + text_shape(90, 385, 760, 80, "body", [
            "<strong>Business impact:</strong> Lower productivity, onboarding delays, repeated supervisor interruptions, and compliance risk when staff cannot quickly verify procedures.",
        ], DARK, 16, rich=True),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        rect(0, 0, 960, 90, "rgba(142,36,170,0.10)", 0)
        + text_shape(60, 28, 840, 50, "title", ["Project Objectives"], DARK, 38)
        + card(60, 120, 200, 170, "Offline AI Chat", ["Provide an on-premise chatbot using Ollama — no internet required after setup."], TEAL)
        + card(280, 120, 200, 170, "PDF Knowledge Base", ["Upload company PDFs and answer questions with Retrieval-Augmented Generation (RAG)."], PURPLE)
        + card(500, 120, 200, 170, "Guided Self-Service", ["Quick-topic buttons plus free-text questions for flexible user support."], "rgba(37,99,235,1)")
        + card(720, 120, 200, 170, "Admin Control", ["Manage documents, topics, unanswered questions, and preview user experience."], "rgba(16,185,129,1)")
        + rect(60, 320, 860, 150, TEAL, 16)
        + text_shape(90, 350, 800, 90, "body", [
            "<strong>Success criteria:</strong> Users receive sourced answers from uploaded PDFs within ~1 minute; admins can update knowledge without code changes; system runs on Windows with MySQL + Ollama.",
        ], WHITE, 17, rich=True),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        text_shape(60, 36, 840, 50, "title", ["Solution Overview"], DARK, 38)
        + text_shape(60, 88, 840, 28, "caption", ["ChatOff = Desktop UI + Ollama LLM + RAG Knowledge Base + MySQL"], GRAY, 14)
        + rect(60, 140, 250, 320, "rgba(255,255,255,1)", 16)
        + icon(150, 170, 56, "iconpark/Peoples/data-user.svg", TEAL)
        + text_shape(80, 245, 210, 90, "headline", ["End User"], DARK, 22, "center")
        + text_shape(80, 300, 210, 120, "body", ["Login, pick topics, ask questions, view chat history"], GRAY, 13, "center")
        + rect(355, 210, 250, 180, "rgba(0,151,167,0.15)", 16)
        + icon(452, 235, 56, "iconpark/Hardware/robot-one.svg", TEAL)
        + text_shape(375, 305, 210, 70, "headline", ["ChatOff App"], DARK, 20, "center")
        + rect(650, 140, 250, 150, "rgba(255,255,255,1)", 16)
        + icon(745, 165, 48, "iconpark/Office/file-pdf-one.svg", PURPLE)
        + text_shape(670, 225, 210, 50, "body", ["PDF RAG Index<br/>(rag_db.json)"], GRAY, 13, "center", rich=True)
        + rect(650, 310, 250, 150, "rgba(255,255,255,1)", 16)
        + icon(745, 335, 48, "iconpark/Datas/database-code.svg", TEAL)
        + text_shape(670, 395, 210, 50, "body", ["MySQL<br/>(users, history, topics)"], GRAY, 13, "center", rich=True)
        + text_shape(60, 480, 840, 40, "caption", ["Fully offline inference — documents never leave the local machine"], GRAY, 13, "center"),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        text_shape(60, 30, 840, 44, "title", ["Use Case Diagram"], DARK, 36)
        + text_shape(60, 78, 840, 24, "caption", ["Main actors and system interactions"], GRAY, 13)
        + mermaid_board(
            40,
            110,
            880,
            390,
            """flowchart LR
    subgraph Actors
      U[End User]
      A[Administrator]
    end
    subgraph ChatOff System
      UC1[Login / Sign Up]
      UC2[Ask Question via Chat]
      UC3[Select Quick Topic]
      UC4[View Chat History]
      UC5[Upload PDF to Knowledge Base]
      UC6[Build & Manage Topics]
      UC7[Answer Unanswered Questions]
      UC8[Preview User Chat]
      UC9[Delete / View Documents]
    end
    U --> UC1
    U --> UC2
    U --> UC3
    U --> UC4
    A --> UC1
    A --> UC5
    A --> UC6
    A --> UC7
    A --> UC8
    A --> UC9""",
        ),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        text_shape(60, 30, 840, 44, "title", ["Technology Stack"], DARK, 36)
        + text_shape(60, 78, 840, 24, "caption", ["Modern Python desktop stack with local AI"], GRAY, 13)
        + card(60, 120, 260, 160, "Frontend", ["CustomTkinter (Python)<br/>Dark-themed desktop GUI<br/>Chat, Admin Console, Dialogs"], TEAL, rich=True)
        + card(340, 120, 260, 160, "AI Engine", ["Ollama (llama3.2:3b)<br/>Streaming responses<br/>Local embeddings (nomic-embed-text)"], PURPLE, rich=True)
        + card(620, 120, 260, 160, "RAG Layer", ["PyMuPDF / PyPDF2<br/>Text chunking + vector search<br/>JSON vector store (rag_db.json)"], "rgba(37,99,235,1)", rich=True)
        + card(60, 300, 260, 160, "Database", ["MySQL 8<br/>Users, chat history<br/>Topics and sessions"], TEAL, rich=True)
        + card(340, 300, 260, 160, "Security", ["bcrypt password hashing<br/>Role-based admin access<br/>Forced password change"], "rgba(239,68,68,1)", rich=True)
        + card(620, 300, 260, 160, "Deployment", ["PyInstaller (.exe)<br/>Inno Setup installer<br/>Windows + WSL dev"], "rgba(16,185,129,1)", rich=True),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        text_shape(60, 30, 840, 44, "title", ["System Workflow — RAG Pipeline"], DARK, 36)
        + text_shape(60, 78, 840, 24, "caption", ["How a user question becomes a sourced answer"], GRAY, 13)
        + mermaid_board(
            50,
            105,
            860,
            400,
            """flowchart TD
    Q[User sends question] --> E[Embed question via Ollama]
    E --> P{Previously answered<br/>by admin?}
    P -->|Yes| A1[Return saved answer]
    P -->|No| R[Search PDF chunks<br/>cosine similarity]
    R --> M{Match score<br/>above threshold?}
    M -->|Yes| C[Build context prompt<br/>from top-k chunks]
    C --> L[Stream answer from LLM]
    L --> S[Show Sources footer]
    M -->|No| U[Save to Unanswered Queue]
    U --> G[Generate general AI reply]
    G --> H[Save chat to MySQL]""",
        ),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        text_shape(60, 30, 840, 44, "title", ["Database Design"], DARK, 36)
        + text_shape(60, 78, 840, 24, "caption", ["MySQL relational data + JSON vector knowledge store"], GRAY, 13)
        + card(60, 115, 400, 185, "MySQL Tables", [
            "<strong>users</strong> — accounts, bcrypt password, must_change_password",
            "<strong>chat_history</strong> — session_id, prompt, response, timestamps",
            "<strong>chat_topics</strong> — main/sub topics, reply_message, pdf_source",
        ], TEAL, rich=True)
        + card(490, 115, 400, 185, "RAG Store (rag_db.json)", [
            "<strong>chunks</strong> — text segments from PDFs",
            "<strong>embeddings</strong> — vector representations",
            "<strong>metadata</strong> — file size, upload date, extractor type",
        ], PURPLE, rich=True)
        + card(60, 320, 830, 170, "Data Relationships", [
            "Users own many chat sessions; each session has multiple prompt/response pairs.",
            "Topics link to specific PDF sources for filtered RAG queries.",
            "Unanswered questions (unanswered_db.json) queue items for admin review.",
        ], "rgba(37,99,235,1)"),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        text_shape(60, 30, 840, 44, "title", ["Key Features"], DARK, 36)
        + text_shape(60, 78, 400, 24, "caption", ["End User Experience"], TEAL, 13)
        + text_shape(500, 78, 400, 24, "caption", ["Admin Console"], PURPLE, 13)
        + rect(60, 110, 400, 360, "rgba(255,255,255,1)", 16)
        + text_shape(85, 130, 350, 320, "body", [
            "• Login / sign-up with secure authentication",
            "• Quick-topic buttons for common questions",
            "• Free-text chat with streaming AI replies",
            "• Stop button to cancel generation",
            "• Chat sessions saved in sidebar history",
            "• Source citations (PDF name + match score)",
            "• Malay and English language detection",
        ], DARK, 15)
        + rect(500, 110, 400, 360, "rgba(255,255,255,1)", 16)
        + text_shape(525, 130, 350, 320, "body", [
            "• Dashboard with document/topic stats",
            "• Upload PDF with progress bar and OCR option",
            "• AI Topic Builder from PDF content",
            "• Manage topics (create/edit/delete)",
            "• Unanswered Questions queue",
            "• Manual knowledge entries",
            "• Preview User Chat mode",
            "• Document sort and library management",
        ], DARK, 15),
    ),
    slide_wrap(
        GRADIENT_LIGHT,
        text_shape(60, 30, 840, 44, "title", ["Limitations & Future Work"], DARK, 36)
        + card(60, 95, 410, 200, "Current Limitations", [
            "• Requires local Ollama + GPU/RAM (8GB+ recommended)",
            "• First RAG reply may take up to ~1 minute",
            "• Scanned PDFs need Tesseract OCR setup",
            "• Windows-focused deployment (PyInstaller)",
            "• Single-machine — not multi-user server yet",
        ], "rgba(239,68,68,1)")
        + card(490, 95, 410, 200, "Future Enhancements", [
            "• Faster models and hardware optimization",
            "• Multi-language document support",
            "• Centralized server for team access",
            "• Analytics dashboard for usage insights",
            "• Auto-sync knowledge from shared drives",
        ], "rgba(16,185,129,1)")
        + rect(60, 320, 840, 150, "rgba(255,255,255,1)", 16)
        + text_shape(90, 345, 780, 100, "body", [
            "<strong>Why it still delivers value today:</strong> ChatOff keeps sensitive documents on-premise, gives instant self-service for repetitive questions, and lets admins improve answers without developer involvement.",
        ], DARK, 16, rich=True),
    ),
    slide_wrap(
        GRADIENT_COVER,
        rect(0, 0, 960, 540, GRADIENT_COVER, 0)
        + icon(430, 120, 80, "iconpark/Hardware/robot-one.svg", WHITE)
        + text_shape(60, 220, 840, 60, "title", ["Thank You"], WHITE, 48, "center")
        + text_shape(60, 290, 840, 50, "sub-headline", ["ChatOff AI — Offline Knowledge Assistant"], "rgba(226,232,240,1)", 22, "center")
        + text_shape(60, 360, 840, 80, "body", [
            "Questions and Discussion",
            "<br/>Demo available: Login → Upload PDF → Ask a question → View sourced answer",
        ], "rgba(241,245,249,1)", 18, "center", rich=True)
        + text_shape(60, 490, 840, 30, "caption", ["ChatOff v2.2  |  Python • Ollama • MySQL • CustomTkinter"], "rgba(203,213,225,1)", 12, "center"),
    ),
]


def main():
    print("Creating Lark presentation...")
    create = subprocess.run(
        [
            "lark-cli",
            "slides",
            "+create",
            "--as",
            "user",
            "--title",
            "ChatOff AI - System Presentation",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(create.stdout)
    pres_id = result["data"]["xml_presentation_id"]
    print(f"Created presentation: {pres_id}")

    slide_ids = []
    for i, slide_xml in enumerate(SLIDES, start=1):
        payload = json.dumps({"slide": {"content": slide_xml}})
        cmd = [
            "lark-cli",
            "slides",
            "xml_presentation.slide",
            "create",
            "--as",
            "user",
            "--params",
            json.dumps({"xml_presentation_id": pres_id}),
            "--data",
            payload,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"Failed on slide {i}: {proc.stderr}", file=sys.stderr)
            sys.exit(1)
        slide_resp = json.loads(proc.stdout)
        slide_id = slide_resp.get("data", {}).get("slide_id", "?")
        slide_ids.append(slide_id)
        print(f"  Added slide {i}/12 ({slide_id})")

    verify = subprocess.run(
        [
            "lark-cli",
            "slides",
            "xml_presentations",
            "get",
            "--as",
            "user",
            "--params",
            json.dumps({"xml_presentation_id": pres_id}),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    verify_data = json.loads(verify.stdout)
    slides_count = len(verify_data.get("data", {}).get("slides", []))
    print(f"\nVerification: {slides_count} slides in presentation")

    output = {
        "xml_presentation_id": pres_id,
        "title": "ChatOff AI - System Presentation",
        "slides_added": len(slide_ids),
        "slide_ids": slide_ids,
        "url": result.get("data", {}).get("url"),
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
