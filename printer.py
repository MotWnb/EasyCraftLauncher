class Printer(object):
    def info(self, text, end="\n"):
        print(f"\033[97m[INFO] {text}\033[0m", end=end)

    def warn(self, text, end="\n"):
        print(f"\033[93m[WARN] {text}\033[0m", end=end)

    def error(self, text, end="\n"):
        print(f"\033[91m[ERROR] {text}\033[0m", end=end)
