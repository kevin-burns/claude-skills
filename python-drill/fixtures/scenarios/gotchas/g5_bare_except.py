def port(cfg):
    try:
        return int(cfg["port"])
    except:
        return 8080

print(port({"port": "80"}), port({"port": "eighty"}), port({}), port(None))
