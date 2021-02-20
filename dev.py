from operator import itemgetter
import time

flows = [{"order" : 0, "test" : 4},{"order" : 1, "test" : 3},{"order" : 0, "test" : 2},{"test" : 0}]
print(flows)

try:
    newlist = sorted(flows, key=itemgetter("order"), reverse=True) 
except KeyError:
    for value in flows:
        if "order" not in value:
            value["order"] = 0
    newlist = sorted(flows, key=itemgetter("order"), reverse=True) 
print(newlist)