import sys

counts = {}
with open(sys.argv[1]) as f:
    for line in f:
        if line.startswith("From"):
            sender = line.split()[1]
            counts[sender] = counts.get(sender, 0) + 1
print(counts)
