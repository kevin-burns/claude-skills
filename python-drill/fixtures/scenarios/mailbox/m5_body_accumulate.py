import sys

bodies = []
body = ""
in_body = False
with open(sys.argv[1]) as f:
    for line in f:
        if line.startswith("From "):
            if body:
                bodies.append(body)
            in_body = False
        elif line.strip() == "" and not in_body:
            in_body = True
        elif in_body:
            body += line.strip() + " "
print(len(bodies))
print(bodies)
