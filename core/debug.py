import time
from functools import wraps

def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print ("Total time running %s: %s seconds" %
               (function.__name__, str(t1-t0))
               )
        return result
    return function_timer

@fn_timer
def test():
    a = { "test" : 1 }
    for x in range(0,1000000):
        try:
            b = a["test"]
        except KeyError:
            b = 1

@fn_timer
def test2():
    a = { "test" : 1 }
    for x in range(0,1000000):
        if "test" in a:
            b = a["test"]
        else:
            b = 1

test()
test2()
