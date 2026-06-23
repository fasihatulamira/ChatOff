#!/usr/bin/env python3
"""
Recolor all icons by replacing <icon> with colored emoji text shapes.

Also removes any screenshot-like content if present (none in XML currently),
by replacing <img> blocks if they exist.
"""
import json
import re
import subprocess

PRES = "X8UDs5FialThKwd8V1XjTXGipfg"

COLOR = {
    "teal": "rgba(0,151,167,1)",
    "purple": "rgba(142,36,170,1)",
    "blue": "rgba(37,99,235,1)",
    "green": "rgba(16,185,129,1)",
    "red": "rgba(239,68,68,1)",
    "amber": "rgba(245,158,11,1)",
    "dark": "rgba(15,23,42,1)",
    "white": "rgba(255,255,255,1)",
}


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'{name}="([^"]+)"', tag)
    return m.group(1) if m else None


def emoji_for(icon_type: str) -> tuple[str, str]:
    """Return (emoji, color)."""
    t = (icon_type or "").lower()
    if "file-pdf" in t or "pdf" in t or "file" in t:
        return "📄", COLOR["purple"]
    if "database" in t or "data" in t:
        return "🗄️", COLOR["teal"]
    if "lock" in t or "security" in t:
        return "🔒", COLOR["red"]
    if "warning" in t or "alert" in t or "problem" in t:
        return "⚠️", COLOR["amber"]
    if "robot" in t:
        return "🤖", COLOR["teal"]
    if "chart" in t:
        return "📊", COLOR["blue"]
    if "thumb" in t or "check" in t:
        return "✅", COLOR["green"]
    if "target" in t or "aim" in t or "flag" in t:
        return "🎯", COLOR["purple"]
    if "connection" in t or "api" in t:
        return "🔗", COLOR["blue"]
    if "laptop" in t or "computer" in t:
        return "💻", COLOR["teal"]
    return "✨", COLOR["purple"]


def text_emoji_shape(x, y, w, h, emoji: str, color: str) -> str:
    # Centered emoji; fontSize tuned to fit the icon box.
    size = max(14, min(44, int(min(float(w), float(h)) * 0.9)))
    return (
        f'<shape type="text" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
        f'<content textType="headline" fontSize="{size}" color="{color}" textAlign="center">'
        f"<p>{emoji}</p></content></shape>"
    )


def replace_parts(slide_id: str, parts: list[dict]) -> None:
    if not parts:
        return
    proc = subprocess.run(
        [
            "lark-cli",
            "slides",
            "+replace-slide",
            "--as",
            "user",
            "--presentation",
            PRES,
            "--slide-id",
            slide_id,
            "--parts",
            json.dumps(parts),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr)


def main() -> None:
    pres = subprocess.run(
        [
            "lark-cli",
            "slides",
            "xml_presentations",
            "get",
            "--as",
            "user",
            "--params",
            json.dumps({"xml_presentation_id": PRES}),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    content = json.loads(pres.stdout)["data"]["xml_presentation"]["content"]
    slides = re.findall(r'<slide id="([^"]+)">(.*?)</slide>', content, re.S)

    # Collect icon replacements per slide (parts limit: 200).
    for slide_id, body in slides:
        parts: list[dict] = []

        # Replace all <icon .../> with a colored emoji shape.
        for m in re.finditer(r"<icon\s+[^>]*/>", body):
            tag = m.group(0)
            bid = _attr(tag, "id")
            icon_type = _attr(tag, "iconType") or ""
            x = _attr(tag, "topLeftX") or "0"
            y = _attr(tag, "topLeftY") or "0"
            w = _attr(tag, "width") or "32"
            h = _attr(tag, "height") or "32"
            if not bid:
                continue
            em, col = emoji_for(icon_type)
            parts.append(
                {
                    "action": "block_replace",
                    "block_id": bid,
                    "replacement": text_emoji_shape(x, y, w, h, em, col),
                }
            )

        # If any <img .../> exists, replace it with a clean card (remove screenshots).
        for m in re.finditer(r"<img\s+[^>]*/>", body):
            tag = m.group(0)
            bid = _attr(tag, "id")
            x = _attr(tag, "topLeftX") or "0"
            y = _attr(tag, "topLeftY") or "0"
            w = _attr(tag, "width") or "300"
            h = _attr(tag, "height") or "160"
            if not bid:
                continue
            parts.append(
                {
                    "action": "block_replace",
                    "block_id": bid,
                    "replacement": (
                        f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}">'
                        f'<fill><fillColor color="rgba(226,232,240,1)"/></fill><content/></shape>'
                    ),
                }
            )

        # Apply in batches (safety).
        while parts:
            batch, parts = parts[:180], parts[180:]
            replace_parts(slide_id, batch)


if __name__ == "__main__":
    main()

