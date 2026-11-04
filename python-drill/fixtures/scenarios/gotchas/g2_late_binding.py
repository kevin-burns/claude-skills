handlers = []
for env in ["dev", "test", "prod"]:
    handlers.append(lambda: f"deploy to {env}")
print([h() for h in handlers])
