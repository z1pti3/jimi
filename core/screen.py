# Handle linux and windows modules
try:
    import readline
except ImportError:
    import pyreadline as readline

class _screen:
    def __init__(self, menu_items, prompt):
        self.items = menu_items
        self.prompt = prompt

    def complete(self, text, state):
        for item in self.items:
            if item[0].startswith(text):
                if not state:
                    if len(item[0].split(" ")) == len(text.split(" ")):
                        return item[0]
                else:
                    state -= 1

    def load(self):
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims("")
        try:
            ret=1
            while ret!=0:
                readline.set_completer(self.complete)
                ans = input(self.prompt)
                call = None
                for item in self.items:
                    if ans.startswith(item[0]):                   
                        if (item[1] != None):
                            # Searches in order e.g. start, start worker, start worker thread; but needs to match the best match that will be the last
                            call = [item[1],ans.split()]
                if call:
                    # Making call to the best matched menu item
                    ret = call[0](call[1])
        except KeyboardInterrupt:
            pass
        print()
