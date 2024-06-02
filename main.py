from downloader import download_minecraft_version
from launcher import main as m


def main():
    choice = input("请输入你想要执行的项目(请输入对应的序号)\n"
                   "1.下载版本与依赖\n"
                   "2.启动游戏\n"
                   "请选择:")
    match int(choice):
        case 1:
            download_minecraft_version()
        case 2:
            m()


if __name__ == '__main__':
    while True:
        main()
