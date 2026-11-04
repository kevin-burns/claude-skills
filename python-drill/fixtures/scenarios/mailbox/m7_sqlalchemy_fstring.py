import sys

from sqlalchemy import create_engine, text

engine = create_engine("sqlite://")
conn = engine.connect()
conn.execute(text("CREATE TABLE mail (sender TEXT, subject TEXT)"))

entities = []
sender = None
for line in open(sys.argv[1]):
    if line.startswith("From "):
        sender = line.split()[1]
        entities.append(sender)
    if line.startswith("Subject:"):
        subject = line[9:].strip()
        conn.execute(text(f"INSERT INTO mail VALUES ('{sender}', '{subject}')"))

print(entities)
print(conn.execute(text("SELECT count(*) FROM mail")).scalar())
