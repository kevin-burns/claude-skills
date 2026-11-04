def load(path):
    try:
        raise FileNotFoundError(path)
    finally:
        return "defaults"

print(load("/etc/app.conf"))
