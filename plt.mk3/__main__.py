from base.app import App
import argparse
from jsmin import jsmin
import json
import os.path as op

def main():

    appinfotxt = open(op.join(op.dirname(__file__),"..","APPINFO.jsonc"),"r").read()
    info = json.loads(jsmin(appinfotxt))

    parser = argparse.ArgumentParser(description= info["name"]+' cmd line')
    parser.add_argument('--cmds', type=str, help = "execute these command strings after startup. Can be a file path.", nargs="+", default = [])
    parser.add_argument('--noAsync', action="store_true", help = "pass this flag to disable async execution (for debugging)")
    parser.add_argument('--nogui', action="store_true", help = "pass this flag to disable the gui (for cmd batch execution)")
    args = vars(parser.parse_args())

    app = App(args, info)
    app.start()

if __name__ == "__main__":main()