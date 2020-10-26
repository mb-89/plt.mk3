from PySide2 import QtCore
from functools import wraps, partial

class Plugin(QtCore.QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = app.log

    def stop(self): pass
    def start(self): pass

def publicFun(fun=None, *, guishortcut = None):
        if fun is None:
            return partial(publicFun, guishortcut=guishortcut)
        fun.__dict__["__is_public_fun__"] = True
        fun.__dict__["__public_fun_shortcut__"] = guishortcut
        @wraps(fun)
        def wrapper(*args, **kwargs):
            fun(*args, **kwargs)
        return wrapper
