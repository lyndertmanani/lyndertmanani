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
    id
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
    repositoriesContributedTo(first: 100, includeUserRepositories: true, contributionTypes: [COMMIT]) {
      totalCount
      nodes { nameWithOwner }
    }
  }
}
"""

HISTORY = """
query($owner: String!, $name: String!, $id: ID!, $after: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit {
      history(author: {id: $id}, first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { additions deletions }
      }
    } } }
  }
}
"""
THEMES = {
    "dark": {"text": "#c9d1d9", "muted": "#8b949e", "accent": "#a371f7", "track": "#21262d"},
    "light": {"text": "#24292f", "muted": "#6e7781", "accent": "#8250df", "track": "#eaeef2"},
}


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "stats-card"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if "errors" in payload and not payload.get("data"):
        raise SystemExit(json.dumps(payload["errors"], indent=2))
    return payload["data"]


def lines_changed(user):
    """Lines added and deleted in your commits on the default branch of every repo you contributed to."""
    added = deleted = 0
    for repo in user["repositoriesContributedTo"]["nodes"]:
        owner, name = repo["nameWithOwner"].split("/")
        after = None
        for _page in range(30):
            try:
                data = gql(HISTORY, {"owner": owner, "name": name, "id": user["id"], "after": after})
            except Exception:
                break
            ref = (data.get("repository") or {}).get("defaultBranchRef")
            if not ref or not ref.get("target"):
                break
            hist = ref["target"]["history"]
            for c in hist["nodes"]:
                added += c["additions"]
                deleted += c["deletions"]
            if not hist["pageInfo"]["hasNextPage"]:
                break
            after = hist["pageInfo"]["endCursor"]
    return added, deleted


def fmt(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    return f"{n / 1000:.1f}k" if n >= 10000 else f"{n:,}"


def render(user, lines, t):
    cc = user["contributionsCollection"]
    added, deleted = lines
    rows = [
        ("Repos contributed to", f'{user["repositoriesContributedTo"]["totalCount"]:,}'),
        ("Contributions (last year)", f'{cc["contributionCalendar"]["totalContributions"]:,}'),
        ("Commits (last year)", f'{cc["totalCommitContributions"]:,}'),
        ("Lines of code changed", fmt(added + deleted)),
        ("Lines added", "+" + fmt(added)),
        ("Lines deleted", "-" + fmt(deleted)),
    ]
    width, row_h = 360, 26
    height = 40 + len(rows) * row_h
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<style>.h{{fill:{t["accent"]};font-size:16px;font-weight:600}}.l{{fill:{t["muted"]};font-size:13px}}'
        f'.v{{fill:{t["text"]};font-size:13px;font-weight:600}}</style>',
        '<text x="4" y="22" class="h">GitHub stats</text>',
    ]
    for i, (label, value) in enumerate(rows):
        y = 52 + i * row_h
        out.append(f'<text x="4" y="{y}" class="l">{label}</text><text x="{width - 4}" y="{y}" class="v" text-anchor="end">{value}</text>')
    out.append("</svg>")
    return "\n".join(out)

def main():
    user = gql(QUERY, {"login": LOGIN})["user"]
    lines = lines_changed(user)
    for name, t in THEMES.items():
        path = ROOT / f"stats_{name}.svg"
        path.write_text(render(user, lines, t), encoding="utf-8")
        print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
