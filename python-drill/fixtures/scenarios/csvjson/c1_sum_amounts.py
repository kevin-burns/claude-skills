import csv
import sys

totals = {}
with open(sys.argv[1]) as f:
    for row in csv.reader(f):
        if row[0] == "order_id":
            continue
        customer, amount = row[1], row[2]
        totals[customer] = totals.get(customer, 0) + float(amount or 0)
print(totals)
