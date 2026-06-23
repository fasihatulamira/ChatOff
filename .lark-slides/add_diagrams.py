#!/usr/bin/env python3
"""Add Mermaid diagram whiteboards to ChatOff Lark presentation."""
import json
import subprocess
import sys

PRES_ID = "X8UDs5FialThKwd8V1XjTXGipfg"
GRADIENT_LIGHT = "linear-gradient(180deg,rgba(248,250,252,1) 0%,rgba(226,232,240,1) 100%)"
DARK = "rgba(15,23,42,1)"
GRAY = "rgba(71,85,105,1)"


def run(*args, check=True):
    proc = subprocess.run(list(args), capture_output=True, text=True)
    if check and proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout


def slide_wrap(body: str) -> str:
    return (
        '<slide xmlns="http://www.larkoffice.com/sml/2.0">'
        f'<style><fill><fillColor color="{GRADIENT_LIGHT}"/></fill></style>'
        f"<data>{body}</data>"
        "</slide>"
    )


def text_shape(x, y, w, h, text_type, text, size=None, color=DARK, align="left"):
    size_attr = f' fontSize="{size}"' if size else ""
    return (
        f'<shape type="text" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
        f'<content textType="{text_type}"{size_attr} color="{color}" textAlign="{align}">'
        f"<p>{text}</p></content></shape>"
    )


def mermaid_board(x, y, w, h, diagram: str) -> str:
    return (
        f'<whiteboard topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
        "<mermaid><![CDATA[\n"
        f"{diagram.strip()}\n"
        "]]></mermaid></whiteboard>"
    )


ARCHITECTURE = """
flowchart TB
    subgraph Client["Desktop Client - CustomTkinter"]
        Login[Login / Sign Up]
        Chat[Chat Screen]
        Admin[Admin Console]
    end
    subgraph App["Python Application Layer"]
        Auth[auth.py]
        Bot[chatbot.py]
        RAG[rag.py + rag_index.py]
        PDF[pdf_utils.py]
    end
    subgraph Local["Local Services - Offline"]
        Ollama[Ollama LLM<br/>llama3.2:3b]
        Embed[Embeddings<br/>nomic-embed-text]
        MySQL[(MySQL<br/>users, history, topics)]
        JSON[(JSON Stores<br/>rag_db.json<br/>unanswered_db.json)]
    end
    Login --> Auth
    Chat --> Bot
    Chat --> RAG
    Admin --> RAG
    Admin --> PDF
    Bot --> Ollama
    RAG --> Embed
    RAG --> JSON
    RAG --> MySQL
    Auth --> MySQL
    PDF --> JSON
"""

USE_CASE = """
flowchart LR
    U((End User))
    A((Administrator))
    subgraph System["ChatOff System"]
        direction TB
        UC1[Login / Sign Up]
        UC2[Ask via Chat]
        UC3[Quick Topics]
        UC4[View Chat History]
        UC5[Upload PDF]
        UC6[Topic Builder]
        UC7[Manage Topics]
        UC8[Answer Queue]
        UC9[Preview User Chat]
        UC10[View / Delete Docs]
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
    A --> UC9
    A --> UC10
"""

WORKFLOW = """
flowchart TD
    Q[User sends question] --> E[Embed question via Ollama]
    E --> P{Previously answered<br/>by admin?}
    P -->|Yes| A1[Return saved answer]
    P -->|No| R[Search PDF chunks<br/>cosine similarity]
    R --> M{Match score<br/>above threshold?}
    M -->|Yes| C[Build context prompt<br/>from top-k chunks]
    C --> L[Stream answer from LLM]
    L --> S[Show sources footer]
    M -->|No| U[Save to Unanswered Queue]
    U --> G[Generate general AI reply]
    S --> H[Save chat to MySQL]
    G --> H
    A1 --> H
"""

ERD = """
erDiagram
    users ||--o{ chat_history : owns
    chat_topics ||--o{ chat_topics : parent_of
    users {
        int id PK
        varchar username UK
        varchar email UK
        varchar password
        tinyint must_change_password
    }
    chat_history {
        int id PK
        int user_id FK
        varchar session_id
        varchar session_title
        mediumtext prompt_text
        mediumtext response_text
    }
    chat_topics {
        int id PK
        int parent_id FK
        varchar topic_name
        text reply_message
        varchar pdf_source
    }
    option {
        int id PK
        varchar title
        text content
    }
"""

SLIDES = {
    "plb": slide_wrap(
        text_shape(60, 24, 840, 44, "title", "System Architecture Diagram", 36)
        + text_shape(
            60,
            72,
            840,
            24,
            "caption",
            "Layered offline desktop architecture: GUI, Python core, local AI and storage",
            13,
            GRAY,
        )
        + mermaid_board(30, 100, 900, 420, ARCHITECTURE)
    ),
    "ple": slide_wrap(
        text_shape(60, 24, 840, 44, "title", "Use Case Diagram", 36)
        + text_shape(
            60,
            72,
            840,
            24,
            "caption",
            "End User and Administrator interactions with ChatOff",
            13,
            GRAY,
        )
        + mermaid_board(30, 100, 900, 420, USE_CASE)
    ),
    "plE": slide_wrap(
        text_shape(60, 24, 840, 44, "title", "System Workflow — RAG Pipeline", 36)
        + text_shape(
            60,
            72,
            840,
            24,
            "caption",
            "Flowchart: how a user question becomes a sourced answer",
            13,
            GRAY,
        )
        + mermaid_board(30, 100, 900, 420, WORKFLOW)
    ),
    "pli": slide_wrap(
        text_shape(60, 24, 840, 44, "title", "Database Design — ERD", 36)
        + text_shape(
            60,
            72,
            840,
            24,
            "caption",
            "MySQL relational schema + JSON vector store (rag_db.json, unanswered_db.json)",
            13,
            GRAY,
        )
        + mermaid_board(30, 100, 900, 420, ERD)
    ),
}

AGENDA_UPDATE = [
    {
        "action": "block_replace",
        "block_id": "bOD",
        "replacement": (
            '<shape type="text" topLeftX="150" topLeftY="150" width="760" height="340">'
            '<content fontSize="20" fontFamily="思源黑体" color="rgba(15, 23, 42, 1)" textAlign="left">'
            "<p>01 Problem Statement</p>"
            "<p>02 Project Objectives</p>"
            "<p>03 System Architecture Diagram</p>"
            "<p>04 Use Case Diagram</p>"
            "<p>05 Technology Stack</p>"
            "<p>06 System Workflow (RAG Pipeline)</p>"
            "<p>07 Database Design (ERD)</p>"
            "<p>08 Key Features (User and Admin)</p>"
            "<p>09 Limitations &amp; Future Work</p>"
            "</content></shape>"
        ),
    }
]


def delete_slide(slide_id: str):
    run(
        "lark-cli",
        "slides",
        "xml_presentation.slide",
        "delete",
        "--as",
        "user",
        "--yes",
        "--params",
        json.dumps({"xml_presentation_id": PRES_ID, "slide_id": slide_id}),
    )


def create_slide(content: str, before_slide_id: str | None = None) -> str:
    data = {"slide": {"content": content}}
    if before_slide_id:
        data["before_slide_id"] = before_slide_id
    out = run(
        "lark-cli",
        "slides",
        "xml_presentation.slide",
        "create",
        "--as",
        "user",
        "--params",
        json.dumps({"xml_presentation_id": PRES_ID}),
        "--data",
        json.dumps(data),
    )
    resp = json.loads(out)
    return resp["data"]["slide_id"]


def replace_slide(slide_id: str, content: str):
    """Replace entire slide by delete + create at same position."""
    # Find next slide to insert before
    pres = json.loads(
        run(
            "lark-cli",
            "slides",
            "xml_presentations",
            "get",
            "--as",
            "user",
            "--params",
            json.dumps({"xml_presentation_id": PRES_ID}),
        )
    )
    import re

    xml = pres["data"]["xml_presentation"]["content"]
    ids = re.findall(r'<slide id="([^"]+)"', xml)
    try:
        idx = ids.index(slide_id)
        before = ids[idx + 1] if idx + 1 < len(ids) else None
    except ValueError:
        print(f"Slide {slide_id} not found", file=sys.stderr)
        raise SystemExit(1)

    delete_slide(slide_id)
    new_id = create_slide(content, before)
    print(f"  Replaced {slide_id} -> {new_id} (before={before})")
    return new_id


def main():
    print("Updating agenda slide...")
    run(
        "lark-cli",
        "slides",
        "+replace-slide",
        "--as",
        "user",
        "--presentation",
        PRES_ID,
        "--slide-id",
        "pla",
        "--parts",
        json.dumps(AGENDA_UPDATE),
    )

    # Replace from bottom to top so before_slide_id anchors stay valid
    order = ["pli", "plE", "ple", "plb"]
    for sid in order:
        print(f"Replacing diagram slide {sid}...")
        replace_slide(sid, SLIDES[sid])

    print("Verifying...")
    pres = json.loads(
        run(
            "lark-cli",
            "slides",
            "xml_presentations",
            "get",
            "--as",
            "user",
            "--params",
            json.dumps({"xml_presentation_id": PRES_ID}),
        )
    )
    xml = pres["data"]["xml_presentation"]["content"]
    mermaid_count = xml.count("<mermaid>")
    slide_count = xml.count('<slide id="')
    print(f"Slides: {slide_count}, Mermaid diagrams: {mermaid_count}")
    if mermaid_count < 4:
        print("Warning: expected at least 4 mermaid diagrams", file=sys.stderr)
        raise SystemExit(1)
    print("Done.")
    print(f"https://sukaduasukadotco.jp.larksuite.com/slides/{PRES_ID}")


if __name__ == "__main__":
    main()
