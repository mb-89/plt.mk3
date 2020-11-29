import pyqtgraph as pg
from .__function__ import Function as _F
from scipy import signal
import pandas as pd
import copy

class Function(_F):
    def calc(self, srcSeries, f_Hz, **kwargs):
        f_Hz = float(f_Hz)
        fs = 1.0/srcSeries.attrs["_ts"]
        order = int(kwargs.get("order",2))
        fnorm = f_Hz/(fs/2)
        b,a = signal.bessel(order,fnorm,'low')
        newvals = signal.filtfilt(b,a,srcSeries)
        newseries = pd.Series(newvals, index=srcSeries.index)
        for k,v in srcSeries.attrs.items():newseries.attrs[k]=copy.copy(v)
        newseries.name = srcSeries.attrs["name"]
        newseries.attrs["comments"].append(f" (besselfilt, f={f_Hz}Hz, o={order})")
        return newseries