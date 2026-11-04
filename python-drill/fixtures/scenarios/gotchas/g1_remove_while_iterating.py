hosts = ["web1", "tmp-a", "tmp-b", "db1", "tmp-c"]
for h in hosts:
    if h.startswith("tmp"):
        hosts.remove(h)
print(hosts)
