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

EXCLUDE_REPOS = {USERNAME}

# Friendly fallback descriptions based on repo name keywords
KEYWORD_DESCRIPTIONS = {
    "calculator":   "A calculator application",
    "todo":         "A task management / to-do list app",
    "to-do":        "A task management / to-do list app",
    "sudoku":       "A Sudoku puzzle solver",
    "game":         "An interactive game project",
    "guessing":     "A number guessing game",
    "sort":         "A sorting algorithm implementation",
    "search":       "A search algorithm implementation",
    "api":          "A REST API project",
    "data":         "A data engineering / science project",
    "ml":           "A machine learning project",
    "portfolio":    "Personal portfolio website",
    "chat":         "A chat application",
    "auth":         "An authentication system",
    "crud":         "A CRUD application",
    "dashboard":    "An analytics dashboard",
    "scraper":      "A web scraping tool",
    "etl":          "An ETL data pipeline",
    "pipeline":     "A data pipeline project",
    "bank":         "A banking / finance application",
    "shop":         "An e-commerce / shopping project",
    "school":       "A school management system",
    "library":      "A library management system",
    "hospital":     "A hospital management system",
}


def smart_description(repo):
    desc = repo.get("description")
    if desc and desc.strip():
        return desc.strip()
    name = repo["name"].lower().replace("-", " ").replace("_", " ")
    for keyword, fallback in KEYWORD_DESCRIPTIONS.items():
        if keyword in name:
            return fallback
    return repo["name"].replace("-", " ").replace("_", " ").title() + " project"


def fetch_repos():
    url = f"https://api.github.com/users/{USERNAME}/repos"
    params = {"sort": "pushed", "direction": "desc", "per_page": 50, "type": "owner"}
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return [r for r in resp.json() if r["name"] not in EXCLUDE_REPOS and not r["fork"]]


def fetch_commit_count(repo_name):
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits"
    resp = requests.get(url, headers=HEADERS, params={"per_page": 1})
    if resp.status_code != 200:
        return "—"
    link = resp.headers.get("Link", "")
    if 'rel="last"' in link:
        match = re.search(r'page=(\d+)>; rel="last"', link)
        if match:
            return match.group(1) + "+"
    return str(len(resp.json()))


def fetch_topics(repo_name):
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/topics"
    headers = {**HEADERS, "Accept": "application/vnd.github.mercy-preview+json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return "—"
    topics = resp.json().get("names", [])
    return ", ".join(f"`{t}`" for t in topics) if topics else "—"


def parse_pushed_at(repo):
    pushed = repo.get("pushed_at") or repo.get("updated_at")
    return datetime.fromisoformat(pushed.replace("Z", "+00:00"))


def days_ago(repo):
    delta = datetime.now(timezone.utc) - parse_pushed_at(repo)
    d = delta.days
    if d == 0:
        return "today"
    if d == 1:
        return "yesterday"
    return f"{d} days ago"


def build_projects_section(repos):
    if not repos:
        return "No public repositories found yet."

    repos_sorted = sorted(repos, key=parse_pushed_at, reverse=True)
    current   = repos_sorted[0]
    completed = repos_sorted[1:6]

    pushed_str  = parse_pushed_at(current).strftime("%d %b %Y")
    description = smart_description(current)
    language    = current.get("language") or "—"
    stars       = current.get("stargazers_count", 0)
    forks       = current.get("forks_count", 0)
    issues      = current.get("open_issues_count", 0)
    size_kb     = current.get("size", 0)
    size_str    = f"{size_kb:,} KB" if size_kb else "—"
    commits     = fetch_commit_count(current["name"])
    topics      = fetch_topics(current["name"])
    last_active = days_ago(current)
    visibility  = "🔓 Public" if not current.get("private") else "🔒 Private"

    current_block = f"""### 🔧 Currently Working On

| Field | Details |
|---|---|
| **📁 Repo** | [{current['name']}]({current['html_url']}) |
| **📝 Description** | {description} |
| **💻 Language** | {language} |
| **🏷️ Topics** | {topics} |
| **⭐ Stars** | {stars} |
| **🍴 Forks** | {forks} |
| **🐛 Open Issues** | {issues} |
| **📦 Repo Size** | {size_str} |
| **📊 Commits** | {commits} |
| **🕒 Last Active** | {last_active} ({pushed_str}) |
| **🔐 Visibility** | {visibility} |

"""

    if completed:
        rows = []
        for r in completed:
            desc   = smart_description(r)
            lang   = r.get("language") or "—"
            stars_c = r.get("stargazers_count", 0)
            pushed = parse_pushed_at(r).strftime("%d %b %Y")
            rows.append(
                f"| [{r['name']}]({r['html_url']}) | {desc} | {lang} | ⭐ {stars_c} | {pushed} |"
            )

        completed_block = (
            "### ✅ Completed / Previous Projects\n\n"
            "| Project | Description | Language | Stars | Last Pushed |\n"
            "|---------|-------------|----------|-------|-------------|\n"
            + "\n".join(rows) + "\n\n"
        )
    else:
        completed_block = ""

    updated_at = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    footer = f"<sub>🤖 Auto-updated by GitHub Actions · Last checked: {updated_at}</sub>\n"

    return current_block + completed_block + footer


def update_readme(projects_section):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    pattern     = r"(<!-- PROJECTS:START -->).*?(<!-- PROJECTS:END -->)"
    replacement = f"<!-- PROJECTS:START -->\n{projects_section}\n<!-- PROJECTS:END -->"
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        print("⚠️  Markers <!-- PROJECTS:START --> / <!-- PROJECTS:END --> not found.")
        return False

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    print("✅ README updated successfully.")
    return True


if __name__ == "__main__":
    print(f"🔍 Fetching repos for {USERNAME}...")
    repos = fetch_repos()
    print(f"   Found {len(repos)} repos.")
    section = build_projects_section(repos)
    success = update_readme(section)
    if not success:
        exit(1)
