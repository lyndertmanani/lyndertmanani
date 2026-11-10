"""Render the contribution calendar with a GitHub Copilot icon eating it.

Fetches the last year of contributions through the GraphQL API and writes
contrib_dark.svg / contrib_light.svg. As the icon eats each square the
"remaining" counter drops by that day's contribution count.

Needs GITHUB_TOKEN in the environment. LOGIN defaults to the repo owner.
"""
import json
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
        "bg": "#0d1117", "border": "#30363d", "bar": "#161b22", "text": "#c9d1d9",
        "muted": "#8b949e", "accent": "#a371f7",
        "cells": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "bar": "#f6f8fa", "text": "#24292f",
        "muted": "#6e7781", "accent": "#8250df",
        "cells": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    },
}

CELL, GAP = 11, 3
PITCH = CELL + GAP
LEFT, TOP = 36, 66
STEP_SECONDS = 0.05
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


def kt(value):
    return f"{min(max(value, 0.0), 1.0):.4f}"


def render(calendar, theme_name):
    t = THEMES[theme_name]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    order = eating_order(weeks)
    n = len(order)
    move = n * STEP_SECONDS
    dur = move + PAUSE_SECONDS
    frac = move / dur

    width = LEFT + len(weeks) * PITCH + 14
    height = TOP + 7 * PITCH + 62

    def at(i):
        return max(i / (n - 1) * frac, 0.0001)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'font-family="ConsolasFallback,Consolas,Menlo,monospace">',
        "<style>text{white-space:pre}.m{fill:%s;font-size:10px}.p{fill:%s;font-size:12px}.n{fill:%s;font-size:14px;font-weight:bold}</style>"
        % (t["muted"], t["text"], t["accent"]),
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="2"/>',
        f'<path d="M1 11a10 10 0 0 1 10-10h{width - 22}a10 10 0 0 1 10 10v22H1z" fill="{t["bar"]}"/>',
        '<circle cx="20" cy="17" r="5" fill="#ff5f56"/><circle cx="38" cy="17" r="5" fill="#ffbd2e"/><circle cx="56" cy="17" r="5" fill="#27c93f"/>',
        f'<text x="78" y="21" class="p">lendert@manani:~$ <tspan fill="{t["accent"]}">./eat-contributions.sh</tspan></text>',
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
            f'values="{base};{empty};{base}" keyTimes="0;{kt(at(i))};{RESET}"/></rect>'
        )

    pos = [
        (LEFT + w * PITCH + CELL / 2 - 8, TOP + row * PITCH + CELL / 2 - 8)
        for (w, row, _c, _l, _d) in order
    ]
    values = ";".join(f"{x:.1f} {y:.1f}" for x, y in pos) + f";{pos[-1][0]:.1f} {pos[-1][1]:.1f}"
    keytimes = ";".join(kt(i / (n - 1) * frac) for i in range(n)) + ";1"
    out.append(
        f'<g><animateTransform attributeName="transform" type="translate" calcMode="linear" '
        f'dur="{dur:.2f}s" repeatCount="indefinite" values="{values}" keyTimes="{keytimes}"/>'
        f'<path d="{COPILOT_PATH}" fill="{t["accent"]}" transform="scale(0.6667)"/></g>'
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
