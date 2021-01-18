from .__parser__ import Parser as _P
from lxml import etree
import os.path as op
from lxml import etree
from PySide2.QtCore import QCoreApplication
import numpy as np
import pandas as pd

app = QCoreApplication.instance()

class Parser(_P):
    def parse(self, filepath):
        if not op.isfile(filepath):raise UserWarning("path is not a file")
        try: rootxml = etree.parse(filepath).getroot()
        except: raise UserWarning("not a valid xml")
        isVisionXML = (rootxml.tag == "DataSet") or (rootxml.tag == "DataMatrix")
        if not isVisionXML:raise UserWarning("not a valid visionxml")

        app.log.info(f"started parsing {op.basename(filepath)} (visionxml)")
        dfs = self.analyzevisionxml(rootxml, filepath)
        dfs = self.postprocess(dfs, filepath)

        if dfs:app.log.info(f"done parsing {op.basename(filepath)}, extracted {len(dfs)} dataframes. (visionxml)")
        else: app.log.error(f"parsing {op.basename(filepath)} failed.")
        return dfs

    def analyzevisionxml(self, rootxml, filepath):
        dirname = op.dirname(filepath)
        dataframes = []
        #first, clean up the xml and resolve all children:
        xml = rootxml.find("VisionStructure")
        self._recursiveResolveXMLchildren(xml, dirname)

        #get all mass data files
        massData = []
        for record in (x for x in xml.iter("AssociatedRecord") if x.find("Name").text == "MassData"):
            path = [record.find("RecordRef").text]
            target = record.getparent()
            columnInfo = target.getparent().find("Private").find("Columns")
            while target != xml:
                nameelem = target.find("RecordRef")
                if nameelem is not None:
                    path.append(op.dirname(target.find("RecordRef").text))
                target=target.getparent()
            path = op.join(dirname, *reversed(path))
            if op.isfile(path) and op.getsize(path):
                massData.append((path,columnInfo))

        #parse all data matrices
        L = len(massData)
        idx = 0
        for f, cols in massData:
            basename = op.basename(op.dirname(f))
            app.log.info(f"extracting datamatrix {f}...")
            dtypes = self.getdtypes(cols)
            data = np.fromfile(f, dtype=dtypes)
            df = pd.DataFrame(data)
            for x in df.columns:
                if x.startswith("$pad"):
                    del df[x]
            dataframes.append(df)

        return dataframes

    def getdtypes(self, cols):
        dtypeListlist = []
        dt = np.dtype([('a', 'i4'), ('b', 'i4'), ('c', 'i4'), ('d', 'f4'), ('e', 'i4'),
                    ('f', 'i4', (256,))])

        colnames = []
        nrOfplaceHolders = 0
        for col in cols.iter("Column"):

            quantityName = col.find("Quantity").text
            signame = col.find("Signal").text.replace("\\","").replace("_","/")
            if signame in colnames: quantityName = "IGNORE"
            else:                   colnames.append(signame)
            unit = col.find("Unit").text
            fullname = signame+"_"+quantityName#+"_"+unit
            if   quantityName is None:
                raise UserWarning("invalid rawdata")

            elif quantityName == "Logical":
                dtypeListlist.append((fullname,'b'))
                dtypeListlist.append((f"$pad{nrOfplaceHolders}",'V7'))
                nrOfplaceHolders+=1
                #mask="b7x"

            elif quantityName in ["Integer", "Integer Flag"]:
                dtypeListlist.append((f"$pad{nrOfplaceHolders}",'V4'))
                dtypeListlist.append((fullname,'i4'))
                nrOfplaceHolders+=1

            elif quantityName in ["Text", "IGNORE"]:
                #dtypeListlist.append((fullname,'i4'))
                dtypeListlist.append((f"$pad{nrOfplaceHolders}",'V8'))
                nrOfplaceHolders+=1

            else:
                type = np.dtype('d')
                dtypeListlist.append((fullname,type))

        return np.dtype(dtypeListlist)

    def _recursiveResolveXMLchildren(self, xml, dirname):
        for ch in list(xml.iterchildren("Child")):
            file = op.join(dirname, ch.find("RecordRef").text)
            tmproot = etree.parse(file).getroot()
            chxml = tmproot
            #if not chxml: continue
            #tmproot.remove(chxml)
            namechild = etree.SubElement(chxml, "Name")
            namechild.text = ch.find("Name").text
            recordchild = etree.SubElement(chxml, "RecordRef")
            recordchild.text = ch.find("RecordRef").text
            xml.remove(ch)
            chxml.tag = namechild.text.replace(" ","")
            xml.append(chxml)