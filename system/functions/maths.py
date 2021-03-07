import math

def sum(*args):
    sumResult=0
    for arg in args:
        sumResult+=arg
    return sumResult

def length(var):
    return len(var)

def roundNum(var):
    return round(var)

def ceil(var):
    return math.ceil(var)

def floor(var):
    return math.floor(var)

def increment(var,by):
    var += by
    return var

def decrement(var,by):
    var -= by
    return var