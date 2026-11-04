import sys

entities = []
sender = None
with open(sys.argv[1]) as f:
    for line in f:
        if line.startswith("From "):
            sender = line.split()[1]
        if line.startswith("Subject:"):
            entities.append((sender, line[9:]))
print(entities)
