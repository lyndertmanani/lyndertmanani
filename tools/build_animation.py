"""Render the contribution calendar with a GitHub Pac-Man eating it, chased by Copilot icons.

Fetches the last year of contributions through the GraphQL API and writes
contrib_dark.svg / contrib_light.svg. As the icon eats each square the
"remaining" counter drops by that day's contribution count.

Needs GITHUB_TOKEN in the environment. LOGIN defaults to the repo owner.
"""
import json
import random
from collections import deque
import os
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGIN = os.environ.get("LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "lyndertmanani"
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount contributionLevel date weekday } }
      }
    }
  }
}
"""

COPILOT_PATH = (
    "M23.922 16.997C23.061 18.492 18.063 22.02 12 22.02S.939 18.492.078 16.997A.6.6 0 0 1 0 16.741v-2.869a1 1 0 0 1 .053-.22c.372-.935 1.347-2.292 2.605-2.656c.167-.429.414-1.055.644-1.517a10 10 0 0 1-.052-1.086c0-1.331.282-2.499 1.132-3.368c.397-.406.89-.717 1.474-.952C7.255 2.937 9.248 1.98 11.978 1.98s4.767.957 6.166 2.093c.584.235 1.077.546 1.474.952c.85.869 1.132 2.037 1.132 3.368c0 .368-.014.733-.052 1.086c.23.462.477 1.088.644 1.517c1.258.364 2.233 1.721 2.605 2.656a.8.8 0 0 1 .053.22v2.869a.6.6 0 0 1-.078.256m-11.75-5.992h-.344a4 4 0 0 1-.355.508c-.77.947-1.918 1.492-3.508 1.492c-1.725 0-2.989-.359-3.782-1.259a2 2 0 0 1-.085-.104L4 11.746v6.585c1.435.779 4.514 2.179 8 2.179s6.565-1.4 8-2.179v-6.585l-.098-.104s-.033.045-.085.104c-.793.9-2.057 1.259-3.782 1.259c-1.59 0-2.738-.545-3.508-1.492a4 4 0 0 1-.355-.508m2.328 3.25c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1s-1-.451-1-1v-2c0-.549.451-1 1-1m-5 0c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1s-1-.451-1-1v-2c0-.549.451-1 1-1m3.313-6.185c.136 1.057.403 1.913.878 2.497c.442.544 1.134.938 2.344.938c1.573 0 2.292-.337 2.657-.751c.384-.435.558-1.15.558-2.361c0-1.14-.243-1.847-.705-2.319c-.477-.488-1.319-.862-2.824-1.025c-1.487-.161-2.192.138-2.533.529c-.269.307-.437.808-.438 1.578v.021q0 .397.063.893m-1.626 0q.063-.496.063-.894v-.02c-.001-.77-.169-1.271-.438-1.578c-.341-.391-1.046-.69-2.533-.529c-1.505.163-2.347.537-2.824 1.025c-.462.472-.705 1.179-.705 2.319c0 1.211.175 1.926.558 2.361c.365.414 1.084.751 2.657.751c1.21 0 1.902-.394 2.344-.938c.475-.584.742-1.44.878-2.497"
)

LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

THEMES = {
    "dark": {
        "text": "#c9d1d9", "pac": "#e3b341", "ghosts": ["#a371f7", "#58a6ff", "#f778ba"],
        "muted": "#8b949e", "accent": "#a371f7",
        "cells": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
    },
    "light": {
        "text": "#24292f", "pac": "#bf8700", "ghosts": ["#8250df", "#0969da", "#bf3989"],
        "muted": "#6e7781", "accent": "#8250df",
        "cells": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    },
}

CELL, GAP = 11, 3
PITCH = CELL + GAP
LEFT, TOP = 36, 28
STEP_SECONDS = 0.1
PAD = 15
TAIL = 16
LAGS = (5, 8, 11)
CLAUDE_PATH = "M20.998 10.949H24v3.102h-3v3.028h-1.487V20H18v-2.921h-1.487V20H15v-2.921H9V20H7.488v-2.921H6V20H4.487v-2.921H3V14.05H0v-3.1h3V5h17.998zM6 10.949h1.488V8.102H6zm10.51 0H18V8.102h-1.49z"
OPENAI_PATH = "M20.557 10.634a5.07 5.07 0 0 0-.42-4.099c-1.087-1.901-3.284-2.864-5.432-2.42c-.939-1.061-2.321-1.654-3.754-1.654a5.07 5.07 0 0 0-4.814 3.481a5 5 0 0 0-3.334 2.42a5.07 5.07 0 0 0 .618 5.901a5.06 5.06 0 0 0 .444 4.1a5.025 5.025 0 0 0 5.432 2.419a5.07 5.07 0 0 0 3.753 1.679a5.07 5.07 0 0 0 4.815-3.481a5 5 0 0 0 3.333-2.42a5.07 5.07 0 0 0-.642-5.926M13.05 21.152a3.66 3.66 0 0 1-2.395-.864c.025-.025.099-.05.124-.074l3.975-2.296a.65.65 0 0 0 .321-.568v-5.605l1.679.963c.025 0 .025.024.025.05v4.641a3.716 3.716 0 0 1-3.729 3.753M5 17.72c-.444-.765-.592-1.654-.444-2.518c.025.024.075.05.124.074l3.975 2.296a.6.6 0 0 0 .642 0l4.864-2.815v1.95c0 .026 0 .05-.024.05l-4.025 2.321c-1.778 1.037-4.074.42-5.111-1.358M3.965 9.03a3.88 3.88 0 0 1 1.95-1.654v4.74c0 .223.124.445.321.568l4.865 2.815l-1.68.963c-.024 0-.049.025-.049 0L5.347 14.14a3.714 3.714 0 0 1-1.383-5.111m13.827 3.21l-4.864-2.815l1.679-.963c.024 0 .05-.025.05 0l4.024 2.32a3.727 3.727 0 0 1 1.358 5.112a3.72 3.72 0 0 1-1.95 1.63v-4.716a.61.61 0 0 0-.297-.568m1.654-2.519a.5.5 0 0 0-.123-.074L15.347 7.35a.6.6 0 0 0-.642 0L9.84 10.165V8.214c0-.025 0-.05.025-.05l4.025-2.32A3.73 3.73 0 0 1 19 7.226c.445.741.593 1.63.445 2.494M8.927 13.177l-1.68-.963c-.024 0-.024-.025-.024-.05v-4.64a3.75 3.75 0 0 1 3.753-3.753a3.66 3.66 0 0 1 2.395.864a.5.5 0 0 1-.123.074L9.273 7.004a.65.65 0 0 0-.321.568v5.605zm.913-1.975l2.173-1.26l2.173 1.26v2.493l-2.173 1.26l-2.173-1.26z"
PAUSE_SECONDS = 3.0
RESET = 0.985


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "contrib-animation"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(json.dumps(payload["errors"], indent=2))
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def eating_order(weeks):
    """Cells column by column, alternating direction, as (week, row, count, level, date)."""
    order = []
    for w, week in enumerate(weeks):
        days = sorted(week["contributionDays"], key=lambda d: d["weekday"])
        if w % 2:
            days.reverse()
        for d in days:
            order.append((w, d["weekday"], d["contributionCount"], LEVELS.index(d["contributionLevel"]), d["date"]))
    return order


def plan_path(order, weeks):
    """Classic Pac-Man sweep: row by row, left to right then back, stepping down at each edge."""
    valid = {(w, r) for (w, r, *_rest) in order}
    path = []
    for row in range(7):
        cols = range(weeks) if row % 2 == 0 else range(weeks - 1, -1, -1)
        path += [(c, row) for c in cols]
    eaten = {cell: PAD + k for k, cell in enumerate(path) if cell in valid}
    return path, eaten

def kt(value):
    return f"{min(max(value, 0.0), 1.0):.4f}"


def render(calendar, theme_name):
    t = THEMES[theme_name]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    order = eating_order(weeks)
    path, eaten = plan_path(order, len(weeks))
    n = len(path)
    move = n * STEP_SECONDS
    dur = move + PAUSE_SECONDS
    frac = move / dur

    width = LEFT + len(weeks) * PITCH + 14
    height = TOP + 7 * PITCH + 62

    def at(i):
        return max(i / (n - 1) * frac, 0.0001)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        "<style>text{white-space:pre}.m{fill:%s;font-size:10px}.p{fill:%s;font-size:12px}.n{fill:%s;font-size:14px;font-weight:bold}</style>"
        % (t["muted"], t["text"], t["accent"]),
    ]

    last_month, last_x = None, -100
    for w, week in enumerate(weeks):
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        x = LEFT + w * PITCH
        if first.month != last_month and x - last_x >= 3 * PITCH:
            out.append(f'<text x="{x}" y="{TOP - 8}" class="m">{first.strftime("%b")}</text>')
            last_month, last_x = first.month, x
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="8" y="{TOP + row * PITCH + CELL - 1}" class="m">{label}</text>')

    for i, (w, row, count, level, day) in enumerate(order):
        x, y = LEFT + w * PITCH, TOP + row * PITCH
        base, empty = t["cells"][level], t["cells"][0]
        title = f"{count} contributions on {day}"
        if level == 0:
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{empty}"><title>{title}</title></rect>')
            continue
        out.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{base}"><title>{title}</title>'
            f'<animate attributeName="fill" calcMode="discrete" dur="{dur:.2f}s" repeatCount="indefinite" '
            f'values="{base};{empty};{base}" keyTimes="0;{kt(at(eaten[(w, row)]))};{RESET}"/></rect>'
        )

    def cell_at(idx):
        if idx < 0:
            return path[0][0] + idx, path[0][1]
        if idx >= len(path):
            return path[-1][0] + idx - len(path) + 1, path[-1][1]
        return path[idx]

    def xy(idx):
        c, r = cell_at(idx)
        return LEFT + c * PITCH + CELL / 2, TOP + r * PITCH + CELL / 2

    keytimes = ";".join(kt(i / (n - 1) * frac) for i in range(n)) + ";1"

    def track(lag, dx, dy):
        pts = [xy(max(i - PAD, 0) - lag) for i in range(n)]
        pts.append(pts[-1])
        return ";".join(f"{x + dx:.1f} {y + dy:.1f}" for x, y in pts)

    def move(values):
        return (
            f'<animateTransform attributeName="transform" type="translate" calcMode="linear" '
            f'dur="{dur:.2f}s" repeatCount="indefinite" values="{values}" keyTimes="{keytimes}"/>'
        )

    chasers = [(CLAUDE_PATH, "#d97757"), (COPILOT_PATH, t["accent"]), (OPENAI_PATH, t["text"])]
    for k, (d_attr, color) in reversed(list(enumerate(chasers))):
        stride = (0.34, 0.30, 0.38)[k]
        out.append(
            f'<g>{move(track(LAGS[k], 0, 0))}<g>'
            f'<animateTransform attributeName="transform" type="translate" dur="{stride}s" repeatCount="indefinite" '
            f'values="-8 -8;-8 -10.5;-8 -8"/>'
            f'<path d="{d_attr}" fill="{color}" transform="scale(0.6667)"/></g></g>'
        )
    angles = []
    for i in range(n):
        (x1, y1), (x2, y2) = xy(max(i - PAD, 0)), xy(max(i - PAD, 0) + 1)
        angles.append(0 if x2 > x1 else 180 if x2 < x1 else 90)
    angles.append(angles[-1])
    rot = ";".join(f"{a} 0 0" for a in angles)
    r = 7
    open_d = f"M0 0L{r * 0.766:.2f} {-r * 0.643:.2f}A{r} {r} 0 1 0 {r * 0.766:.2f} {r * 0.643:.2f}Z"
    shut_d = f"M0 0L{r:.2f} {-0.3}A{r} {r} 0 1 0 {r:.2f} {0.3}Z"
    out.append(
        f'<g>{move(track(0, 0, 0))}'
        f'<g><animateTransform attributeName="transform" type="rotate" calcMode="discrete" '
        f'dur="{dur:.2f}s" repeatCount="indefinite" values="{rot}" keyTimes="{keytimes}"/>'
        f'<path d="{open_d}" fill="{t["pac"]}">'
        f'<animate attributeName="d" dur="0.24s" repeatCount="indefinite" values="{open_d};{shut_d};{open_d}"/></path></g></g>'
    )
    fy = TOP + 7 * PITCH + 30
    out.append(f'<text x="{LEFT}" y="{fy}" class="p">remaining contributions:</text>')
    remaining = total
    states = [(0.0, remaining)]
    for i, (_w, _r, c, _l, _d) in enumerate(order):
        if c > 0:
            remaining -= c
            states.append((at(i), remaining))
    for k, (start, value) in enumerate(states):
        label = f'<text x="{LEFT + 25 * 7.2:.0f}" y="{fy}" class="n" visibility="{"visible" if k == 0 else "hidden"}">{value:,}'
        if k == 0 and len(states) > 1:
            anim = f'values="visible;hidden;visible" keyTimes="0;{kt(states[1][0])};{RESET}"'
        elif k == 0:
            anim = None
        elif k < len(states) - 1:
            anim = f'values="hidden;visible;hidden" keyTimes="0;{kt(start)};{kt(states[k + 1][0])}"'
        else:
            anim = f'values="hidden;visible;hidden" keyTimes="0;{kt(start)};{RESET}"'
        if anim:
            label += f'<animate attributeName="visibility" calcMode="discrete" dur="{dur:.2f}s" repeatCount="indefinite" {anim}/>'
        out.append(label + "</text>")

    lx = width - 14 - 5 * PITCH - 80
    out.append(f'<text x="{lx}" y="{fy}" class="m">Less</text>')
    for lvl in range(5):
        out.append(f'<rect x="{lx + 30 + lvl * PITCH}" y="{fy - 10}" width="{CELL}" height="{CELL}" rx="2" fill="{t["cells"][lvl]}"/>')
    out.append(f'<text x="{lx + 30 + 5 * PITCH + 4}" y="{fy}" class="m">More</text>')
    out.append(f'<text x="{LEFT}" y="{fy + 20}" class="m">{total:,} contributions in the last year</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    calendar = fetch()
    for name in THEMES:
        path = ROOT / f"contrib_{name}.svg"
        path.write_text(render(calendar, name), encoding="utf-8")
        print(f"wrote {path.name} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
