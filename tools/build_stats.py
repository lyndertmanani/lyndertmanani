"""Render a GitHub stats card (stats_dark.svg / stats_light.svg) from the GraphQL API.

Needs GITHUB_TOKEN. LOGIN defaults to the repo owner.
"""
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGIN = os.environ.get("LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "lyndertmanani"
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection { totalCommitContributions contributionCalendar { totalContributions } }
  }
}
"""

THEMES = {
    "dark": {"text": "#c9d1d9", "muted": "#8b949e", "accent": "#a371f7", "track": "#21262d"},
    "light": {"text": "#24292f", "muted": "#6e7781", "accent": "#8250df", "track": "#eaeef2"},
}


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "stats-card"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(json.dumps(payload["errors"], indent=2))
    return payload["data"]["user"]


def render(user, t):
    repos = user["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    cc = user["contributionsCollection"]
    rows = [
        ("Contributions (last year)", cc["contributionCalendar"]["totalContributions"]),
        ("Commits (last year)", cc["totalCommitContributions"]),
        ("Pull requests", user["pullRequests"]["totalCount"]),
        ("Issues", user["issues"]["totalCount"]),
        ("Public repos", user["repositories"]["totalCount"]),
        ("Stars earned", stars),
        ("Followers", user["followers"]["totalCount"]),
    ]

    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            size, color = langs.get(name, (0, e["node"]["color"] or "#8b949e"))
            langs[name] = (size + e["size"], color)
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
    total = sum(s for _n, (s, _c) in top) or 1

    width, row_h = 520, 24
    height = 56 + max(len(rows), len(top) + 1) * row_h
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<style>.h{{fill:{t["accent"]};font-size:16px;font-weight:600}}.l{{fill:{t["muted"]};font-size:13px}}'
        f'.v{{fill:{t["text"]};font-size:13px;font-weight:600}}</style>',
        f'<text x="4" y="22" class="h">GitHub stats</text>',
        f'<text x="290" y="22" class="h">Top languages</text>',
    ]
    for i, (label, value) in enumerate(rows):
        y = 52 + i * row_h
        out.append(f'<text x="4" y="{y}" class="l">{label}</text><text x="230" y="{y}" class="v" text-anchor="end">{value:,}</text>')
    for i, (name, (size, color)) in enumerate(top):
        y = 52 + i * row_h
        pct = size / total
        out.append(
            f'<text x="290" y="{y}" class="l">{name}</text><text x="{width - 4}" y="{y}" class="v" text-anchor="end">{pct:.0%}</text>'
            f'<rect x="290" y="{y + 5}" width="{width - 294}" height="4" rx="2" fill="{t["track"]}"/>'
            f'<rect x="290" y="{y + 5}" width="{(width - 294) * pct:.1f}" height="4" rx="2" fill="{color}"/>'
        )
    out.append("</svg>")
    return "\n".join(out)


def main():
    user = fetch()
    for name, t in THEMES.items():
        path = ROOT / f"stats_{name}.svg"
        path.write_text(render(user, t), encoding="utf-8")
        print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
