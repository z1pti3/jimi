import time

def test():
    return { "rc" :0, "result" : True }

def test2():
    return 0, True

a,b,c = test2()

print(a)


# start = time.time()
# for i in range(0,1000000):
#     actionResult = test()
# end = time.time()

# print(end-start)

# start = time.time()
# for i in range(0,1000000):
#     actionResult = { "rc" : -1, "result" : False }
#     rc, result = test2()
#     actionResult = { "rc" : rc, "result" : result }
# end = time.time()

# print(end-start)
