import requests
import os
from datetime import datetime, timedelta, timezone

GH_TOKEN = os.getenv('GH_TOKEN')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
ORG = 'tryvinci'

headers = {
    'Authorization': f'token {GH_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

now = datetime.now(timezone.utc)
yesterday = now - timedelta(days=1)
since = yesterday.isoformat()

# Get list of repos
repo_resp = requests.get(f'https://api.github.com/orgs/{ORG}/repos?per_page=100', headers=headers)

if repo_resp.status_code != 200:
    print("Failed to fetch repos:", repo_resp.status_code, repo_resp.text)
    exit(1)

repos = repo_resp.json()
summary_lines = [f'## 🧾 Daily GitHub Issue Summary – {now.strftime("%Y-%m-%d")}']
has_any_issues = False  # ✅ flag to track if we found anything

for repo in repos:
    repo_name = repo['name']
    if repo.get('archived'):
        continue

    # Get open issues
    open_resp = requests.get(f'https://api.github.com/repos/{ORG}/{repo_name}/issues?state=open&per_page=100', headers=headers)
    open_issues = open_resp.json()
    open_issues = [i for i in open_issues if 'pull_request' not in i]

    # Get closed issues in the last 24h
    closed_resp = requests.get(f'https://api.github.com/repos/{ORG}/{repo_name}/issues?state=closed&since={since}&per_page=100', headers=headers)
    closed_issues = closed_resp.json()
    closed_issues = [i for i in closed_issues if 'pull_request' not in i]

    if open_issues or closed_issues:
        has_any_issues = True
        summary_lines.append(f'\n### `{repo_name}`')

        if open_issues:
            summary_lines.append(f'**Open Issues** ({len(open_issues)}):')
            for issue in open_issues:
                summary_lines.append(f'- [#{issue["number"]}]({issue["html_url"]}) {issue["title"]}')

        if closed_issues:
            summary_lines.append(f'**Closed in last 24h** ({len(closed_issues)}):')
            for issue in closed_issues:
                summary_lines.append(f'- [#{issue["number"]}]({issue["html_url"]}) {issue["title"]}')

        summary_lines.append('')

# ✅ Add fallback message if no issues found
if not has_any_issues:
    summary_lines.append('✅ No open or closed issues to report today across any repositories.')

# Send message to Discord (max 2000 characters)
msg = '\n'.join(summary_lines)
if len(msg) > 2000:
    msg = msg[:1997] + '...'

res = requests.post(DISCORD_WEBHOOK, json={'content': msg})
if res.status_code != 204:
    print("❌ Failed to send to Discord:", res.status_code, res.text)
else:
    print("✅ Sent summary to Discord.")
