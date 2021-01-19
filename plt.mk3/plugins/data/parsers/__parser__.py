from PySide2.QtCore import QObject, Signal, QCoreApplication
import os.path as op
from numpy import diff, median
nrOfDataFrames = 0

app = QCoreApplication.instance()

timeformats = {
    "time/datetime": 60.0*60.0*24.0,
    "rt/time/datetime": 60.0*60.0*24.0,
    "time": 1,
    "time/s": 1,
    "time/ms": 1e-3
}

class Parser(QObject):
    done = Signal(tuple)
    def __init__(self):
        super().__init__()
        self.name = op.splitext(op.basename(__file__))[0]

    def parse(self, filepath):
        raise UserWarning(f"parser <{self.name}> not implemented")

    def postprocess(self, dfList, filepath, disableChunks=False):
        """
        Here, we recv the dfs produced by the parsers and apply some common post processing, 
        like trying to find the time column and convert it to seconds, 
        splitting the result into chunks and adding the name to the dataframe
        """
        dfList = [self.reduceColnames(x) for x in dfList]
        dfList = [self.reindex(x) for x in dfList]
        dfList = [item for sublist in [self.chunk(x, disableChunks) for x in dfList] for item in sublist] #flattened list of lists
        dfList = [self.rmConstCols(x) for x in dfList]

        for idx,x in enumerate(dfList): 
             self.setAttrs(idx,x,filepath)
             x.fillna(0,inplace=True)
        return [x for x in dfList if not x.empty]

    def setAttrs(self, idx, df, src):
        global nrOfDataFrames
        subattrs = attrDict()
        for x in list(df.attrs.keys()):
            subattrs[x] = df.attrs.pop(x)

        df.attrs["#"] = nrOfDataFrames
        df.attrs["name"] = "df."+op.splitext(op.basename(src))[0]+f".{idx}"
        df.attrs["rows x cols"] = f"{len(df)} x {len(df.columns)}"
        df.attrs["idxcol*"] = df.index.name
        df.attrs["idxtara*"] = "DF.index[0]"
        df.attrs["attrs(?)"] = subattrs
        nrOfDataFrames+=1

    def reduceColnames(self, df):
        df.columns = [x.replace("_","/") for x in df.columns]
        cols = list(df.columns)
        
        while True:
            splitcols = [x.split("/") for x in cols]
            starts = [x[0] for x in splitcols]
            pops = [x for x in starts if starts.count(x)==1]
            for p in pops: starts.remove(p)
            rems = set(starts)
            remcnt = 0
            for rem in rems:
                for splitcol in splitcols:
                    if splitcol[0] == rem: 
                        splitcol.pop(0)
                        remcnt+=1
            if remcnt == 0:break
            if len(set(tuple(tuple(x) for x in splitcols)))<len(cols): break
            cols = ["/".join(x) for x in splitcols]
        
        df.rename(columns=dict(zip(df.columns, cols)),inplace=True)
        df.rename(columns=str.lower,inplace=True)
        return df

    def reindex(self, df):
        df.index.name = "dfidx"
        timecol = None
        for k,v in timeformats.items():
            if k in df:
                timecol = k
                fak = v
                break

        if timecol:
            df[timecol] = df[timecol] - df[timecol].iloc[0]
            df[timecol] = df[timecol] *fak
            df.rename(columns={timecol: 'time/s'},inplace=True)
            df.set_index("time/s",inplace=True)

        if not df.index.is_monotonic:
            df.sort_index(inplace=True)
        return df

    def chunk(self,df,disableChunks=False):
        dataframes = []
        dfdiff = diff(df.index)
        meddiff = median(dfdiff)
        splits = []
        if not disableChunks:
            for idx,x in enumerate(dfdiff): 
                if x>5.0*meddiff: splits.append(idx+1)
        if not splits:
            df.attrs["_ts"] = meddiff
            dataframes = [df]
            return dataframes

        start = 0
        idx = 0
        for end in splits:
            chunk = df.iloc[start:end,:]
            dataframes.append(chunk)
            chunk.attrs["_ts"] = meddiff
            chunk.index = chunk.index-chunk.index[0]
            idx+=1
            start = end
        return dataframes

    def rmConstCols(self,df):
        constcols = tuple(x for x in df.columns if df[x].nunique()==1)
        for cc in constcols:
            name = cc
            val = df[name].iloc[0]
            df.attrs[name] = val
            df.drop(columns=[cc], inplace=True)
        return df

class attrDict(dict):
    def __str__(self):
        return f"<{len(self)} items>"