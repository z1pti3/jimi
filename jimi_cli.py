import sys
import os

if len(sys.argv) > 1:
    if sys.argv[1] == "reset":
        if sys.argv[2] == "root":
            from core import auth
            from system import install
            rootUser = auth._user().getAsClass(query={ "username" : "root" })
            if len(rootUser) == 1:
                rootUser = rootUser[0]
                rootPass = install.randomString(30)
                rootUser.setAttribute("passwordHash",rootPass)
                rootUser.update(["passwordHash"])
                print("{0}".format(rootPass))
else:
    from screens import mainScreen
    screen = mainScreen.mainScreen()
