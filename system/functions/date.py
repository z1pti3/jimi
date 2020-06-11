import time
import datetime

def now(milliseconds=False):
    if milliseconds:
        return time.time() * 1000
    return time.time()

def day():
    return datetime.datetime.now().strftime('%A')

def year():
    return int(datetime.datetime.now().strftime('%Y'))

def month():
    return int(datetime.datetime.now().strftime('%m'))

def dt(format="%d-%m-%Y"):
    return datetime.datetime.now().strftime(format)

def dateBetween(startDateStr, endDateStr, dateStr=None):
    if dateStr == None:
        dateStr = datetime.datetime.now().strftime('%H:%M %d-%m-%Y')
    startDate = datetime.datetime.strptime(startDateStr, '%H:%M %d-%m-%Y')
    endDate = datetime.datetime.strptime(endDateStr, '%H:%M %d-%m-%Y')
    date = datetime.datetime.strptime(dateStr, '%H:%M %d-%m-%Y')
    return startDate < date < endDate

def timeBetween(startDateStr, endDateStr, dateStr=None):
    if dateStr == None:
        dateStr = datetime.datetime.now().strftime('%H:%M')
    startDate = datetime.datetime.strptime(startDateStr, '%H:%M')
    endDate = datetime.datetime.strptime(endDateStr, '%H:%M')
    date = datetime.datetime.strptime(dateStr, '%H:%M')
    return startDate < date < endDate

