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

# Get list of repositories
repo_resp = requests.get(f'https://api.github.com/orgs/{ORG}/repos?per_page=100', headers=headers)

if repo_resp.status_code != 200:
    print("Failed to fetch repositories:", repo_resp.status_code, repo_resp.text)
    exit(1)

repos = repo_resp.json()
summary_lines = [f'Daily GitHub Issue Summary – {now.strftime("%Y-%m-%d")}']
has_any_issues = False

for repo in repos:
    repo_name = repo['name']
    if repo.get('archived'):
        continue

    # Fetch open issues
    open_resp = requests.get(
        f'https://api.github.com/repos/{ORG}/{repo_name}/issues?state=open&per_page=100',
        headers=headers
    )
    open_issues = [i for i in open_resp.json() if 'pull_request' not in i]

    # Fetch recently closed issues (last 24 hours)
    closed_resp = requests.get(
        f'https://api.github.com/repos/{ORG}/{repo_name}/issues?state=closed&since={since}&per_page=100',
        headers=headers
    )
    closed_issues = [i for i in closed_resp.json() if 'pull_request' not in i]

    if open_issues or closed_issues:
        has_any_issues = True
        summary_lines.append(f'\nRepository: {repo_name}')

        if open_issues:
            summary_lines.append(f'Open Issues ({len(open_issues)}):')
            for issue in open_issues:
                summary_lines.append(f'- [#{issue["number"]}]({issue["html_url"]}) {issue["title"]}')

        if closed_issues:
            summary_lines.append(f'Closed Issues (last 24h) ({len(closed_issues)}):')
            for issue in closed_issues:
                summary_lines.append(f'- [#{issue["number"]}]({issue["html_url"]}) {issue["title"]}')

        summary_lines.append('')

if not has_any_issues:
    summary_lines.append('No open or recently closed issues to report today.')

# Send message to Discord
msg = '\n'.join(summary_lines)
if len(msg) > 2000:
    msg = msg[:1997] + '...'

res = requests.post(DISCORD_WEBHOOK, json={'content': msg})
if res.status_code != 204:
    print("Failed to send to Discord:", res.status_code, res.text)
else:
    print("Summary successfully posted to Discord.")
