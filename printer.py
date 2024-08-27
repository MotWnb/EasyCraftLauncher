class Printer(object):
    @staticmethod
    def info(text, end="\n"):
        # 判断是否需要强制换行
        if end != "\n":
            text += "\n"
        print(f"\033[97m[INFO] {text}\033[0m", end=end, flush=False)

    @staticmethod
    def warn(text, end="\n"):
        if end != "\n":
            text += "\n"
        print(f"\033[93m[WARN] {text}\033[0m", end=end, flush=False)

    @staticmethod
    def error(text, end="\n"):
        if end != "\n":
            text += "\n"
        print(f"\033[91m[ERROR] {text}\033[0m", end=end, flush=False)
