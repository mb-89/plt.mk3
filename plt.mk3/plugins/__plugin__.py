from PySide2 import QtCore
from functools import wraps, partial

_app = None

class Plugin(QtCore.QObject):
    @staticmethod
    def getDependencies():
        return []

    def __init__(self, app):
        global _app
        super().__init__()
        self.app = app
        self.log = app.log
        _app = app

    def stop(self): pass
    def start(self): pass

def publicFun(fun=None, *, guishortcut = None, isAsync = False):
        if fun is None:
            return partial(publicFun, guishortcut=guishortcut, isAsync=isAsync)
        fun.__dict__["__is_public_fun__"] = True
        fun.__dict__["__public_fun_shortcut__"] = guishortcut
        fun.__dict__["__is_async__"] = isAsync and not _app.args["noAsync"]
        @wraps(fun)
        def wrapper(*args, **kwargs):
            if fun.__dict__["__is_async__"]:
                fun(*args, **kwargs)
            else:
                fun(*args, **kwargs)
                _app.cmdDone.emit()
        return wrapper


