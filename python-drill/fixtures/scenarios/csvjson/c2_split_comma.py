import sys

totals = {}
for line in open(sys.argv[1]).readlines()[1:]:
    order_id, customer, amount, date = line.strip().split(",")
    totals[customer] = totals.get(customer, 0) + float(amount)
print(totals)
