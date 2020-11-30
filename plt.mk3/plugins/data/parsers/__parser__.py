from PySide2.QtCore import QObject, Signal
import os.path as op
from numpy import diff, median
nrOfDataFrames = 0

class Parser(QObject):
    done = Signal(tuple)

    def __init__(self, path, app):
        """
        Check if this parser recognizes the file at the given path.
        If so, we set the "recognized" flag to true and build a list of "reserved files"
        That this parser will use exclusively and that must not be used by other parsers
        """
        super().__init__()
        self.recognized = False
        self.reservedFiles = []
        self.app = app
        self.name = op.splitext(op.basename(path))[0]
        self.path = path
    
    def parse(self):
        """
        Here, we use the reserved files to parse the data
        We return a list of dataframes and an error message (empty string in case of no errs)
        """
        dflist = []
        self.app.log.error("parser not implemented")
        self.done.emit(dflist)

    def postprocess(self, dfList):
        """
        Here, we recv the dfs produced by the parsers and apply some common post processing, 
        like trying to find the time column and convert it to seconds, 
        splitting the result into chunks and adding the name to the dataframe
        """
        dfList = [self.reduceColnames(x) for x in dfList]
        dfList = [self.convertTime2SecFn(x) for x in dfList]
        dfList = [item for sublist in [self.mkchunks(x) for x in dfList] for item in sublist] #flattened list of lists
        dfList = [self.putConstColsInMetaData(x) for x in dfList]
        dfList = [self.addParentRefToCols(x) for x in dfList]
        for df in dfList: 
            self.addMiscMetaData(df)
            df.fillna(0,inplace=True)

        return [x for x in dfList if not x.empty]

    def addParentRefToCols(self,df):
        for x in df.columns:
            df[x].attrs["_parent"] = "bla"
        return df

    def addMiscMetaData(self, df):
        global nrOfDataFrames
        df.attrs["srcfile"] = self.path
        df.attrs["mem"] = df.memory_usage(index=True).sum()
        df.attrs["rows"] = len(df)
        df.attrs["cols"] = len(df.columns)+1
        df.attrs["idx"] = f"DF{nrOfDataFrames}"
        nrOfDataFrames += 1

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
        return df

    def convertTime2SecFn(self, df):
        #classic timestamp (days since 1900)
        if "Time_DateTime" in df:
            timecol = "Time_DateTime"
            df[timecol] = df[timecol] - df[timecol].iloc[0]
            df[timecol] = df[timecol] *60.0*60.0*24.0
            df.rename(columns={'Time_DateTime': 'Time_s'},inplace=True)
            df.set_index("Time_s",inplace=True)
        #rt_time
        elif "RT/Time_DateTime" in df:
            timecol = "RT/Time_DateTime"
            df[timecol] = df[timecol] - df[timecol].iloc[0]
            df[timecol] = df[timecol] *60.0*60.0*24.0
            df.rename(columns={'RT/Time_DateTime': 'Time_s'},inplace=True)
            df.set_index("Time_s",inplace=True)
        elif "Time_s" in df:
            df.set_index("Time_s",inplace=True)
        elif "Time" in df:
            df.set_index("Time",inplace=True)
        return df

    def putConstColsInMetaData(self, df):
        constcols = tuple(x for x in df.columns if df[x].nunique()==1)
        for cc in constcols:
            name = cc
            val = df[name].iloc[0]
            df.attrs[name] = val
            df.drop(columns=[cc], inplace=True)
        return df

    def mkchunks(self,df):
        dataframes = []
        dfdiff = diff(df.index)
        meddiff = median(dfdiff)
        splits = []
        for idx,x in enumerate(dfdiff): 
            if x>5.0*meddiff: splits.append(idx+1)

        if not splits:
            df.attrs["name"] = self.name
            df.attrs["comments"] = []
            df.attrs["_ts"] = meddiff
            dataframes = [df]
            return dataframes

        start = 0
        idx = 0
        for end in splits:
            chunk = df.iloc[start:end,:]
            dataframes.append(chunk)
            chunk.attrs["name"] = self.name+f".{idx}"
            chunk.attrs["comments"] = []
            chunk.attrs["_ts"] = meddiff
            chunk.index = chunk.index-chunk.index[0]
            idx+=1
            start = end
        return dataframes