import sys

entities = []
with open(sys.argv[1]) as f:
    for line in f:
        if line.startswith("From:"):
            entities.append(line.split()[1])
print(entities)
