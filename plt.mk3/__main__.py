from base.app import App
import argparse

def main():
    app = App()

    parser = argparse.ArgumentParser(description= app.info["name"]+' cmd line')
    parser.add_argument('--cmds', type=str, help = "execute these command strings after startup", nargs="+", default = [])
    args = vars(parser.parse_args())

    app.start(args)

if __name__ == "__main__":main()