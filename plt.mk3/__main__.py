from base.app import App
import argparse

def main():
    app = App()

    parser = argparse.ArgumentParser(description= app.info["name"]+' cmd line')
    parser.add_argument('--cmds', type=str, help = "execute these command strings after startup. Can be a file path.", nargs="+", default = [])
    parser.add_argument('--noAsync', action="store_true", help = "pass this flag to disable async execution (for debugging)")
    parser.add_argument('--nogui', action="store_true", help = "pass this flag to disable the gui (for cmd batch execution)")
    args = vars(parser.parse_args())

    app.start(args)

if __name__ == "__main__":main()