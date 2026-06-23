#!/usr/bin/env python3
"""Fix icons that Lark fell back to setting.svg with supported IconPark types."""
import json
import re
import subprocess

PRES = "X8UDs5FialThKwd8V1XjTXGipfg"

# block_id -> (slide_id, icon_type, color, x, y, size)
FIXES: dict[str, tuple[str, str, str, str, str, str]] = {
    "bvd": ("pla", "iconpark/Hardware/robot.svg", "rgba(0,151,167,1)", "115", "220", "28"),
    "bvJ": ("plu", "iconpark/Hardware/robot.svg", "rgba(0,151,167,1)", "78", "138", "32"),
    "bvB": ("plb", "iconpark/Peoples/peoples.svg", "rgba(0,151,167,1)", "150", "170", "56"),
    "bvD": ("plb", "iconpark/Peoples/peoples.svg", "rgba(0,151,167,1)", "150", "170", "56"),
    "bvR": ("ple", "iconpark/Peoples/peoples.svg", "rgba(0,151,167,1)", "85", "178", "28"),
    "bde": ("ple", "iconpark/Hardware/robot.svg", "rgba(0,151,167,1)", "390", "168", "28"),
    "bdc": ("plW", "iconpark/Hardware/robot.svg", "rgba(142,36,170,1)", "358", "138", "32"),
    "bdh": ("plE", "iconpark/Character/close-one.svg", "rgba(239,68,68,1)", "700", "420", "40"),
    "bdC": ("plw", "iconpark/Hardware/robot.svg", "rgba(0,151,167,1)", "85", "268", "28"),
    "bdY": ("ply", "iconpark/Character/close-one.svg", "rgba(239,68,68,1)", "78", "113", "32"),
    "bdI": ("plq", "iconpark/Hardware/robot.svg", "rgba(255,255,255,1)", "180", "420", "36"),
    "bPD": ("plq", "iconpark/Hardware/robot.svg", "rgba(255,255,255,1)", "430", "120", "80"),
}


def icon_xml(icon_type: str, x: str, y: str, size: str, color: str) -> str:
    return (
        f'<icon iconType="{icon_type}" topLeftX="{x}" topLeftY="{y}" width="{size}" height="{size}">'
        f'<fill><fillColor color="{color}"/></fill></icon>'
    )


def main() -> None:
    by_slide: dict[str, list[dict]] = {}
    for block_id, (slide_id, icon_type, color, x, y, size) in FIXES.items():
        by_slide.setdefault(slide_id, []).append(
            {
                "action": "block_replace",
                "block_id": block_id,
                "replacement": icon_xml(icon_type, x, y, size, color),
            }
        )

    for slide_id, parts in by_slide.items():
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

    pres = subprocess.run(
        [
            "lark-cli", "slides", "xml_presentations", "get", "--as", "user",
            "--params", json.dumps({"xml_presentation_id": PRES}),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    content = json.loads(pres.stdout)["data"]["xml_presentation"]["content"]
    settings = len(re.findall(r'iconType="iconpark/Base/setting\.svg"', content))
    icons = len(re.findall(r"<icon\b", content))
    print(f"Fixed setting fallbacks. icons={icons} setting_left={settings}")


if __name__ == "__main__":
    main()
