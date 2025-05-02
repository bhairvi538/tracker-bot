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

    # Fetch closed issues in the last 24 hours
    closed_resp = requests.get(
        f'https://api.github.com/repos/{ORG}/{repo_name}/issues?state=closed&since={since}&per_page=100',
        headers=headers
    )
    closed_issues = [i for i in closed_resp.json() if 'pull_request' not in i]

    # Only show repo section if either open or closed issues exist
    if open_issues or closed_issues:
        has_any_issues = True
        summary_lines.append(f'\nRepository: {repo_name}')  # Keep leading newline for spacing between repos

        # Open issues section
        summary_lines.append(f'Open Issues ({len(open_issues)}):')
        if open_issues:
            for issue in open_issues:
                summary_lines.append(f'- [#{issue["number"]}]({issue["html_url"]}) {issue["title"]}')
        else:
            summary_lines.append('- None')

        # Closed issues section
        summary_lines.append(f'Closed Issues (last 24h) ({len(closed_issues)}):')
        if closed_issues:
            for issue in closed_issues:
                summary_lines.append(f'- [#{issue["number"]}]({issue["html_url"]}) {issue["title"]}')
        else:
            summary_lines.append('- None')

if not has_any_issues:
    summary_lines.append('\nNo open or recently closed issues to report today.')

# Build the message
msg = '\n'.join(summary_lines)

# Truncate intelligently if over limit
if len(msg) > 2000:
    # Find the last newline before the 1997th character to leave room for '...'
    cutoff = msg.rfind('\n', 0, 1997)
    if cutoff == -1:
        # No newline found, truncate hard
        msg = msg[:1997] + '...'
    else:
        # Truncate at last newline and add ellipsis
        msg = msg[:cutoff] + '\n...'

# Send to Discord
res = requests.post(DISCORD_WEBHOOK, json={'content': msg})
if res.status_code != 204:
    print("Failed to send to Discord:", res.status_code, res.text)
else:
    print("Summary successfully posted to Discord.")
