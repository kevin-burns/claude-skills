import json
import sys

data = json.load(open(sys.argv[1]))
summary = {}
for item in data["list"]:
    day = item["dt_txt"][:10]
    summary[day] = (item["main"]["temp"], item["weather"][0]["main"])
print(summary)
