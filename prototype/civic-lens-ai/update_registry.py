import sys
content = open('c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-ai/app/routing/registry.py').read()
content = content.replace('from app.taxonomy import Category', 'from app.taxonomy import Category, Department')
content = content.replace('"Road Maintenance"', 'Department.ROADS_PWD.value')
content = content.replace('"Sanitation"', 'Department.SANITATION_WASTE.value')
content = content.replace('"Electrical/Municipal Lighting"', 'Department.ELECTRICAL_LIGHTING.value')
content = content.replace('"Drainage/Public Works"', 'Department.DRAINAGE_SEWERAGE.value')
content = content.replace('"Water Supply Board"', 'Department.WATER_SUPPLY.value')
content = content.replace('"Sewerage Operations"', 'Department.DRAINAGE_SEWERAGE.value')
content = content.replace('"Power Distribution"', 'Department.ELECTRICAL_LIGHTING.value')
content = content.replace('"Public Health & Sanitation"', 'Department.PUBLIC_TOILETS.value')
content = content.replace('"Horticulture & Parks"', 'Department.PARKS_HORTICULTURE.value')
content = content.replace('"Traffic Management"', 'Department.TRAFFIC_SAFETY.value')
content = content.replace('"Civic Helpdesk"', 'Department.OTHER_GENERAL.value')

with open('c:/Users/rayme/OneDrive/Documents/SIH_2026/prototype/prototype/civic-lens-ai/app/routing/registry.py', 'w') as f:
    f.write(content)
