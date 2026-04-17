import os
import re
import requests
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_USERNAME", "Binary-1001")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

EXCLUDE_REPOS = {USERNAME}  # Skip the profile repo itself


def fetch_repos():
    """Fetch all public repos sorted by last push."""
    url = f"https://api.github.com/users/{USERNAME}/repos"
    params = {"sort": "pushed", "direction": "desc", "per_page": 50, "type": "owner"}
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return [r for r in resp.json() if r["name"] not in EXCLUDE_REPOS and not r["fork"]]


def parse_pushed_at(repo):
    pushed = repo.get("pushed_at") or repo.get("updated_at")
    return datetime.fromisoformat(pushed.replace("Z", "+00:00"))


def build_projects_section(repos):
    """
    Most recently pushed repo = current working on.
    Everything else = completed (up to 5 shown).
    """
    if not repos:
        return "No public repositories found yet."

    # Sort by push time
    repos_sorted = sorted(repos, key=parse_pushed_at, reverse=True)

    current = repos_sorted[0]
    completed = repos_sorted[1:6]  # show up to 5 completed

    pushed_str = parse_pushed_at(current).strftime("%d %b %Y")
    description = current.get("description") or "No description provided."
    language = current.get("language") or "—"
    stars = current.get("stargazers_count", 0)

    current_block = f"""### 🔧 Currently Working On

| | Details |
|---|---|
| **Repo** | [{current['name']}]({current['html_url']}) |
| **Description** | {description} |
| **Language** | {language} |
| **Stars** | ⭐ {stars} |
| **Last pushed** | {pushed_str} |

"""

    if completed:
        rows = "\n".join(
            f"| [{r['name']}]({r['html_url']}) "
            f"| {r.get('description') or '—'} "
            f"| {r.get('language') or '—'} |"
            for r in completed
        )
        completed_block = f"""### ✅ Completed / Previous Projects

| Project | Description | Language |
|---------|-------------|----------|
{rows}

"""
    else:
        completed_block = ""

    updated_at = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    footer = f"<sub>🤖 Auto-updated by GitHub Actions · Last checked: {updated_at}</sub>\n"

    return current_block + completed_block + footer


def update_readme(projects_section):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    # Replace content between the project markers
    pattern = r"(<!-- PROJECTS:START -->).*?(<!-- PROJECTS:END -->)"
    replacement = f"<!-- PROJECTS:START -->\n{projects_section}\n<!-- PROJECTS:END -->"

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        print("⚠️  Could not find <!-- PROJECTS:START --> and <!-- PROJECTS:END --> markers in README.md")
        print("    Make sure your README.md contains both comment markers.")
        return False

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ README updated successfully.")
    return True


if __name__ == "__main__":
    print(f"🔍 Fetching repos for {USERNAME}...")
    repos = fetch_repos()
    print(f"   Found {len(repos)} repos.")

    section = build_projects_section(repos)
    success = update_readme(section)

    if not success:
        exit(1)
