import re
import sys

text = open(sys.argv[1]).read()
email_re = re.compile(r"([\w.]+)@([\w.]+)")
phone_re = re.compile(r"(\d{3})-(\d{4})")
emails = email_re.findall(text)
phones = phone_re.findall(text)
print(emails)
print(phones)
print(len(set(emails)))
