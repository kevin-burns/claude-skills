import re

names = ["report-12-31-2025.txt", "spam-4-1-2026.csv", "notes-2026-01-04.md", "invoice-1-15-26.pdf"]
date_re = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})")
renamed = {}
for name in names:
    m = date_re.search(name)
    if not m:
        continue
    month, day, year = m.groups()
    renamed[name] = name.replace(m.group(), f"{day}-{month}-{year}")
print(renamed)
