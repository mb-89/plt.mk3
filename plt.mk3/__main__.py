from base.app import App
import argparse

def main():
    app = App()

    parser = argparse.ArgumentParser(description= app.info["name"]+' cmd line')
    parser.add_argument('--cmds', type=str, help = "execute these command strings after startup. Can be a file path.", nargs="+", default = [])
    parser.add_argument('--nomultithread', action="store_true", help = "pass this flag to disable multithreading (for debugging)")
    args = vars(parser.parse_args())

    app.start(args)

if __name__ == "__main__":main()