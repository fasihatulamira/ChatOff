#!/usr/bin/env python3
"""Add icons and screenshots to ChatOff Lark presentation."""
import json
import subprocess

PRES = "X8UDs5FialThKwd8V1XjTXGipfg"
TOKENS = {
    "chat": "TS42b9ogRosBhXxaVvSj85UCptb",
    "admin": "CZSObwEekoBExrxggwdjPOv7pMr",
    "sources": "E0UqbVARMoCqcjxr9HTjE0hIp3f",
}


def icon(x, y, size, icon_type, color=None):
    c = f' color="{color}"' if color else ""
    return f'<icon iconType="{icon_type}" topLeftX="{x}" topLeftY="{y}" width="{size}" height="{size}"{c}/>'


def img(token, x, y, w, h):
    return f'<img src="{token}" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}"/>'


def run(slide_id, parts):
    proc = subprocess.run(
        [
            "lark-cli", "slides", "+replace-slide", "--as", "user",
            "--presentation", PRES,
            "--slide-id", slide_id,
            "--parts", json.dumps(parts),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"FAIL {slide_id}: {proc.stderr[:300]}")
        return False
    data = json.loads(proc.stdout)
    print(f"OK {slide_id}: {data['data']['parts_count']} parts")
    return True


ENHANCEMENTS = {
    "pll": [
        {"action": "block_insert", "insertion": icon(780, 80, 100, "iconpark/Hardware/laptop-computer.svg", "rgba(255,255,255,0.35)")},
        {"action": "block_insert", "insertion": icon(700, 200, 64, "iconpark/Office/file-pdf-one.svg", "rgba(255,255,255,0.4)")},
        {"action": "block_insert", "insertion": icon(860, 220, 56, "iconpark/Datas/database-code.svg", "rgba(255,255,255,0.4)")},
        {"action": "block_insert", "insertion": icon(820, 340, 48, "iconpark/Abstract/circular-connection.svg", "rgba(255,255,255,0.3)")},
        {"action": "block_insert", "insertion": '<shape type="circle" topLeftX="650" topLeftY="60" width="180" height="180"><fill><fillColor color="rgba(255,255,255,0.06)"/></fill><content/></shape>'},
    ],
    "pla": [
        {"action": "block_insert", "insertion": icon(115, 152, 22, "iconpark/Others/thinking-problem.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(115, 186, 22, "iconpark/Sports/target-one.svg", "rgba(142,36,170,1)")},
        {"action": "block_insert", "insertion": icon(115, 220, 22, "iconpark/Hardware/robot-one.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(115, 254, 22, "iconpark/Peoples/data-user.svg", "rgba(37,99,235,1)")},
        {"action": "block_insert", "insertion": icon(115, 288, 22, "iconpark/Abstract/api-app.svg", "rgba(16,185,129,1)")},
        {"action": "block_insert", "insertion": icon(115, 322, 22, "iconpark/Charts/chart-graph.svg", "rgba(245,158,11,1)")},
        {"action": "block_insert", "insertion": icon(115, 356, 22, "iconpark/Datas/database-code.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(115, 390, 22, "iconpark/Character/check-one.svg", "rgba(16,185,129,1)")},
        {"action": "block_insert", "insertion": icon(115, 424, 22, "iconpark/Communicate/message-security.svg", "rgba(239,68,68,1)")},
    ],
    "plk": [
        {"action": "block_insert", "insertion": icon(78, 188, 36, "iconpark/Others/thinking-problem.svg", "rgba(239,68,68,1)")},
        {"action": "block_insert", "insertion": icon(358, 188, 36, "iconpark/Charts/chart-histogram.svg", "rgba(245,158,11,1)")},
        {"action": "block_insert", "insertion": icon(638, 188, 36, "iconpark/Communicate/message-security.svg", "rgba(142,36,170,1)")},
        {"action": "block_insert", "insertion": icon(820, 120, 48, "iconpark/Datas/database-alert.svg", "rgba(0,151,167,0.5)")},
    ],
    "plu": [
        {"action": "block_insert", "insertion": icon(78, 138, 32, "iconpark/Hardware/robot-one.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(298, 138, 32, "iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,1)")},
        {"action": "block_insert", "insertion": icon(518, 138, 32, "iconpark/Base/aiming.svg", "rgba(37,99,235,1)")},
        {"action": "block_insert", "insertion": icon(738, 138, 32, "iconpark/Charts/chart-histogram.svg", "rgba(16,185,129,1)")},
        {"action": "block_insert", "insertion": icon(880, 300, 56, "iconpark/Sports/target-one.svg", "rgba(255,255,255,0.25)")},
    ],
    "plb": [
        {"action": "block_insert", "insertion": img(TOKENS["chat"], 600, 355, 320, 155)},
        {"action": "block_insert", "insertion": '<shape type="text" topLeftX="600" topLeftY="512" width="320" height="22"><content textType="caption" fontSize="10" color="rgba(71,85,105,1)" textAlign="center"><p>Real ChatOff user interface</p></content></shape>'},
        {"action": "block_insert", "insertion": icon(150, 170, 56, "iconpark/Peoples/data-user.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(452, 235, 56, "iconpark/Hardware/laptop-computer.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(745, 165, 48, "iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,1)")},
        {"action": "block_insert", "insertion": icon(745, 335, 48, "iconpark/Datas/database-code.svg", "rgba(0,151,167,1)")},
    ],
    "ple": [
        {"action": "block_insert", "insertion": icon(85, 178, 28, "iconpark/Peoples/data-user.svg", "rgba(255,255,255,1)")},
        {"action": "block_insert", "insertion": icon(85, 268, 28, "iconpark/Datas/data-user.svg", "rgba(255,255,255,1)")},
        {"action": "block_insert", "insertion": icon(220, 168, 24, "iconpark/Character/check-one.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(390, 168, 24, "iconpark/Hardware/robot-one.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(560, 168, 24, "iconpark/Base/more-app.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(730, 168, 24, "iconpark/Charts/chart-line.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(220, 223, 24, "iconpark/Office/file-pdf-one.svg", "rgba(245,158,11,1)")},
        {"action": "block_insert", "insertion": icon(390, 223, 24, "iconpark/Edit/magic-wand.svg", "rgba(245,158,11,1)")},
    ],
    "plW": [
        {"action": "block_insert", "insertion": icon(78, 138, 28, "iconpark/Hardware/laptop-computer.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(358, 138, 28, "iconpark/Hardware/robot-one.svg", "rgba(142,36,170,1)")},
        {"action": "block_insert", "insertion": icon(638, 138, 28, "iconpark/Office/file-pdf-one.svg", "rgba(37,99,235,1)")},
        {"action": "block_insert", "insertion": icon(78, 318, 28, "iconpark/Datas/database-code.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(358, 318, 28, "iconpark/Office/file-lock-one.svg", "rgba(239,68,68,1)")},
        {"action": "block_insert", "insertion": icon(638, 318, 28, "iconpark/Abstract/api-app.svg", "rgba(16,185,129,1)")},
    ],
    "plE": [
        {"action": "block_insert", "insertion": icon(100, 300, 40, "iconpark/Character/check-one.svg", "rgba(16,185,129,0.8)")},
        {"action": "block_insert", "insertion": icon(600, 300, 40, "iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,0.8)")},
        {"action": "block_insert", "insertion": icon(410, 420, 40, "iconpark/Hands/thumbs-up.svg", "rgba(16,185,129,0.8)")},
        {"action": "block_insert", "insertion": icon(700, 420, 40, "iconpark/Datas/database-alert.svg", "rgba(239,68,68,0.8)")},
        {"action": "block_insert", "insertion": icon(850, 120, 56, "iconpark/Abstract/circular-connection.svg", "rgba(0,151,167,0.4)")},
    ],
    "pli": [
        {"action": "block_insert", "insertion": icon(78, 133, 32, "iconpark/Datas/database-code.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(508, 133, 32, "iconpark/Office/file-pdf-one.svg", "rgba(142,36,170,1)")},
        {"action": "block_insert", "insertion": icon(78, 338, 32, "iconpark/Abstract/rectangular-circular-connection.svg", "rgba(37,99,235,1)")},
    ],
    "plw": [
        {"action": "block_insert", "insertion": img(TOKENS["chat"], 75, 118, 370, 130)},
        {"action": "block_insert", "insertion": img(TOKENS["admin"], 515, 118, 370, 130)},
        {"action": "block_insert", "insertion": '<shape type="text" topLeftX="75" topLeftY="250" width="370" height="20"><content textType="caption" fontSize="10" color="rgba(0,151,167,1)" textAlign="center"><p>User chat screen</p></content></shape>'},
        {"action": "block_insert", "insertion": '<shape type="text" topLeftX="515" topLeftY="250" width="370" height="20"><content textType="caption" fontSize="10" color="rgba(142,36,170,1)" textAlign="center"><p>Admin Topic Builder</p></content></shape>'},
        {"action": "block_insert", "insertion": img(TOKENS["sources"], 220, 395, 520, 120)},
        {"action": "block_insert", "insertion": '<shape type="text" topLeftX="220" topLeftY="518" width="520" height="18"><content textType="caption" fontSize="10" color="rgba(71,85,105,1)" textAlign="center"><p>PDF source citations with confidence score</p></content></shape>'},
        {"action": "block_insert", "insertion": icon(85, 268, 22, "iconpark/Hardware/robot-one.svg", "rgba(0,151,167,1)")},
        {"action": "block_insert", "insertion": icon(525, 268, 22, "iconpark/Edit/magic-wand.svg", "rgba(142,36,170,1)")},
    ],
    "ply": [
        {"action": "block_insert", "insertion": icon(78, 113, 28, "iconpark/Datas/database-alert.svg", "rgba(239,68,68,1)")},
        {"action": "block_insert", "insertion": icon(508, 113, 28, "iconpark/Hands/thumbs-up.svg", "rgba(16,185,129,1)")},
        {"action": "block_insert", "insertion": icon(880, 100, 48, "iconpark/Sports/target-two.svg", "rgba(16,185,129,0.35)")},
    ],
    "plq": [
        {"action": "block_insert", "insertion": icon(100, 130, 52, "iconpark/Hands/thumbs-up.svg", "rgba(255,255,255,0.55)")},
        {"action": "block_insert", "insertion": icon(808, 130, 52, "iconpark/Character/check-one.svg", "rgba(255,255,255,0.55)")},
        {"action": "block_insert", "insertion": img(TOKENS["chat"], 40, 60, 200, 110)},
        {"action": "block_insert", "insertion": img(TOKENS["admin"], 720, 60, 200, 110)},
        {"action": "block_insert", "insertion": icon(180, 420, 36, "iconpark/Hardware/robot-one.svg", "rgba(255,255,255,0.35)")},
        {"action": "block_insert", "insertion": icon(744, 420, 36, "iconpark/Office/file-pdf-one.svg", "rgba(255,255,255,0.35)")},
        {"action": "block_insert", "insertion": icon(460, 175, 40, "iconpark/Edit/magic-wand.svg", "rgba(255,255,255,0.3)")},
    ],
}


def main():
    for slide_id, parts in ENHANCEMENTS.items():
        run(slide_id, parts)
    print("Done.")


if __name__ == "__main__":
    main()
