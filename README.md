

```
           8 8888            8 8888                    ,8.       ,8.                     8 8888
           8 8888            8 8888                   ,888.     ,888.                    8 8888
           8 8888            8 8888                  .`8888.   .`8888.                   8 8888
           8 8888            8 8888                 ,8.`8888. ,8.`8888.                  8 8888
           8 8888            8 8888                ,8'8.`8888,8^8.`8888.                 8 8888
           8 8888            8 8888               ,8' `8.`8888' `8.`8888.                8 8888
88.        8 8888            8 8888              ,8'   `8.`88'   `8.`8888.               8 8888
`88.       8 888'            8 8888             ,8'     `8.`'     `8.`8888.              8 8888
  `88o.    8 88'             8 8888            ,8'       `8        `8.`8888.             8 8888
    `Y888888 '               8 8888           ,8'         `         `8.`8888.            8 8888
```

**Notable Featues**
* Advanced task scheduling
* Trigger action flow system
* Event log management integration
* Service desk integration
* Plugin system for expansion
* IF logic including variable access and function calls
* Variables setable and passable within flows


**Supported Functions within IF and VAR:**

now() - Returns current epoc time

day() - Returns day as a number

year() - Returns year as a number

month() - Returns month as number

dt(format="%d-%m-%Y") - Returns datetime in defined feilds

sum(a,b,etc,etc) - Adds all supplied ints

cidr(address, addressRange) - True if IPv4 address given is within network CIDR provided

**Install:**
1. Install and configure MongoDB
2. Install python requirements from requirements.py
3. Create data directroy and within this directoy place settings.json and an RSA public and private key
4. Run jimi_core.py, followed by jimi_web.py ( root login password is randomly generated and will be within jimi_core output when first ran

settings.json - Sample:
```
{
    "system" : {
        "systemID" : 0
    },
    "debug" : {
        "level" : -1,
        "buffer" : 1000
    },
    "mongodb": {
        "host" : "172.19.32.1",
        "port" : 27017,
        "db" : "dev",
        "username" : null,
        "password" : null
    },
    "api": {
        "core" : {
            "bind" : "127.0.0.1",
            "port" : 5000,
            "base" : "api/1.0",
            "apiKey" : null
        },
        "web" : {
            "bind" : "127.0.0.1",
            "port" : 5002,
            "base" : "api/1.0",
            "apiKey" : null
        },
        "proxy" : {
            "http" : null,
            "https" : null
        }
    },
    "workers" : { 
        "concurrent" : 15,
        "loopT" : 0.01,
        "loopT1" : 0.25,
        "loopL" : 200
    },
    "cpuSaver" : { 
        "loopT" : 0.01,
        "loopL" : 100
    },
    "scheduler" : {
        "loopP" : 5
    },
    "cluster" : {
        "loopP" : 10,
        "recoveryTime" : 60,
        "deadTimer" : 30
    },
    "audit" : {
    "db" : {
        "enabled" : true
    },
    "file" : {
        "enabled" : true,
        "logdir" : "log"
    }
    },
    "auth" : {
        "enabled" : true,
        "sessionTimeout" : 900,
        "rsa" : {
            "cert" : "data/sessionPub.pem",
            "key" : "data/sessionPriv.pem"
        },
        "policy" : {
            "minLength" : 8,
            "minNumbers" : 1,
            "minLower" : 1,
            "minUpper" : 1,
            "minSpecial" : 0
        }
    }
}
```

