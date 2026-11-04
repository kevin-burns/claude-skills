import sys

entities = []
with open(sys.argv[1]) as f:
    for line in f:
        if line.startswith("Subject:"):
            entities.append(line.split()[3])
print(entities)
