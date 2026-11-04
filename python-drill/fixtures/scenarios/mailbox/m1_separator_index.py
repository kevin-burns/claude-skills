import sys

entities = []
for line in open(sys.argv[1]):
    if line.startswith("From "):
        entities.append(line.split()[3])
print(entities)
