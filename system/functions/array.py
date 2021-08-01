def index(array,index):
    try:
        return array[index]
    except:
        return array

def append(array,value):
    try:
        array.append(value)
    except:
        pass
    return array

def remove(array,index):
    try:
        del array[index]
    except:
        pass
    return array
