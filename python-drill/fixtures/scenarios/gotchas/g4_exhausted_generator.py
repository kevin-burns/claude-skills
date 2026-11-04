lines = (l.strip() for l in ["a=1", "b=2", "", "c=3"] if l)
count = sum(1 for _ in lines)
keys = [l.split("=")[0] for l in lines]
print(count, keys)
