from PySide2 import QtCore
from functools import wraps, partial

app = QtCore.QCoreApplication.instance()

class Plugin(QtCore.QObject):
    @staticmethod
    def getDependencies():
        return []

    def __init__(self):
        super().__init__()

    def stop(self): pass
    def start(self): pass

def publicFun(fun=None, *, guishortcut = None, isAsync = False):
        if fun is None:
            return partial(publicFun, guishortcut=guishortcut, isAsync=isAsync)
        fun.__dict__["__is_public_fun__"] = True
        fun.__dict__["__public_fun_shortcut__"] = guishortcut
        fun.__dict__["__is_async__"] = isAsync and not app.args["noAsync"]
        @wraps(fun)
        def wrapper(*args, **kwargs):
            if fun.__dict__["__is_async__"]:
                runner = AsyncRunner(fun, args, kwargs)
                runner.singalSender.doneSig.connect(_app.cmdDone.emit)
                QtCore.QThreadPool.globalInstance().start(runner)
            else:
                fun(*args, **kwargs)
                app.cmdDone.emit()
        return wrapper

class AsyncSignalSender(QtCore.QObject):
    doneSig = QtCore.Signal()
    def done(self):
        self.doneSig.emit()

class AsyncRunner(QtCore.QRunnable):
    def __init__(self, fun, *args, **kwargs):
        super().__init__()
        self.fun = fun
        self.args = args
        self.kwargs = kwargs
        self.signalSender = AsyncSignalSender()
    def run(self):
        self.fun(*self.args, **self.kwargs)
        self.signalSender.done()
