#!/usr/bin/env python3
"""Replace emoji text shapes with colored IconPark graphic icons."""
import json
import re
import subprocess

PRES = "X8UDs5FialThKwd8V1XjTXGipfg"

# (slide_id, x, y) -> (icon_type, fill_color, size)
ICON_BY_POSITION: dict[tuple[str, str, str], tuple[str, str, str]] = {
    # Cover
    ("pll", "80", "120"): ("iconpark/Hardware/robot.svg", "rgba(255,255,255,1)", "80"),
    ("pll", "780", "80"): ("iconpark/Hardware/laptop-computer.svg", "rgba(255,255,255,1)", "100"),
    ("pll", "700", "200"): ("iconpark/Office/file-pdf-one.svg", "rgba(255,255,255,1)", "64"),
    ("pll", "860", "220"): ("iconpark/Datas/database-code.svg", "rgba(255,255,255,1)", "56"),
    ("pll", "820", "340"): ("iconpark/Abstract/circular-connection.svg", "rgba(255,255,255,1)", "48"),
    # Agenda
    ("pla", "115", "152"): ("iconpark/Others/thinking-problem.svg", "rgba(0,151,167,1)", "28"),
    ("pla", "115", "186"): ("iconpark/Sports/target-one.svg", "rgba(142,36,170,1)", "28"),
    ("pla", "115", "220"): ("iconpark/Hardware/robot.svg", "rgba(0,151,167,1)", "28"),
    ("pla", "115", "254"): ("iconpark/Peoples/peoples.svg", "rgba(37,99,235,1)", "28"),
    ("pla", "115", "288"): ("iconpark/Abstract/api-app.svg", "rgba(16,185,129,1)", "28"),
    ("pla", "115", "322"): ("iconpark/Charts/chart-graph.svg", "rgba(245,158,11,1)", "28"),
    ("pla", "115", "356"): ("iconpark/Datas/database-code.svg", "rgba(0,151,167,1)", "28"),
    ("pla", "115", "390"): ("iconpark/Character/check-one.svg", "rgba(16,185,129,1)", "28"),
    ("pla", "115", "424"): ("iconpark/Communicate/message-security.svg", "rgba(239,68,68,1)", "28"),
    # Problem
    ("plk", "78", "188"): ("iconpark/Others/thinking-problem.svg", "rgba(239,68,68,1)", "36"),
    ("plk", "358", "188"): ("iconpark/Charts/chart-histogram.svg", "rgba(245,158,11,1)", "36"),
    ("plk", "638", "188"): ("iconpark/Communicate/message-security.svg", "rgba(142,36,170,1)", "36"),
    ("plk", "820", "120"): ("iconpark/Character/close-one.svg", "rgba(0,151,167,1)", "48"),
    # Objectives
    ("plu", "78", "138"): ("iconpark/Hardware/robot.svg", "rgba(0,151,167,1)", "32"),
    ("plu", "298", "138"): ("iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,1)", "32"),
    ("plu", "518", "138"): ("iconpark/Base/aiming.svg", "rgba(37,99,235,1)", "32"),
    ("plu", "738", "138"): ("iconpark/Charts/chart-histogram.svg", "rgba(16,185,129,1)", "32"),
    ("plu", "880", "300"): ("iconpark/Sports/target-one.svg", "rgba(142,36,170,1)", "56"),
    # Solution
    ("plb", "150", "170"): ("iconpark/Peoples/peoples.svg", "rgba(0,151,167,1)", "56"),
    ("plb", "452", "235"): ("iconpark/Hardware/laptop-computer.svg", "rgba(0,151,167,1)", "56"),
    ("plb", "745", "165"): ("iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,1)", "48"),
    ("plb", "745", "335"): ("iconpark/Datas/database-code.svg", "rgba(0,151,167,1)", "48"),
    # Use case
    ("ple", "85", "178"): ("iconpark/Peoples/peoples.svg", "rgba(0,151,167,1)", "28"),
    ("ple", "85", "268"): ("iconpark/Datas/data-user.svg", "rgba(142,36,170,1)", "28"),
    ("ple", "220", "168"): ("iconpark/Character/check-one.svg", "rgba(0,151,167,1)", "28"),
    ("ple", "390", "168"): ("iconpark/Hardware/robot.svg", "rgba(0,151,167,1)", "28"),
    ("ple", "560", "168"): ("iconpark/Base/more-app.svg", "rgba(37,99,235,1)", "28"),
    ("ple", "730", "168"): ("iconpark/Charts/chart-line.svg", "rgba(16,185,129,1)", "28"),
    ("ple", "220", "223"): ("iconpark/Office/file-pdf-one.svg", "rgba(245,158,11,1)", "28"),
    ("ple", "390", "223"): ("iconpark/Edit/magic-wand.svg", "rgba(142,36,170,1)", "28"),
    # Tech stack
    ("plW", "78", "138"): ("iconpark/Hardware/laptop-computer.svg", "rgba(0,151,167,1)", "32"),
    ("plW", "358", "138"): ("iconpark/Hardware/robot.svg", "rgba(142,36,170,1)", "32"),
    ("plW", "638", "138"): ("iconpark/Office/file-pdf-one.svg", "rgba(37,99,235,1)", "32"),
    ("plW", "78", "318"): ("iconpark/Datas/database-code.svg", "rgba(0,151,167,1)", "32"),
    ("plW", "358", "318"): ("iconpark/Office/file-lock-one.svg", "rgba(239,68,68,1)", "32"),
    ("plW", "638", "318"): ("iconpark/Abstract/api-app.svg", "rgba(16,185,129,1)", "32"),
    # Workflow
    ("plE", "100", "300"): ("iconpark/Character/check-one.svg", "rgba(16,185,129,1)", "40"),
    ("plE", "600", "300"): ("iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,1)", "40"),
    ("plE", "410", "420"): ("iconpark/Hands/thumbs-up.svg", "rgba(16,185,129,1)", "40"),
    ("plE", "700", "420"): ("iconpark/Character/close-one.svg", "rgba(239,68,68,1)", "40"),
    ("plE", "850", "120"): ("iconpark/Abstract/circular-connection.svg", "rgba(0,151,167,1)", "56"),
    # Database
    ("pli", "78", "133"): ("iconpark/Datas/database-code.svg", "rgba(0,151,167,1)", "32"),
    ("pli", "508", "133"): ("iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,1)", "32"),
    ("pli", "78", "338"): ("iconpark/Abstract/rectangular-circular-connection.svg", "rgba(37,99,235,1)", "32"),
    # Features
    ("plw", "85", "268"): ("iconpark/Hardware/robot.svg", "rgba(0,151,167,1)", "28"),
    ("plw", "525", "268"): ("iconpark/Edit/magic-wand.svg", "rgba(142,36,170,1)", "28"),
    # Limitations
    ("ply", "78", "113"): ("iconpark/Character/close-one.svg", "rgba(239,68,68,1)", "32"),
    ("ply", "508", "113"): ("iconpark/Hands/thumbs-up.svg", "rgba(16,185,129,1)", "32"),
    ("ply", "880", "100"): ("iconpark/Sports/target-two.svg", "rgba(16,185,129,1)", "48"),
    # Thank you
    ("plq", "100", "130"): ("iconpark/Hands/thumbs-up.svg", "rgba(255,255,255,1)", "52"),
    ("plq", "808", "130"): ("iconpark/Character/check-one.svg", "rgba(255,255,255,1)", "52"),
    ("plq", "180", "420"): ("iconpark/Hardware/robot.svg", "rgba(255,255,255,1)", "36"),
    ("plq", "744", "420"): ("iconpark/Office/file-pdf-one.svg", "rgba(255,255,255,1)", "36"),
    ("plq", "460", "175"): ("iconpark/Edit/magic-wand.svg", "rgba(255,255,255,1)", "40"),
    ("plq", "430", "120"): ("iconpark/Hardware/robot.svg", "rgba(255,255,255,1)", "80"),
}

EMOJI_FALLBACK = {
    "🤖": ("iconpark/Hardware/robot.svg", "rgba(0,151,167,1)"),
    "📄": ("iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,1)"),
    "🗄️": ("iconpark/Datas/database-code.svg", "rgba(0,151,167,1)"),
    "🔒": ("iconpark/Communicate/message-security.svg", "rgba(239,68,68,1)"),
    "⚠️": ("iconpark/Others/thinking-problem.svg", "rgba(245,158,11,1)"),
    "📊": ("iconpark/Charts/chart-histogram.svg", "rgba(37,99,235,1)"),
    "✅": ("iconpark/Character/check-one.svg", "rgba(16,185,129,1)"),
    "🎯": ("iconpark/Sports/target-one.svg", "rgba(142,36,170,1)"),
    "🔗": ("iconpark/Abstract/circular-connection.svg", "rgba(37,99,235,1)"),
    "💻": ("iconpark/Hardware/laptop-computer.svg", "rgba(0,151,167,1)"),
    "✨": ("iconpark/Edit/magic-wand.svg", "rgba(142,36,170,1)"),
}


def graphic_icon(x: str, y: str, w: str, h: str, icon_type: str, color: str) -> str:
    size = max(int(float(w)), int(float(h)), 28)
    return (
        f'<icon iconType="{icon_type}" topLeftX="{x}" topLeftY="{y}" width="{size}" height="{size}">'
        f"<fill><fillColor color=\"{color}\"/></fill></icon>"
    )


def replace_parts(slide_id: str, parts: list[dict]) -> None:
    proc = subprocess.run(
        [
            "lark-cli", "slides", "+replace-slide", "--as", "user",
            "--presentation", PRES, "--slide-id", slide_id,
            "--parts", json.dumps(parts),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{slide_id}: {proc.stderr}")


def main() -> None:
    pres = subprocess.run(
        [
            "lark-cli", "slides", "xml_presentations", "get", "--as", "user",
            "--params", json.dumps({"xml_presentation_id": PRES}),
        ],
        capture_output=True, text=True, check=True,
    )
    content = json.loads(pres.stdout)["data"]["xml_presentation"]["content"]
    slides = re.findall(r'<slide id="([^"]+)">(.*?)</slide>', content, re.S)

    total = 0
    for slide_id, body in slides:
        parts: list[dict] = []
        for m in re.finditer(r'<shape\s+[^>]*type="text"[^>]*>.*?</shape>', body, re.S):
            tag = m.group(0)
            head = tag.split(">", 1)[0] + ">"
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', head))
            pm = re.search(r"<p>([^<]+)</p>", tag)
            if not pm:
                continue
            text = pm.group(1)
            if not any(ord(ch) > 127 for ch in text) or len(text) > 4:
                continue
            bid = attrs.get("id")
            x, y, w, h = attrs.get("topLeftX", "0"), attrs.get("topLeftY", "0"), attrs.get("width", "32"), attrs.get("height", "32")
            if not bid:
                continue
            key = (slide_id, x, y)
            if key in ICON_BY_POSITION:
                icon_type, color, size = ICON_BY_POSITION[key]
                replacement = graphic_icon(x, y, size, size, icon_type, color)
            else:
                icon_type, color = EMOJI_FALLBACK.get(text, ("iconpark/Edit/magic-wand.svg", "rgba(142,36,170,1)"))
                replacement = graphic_icon(x, y, w, h, icon_type, color)
            parts.append({"action": "block_replace", "block_id": bid, "replacement": replacement})
            total += 1

        while parts:
            batch, parts = parts[:180], parts[180:]
            replace_parts(slide_id, batch)

    print(f"Replaced {total} emoji icons with graphic IconPark icons.")


if __name__ == "__main__":
    main()
