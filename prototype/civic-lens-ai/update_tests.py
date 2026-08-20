import os

files = [
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-ai/tests/test_phase4.py',
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-ai/tests/test_phase5.py',
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-ai/tests/test_phase6_rag.py',
    'c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-ai/tests/test_phase8a_persistence.py'
]

replacements = [
    ('"Road Maintenance"', '"Roads & PWD"'),
    ('"Sanitation"', '"Sanitation & Waste Management"'),
    ('"Electrical/Municipal Lighting"', '"Electrical / Street Lighting"'),
    ('"Drainage/Public Works"', '"Drainage & Sewerage"'),
    ('"Water Supply Board"', '"Water Supply"'),
    ('"Sewerage Operations"', '"Drainage & Sewerage"'),
    ('"Power Distribution"', '"Electrical / Street Lighting"'),
    ('"Public Health & Sanitation"', '"Public Toilets"'),
    ('"Horticulture & Parks"', '"Parks & Horticulture"'),
    ('"Traffic Management"', '"Traffic & Road Safety"'),
    ('"Civic Helpdesk"', '"Other / General"')
]

for file in files:
    if os.path.exists(file):
        with open(file, 'r') as f:
            content = f.read()
        for old, new in replacements:
            content = content.replace(old, new)
        with open(file, 'w') as f:
            f.write(content)
