import re
import sys

found = []
for line in open(sys.argv[1]):
    m = re.search(r"[\w.]+@[\w.]+\.\w+", line)
    if m:
        found.append(m.group())
    else:
        found.append(None)
print(found)
