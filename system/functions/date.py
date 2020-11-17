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

def timeBetween(startTimeStr, endTimeStr, timeStr=None):
    if timeStr == None:
        timeStr = datetime.datetime.now().strftime('%H:%M')
    startTime = datetime.datetime.strptime(startTimeStr, '%H:%M')
    endTime = datetime.datetime.strptime(endTimeStr, '%H:%M')
    time = datetime.datetime.strptime(timeStr, '%H:%M')
    if startTime > endTime:
        return time >= startTime or time <= endTime
    else:
        return startTime <= time <= endTime

