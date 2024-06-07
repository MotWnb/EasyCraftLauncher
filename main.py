from downloader import download_minecraft_version as d
from launcher import main as l


def main():
    choice = input("请输入你想要执行的项目(请输入对应的序号)\n"
                   "1.下载版本与依赖\n"
                   "2.启动游戏\n"
                   "请选择:")
    match int(choice):
        case 1:
            d()
        case 2:
            l()


if __name__ == '__main__':
    while True:
        main()
