def add_tag(name, tags=[]):
    tags.append(name)
    return tags

a = add_tag("eu")
b = add_tag("us")
c = add_tag("apac", [])
print(a, b, c)
print(a is b)
