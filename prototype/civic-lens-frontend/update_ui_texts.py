import os

files = [
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-frontend/src/pages/citizen/CitizenIssueDetailPage.tsx',
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-frontend/src/pages/citizen/ReportIssuePage.tsx',
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-frontend/src/pages/supervisor/VerificationQueuePage.tsx',
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-frontend/src/pages/citizen/CitizenProposalDetailPage.tsx',
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-frontend/src/pages/admin/AdminDashboardPage.tsx'
]

replacements = [
    ("|| 'PWD'", "|| 'Roads & PWD'"),
    ("operator_1 (PWD Crew 4)", "operator_1 (Roads & PWD Crew 4)"),
    ("active PWD projects", "active Roads & PWD projects"),
    ("PWD SLA Gazette Notification 2026", "Roads & PWD SLA Gazette Notification 2026"),
    ("routed to PWD dispatch team", "routed to Roads & PWD dispatch team")
]

for file in files:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        for old, new in replacements:
            content = content.replace(old, new)
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
