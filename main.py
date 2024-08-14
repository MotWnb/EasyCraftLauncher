import json
import os

import download_game
import launcher_game


def main():
    # 检测目录下是否有ECL文件夹
    if not os.path.exists("ECL/ok"):
        if not os.path.exists("ECL"):
            os.mkdir("ECL")
        minecraft_folder = input(
            "请输入.minecraft文件夹的路径\n1.指定.minecraft文件夹的路径\n2.使用默认路径("
            "即在当前目录下创建.minecraft文件夹)\n3.使用官方的路径(即C:\\Users\\用户名\\AppData\\Roaming\\.minecraft)")
        if minecraft_folder == "1":
            minecraft_folder = input(
                "请输入.minecraft文件夹的路径,将自动在此文件夹下创建.minecraft文件夹,如输入D:\\ECL:")
            minecraft_folder = minecraft_folder + "\\.minecraft"
        elif minecraft_folder == "2":
            minecraft_folder = os.getcwd() + "\\.minecraft"
        elif minecraft_folder == "3":
            minecraft_folder = os.path.expandvars("%APPDATA%\\.minecraft")
        if not os.path.exists(minecraft_folder):
            os.mkdir(minecraft_folder)
        with open("ECL/ecl.config", "w") as f:
            json.dump({"minecraft_folder": minecraft_folder}, f)
        with open("ECL/ok", "w"):
            pass
    config = json.load(open("ECL/ecl.config"))
    config["ECL_version"] = "0.0.1"
    minecraft_folder = config["minecraft_folder"]
    json.dump(config, open("ECL/ecl.config", "w"))
    user_choice = input("请输入你需要的选项\n1.下载游戏\n2.启动游戏")
    if user_choice == "1":
        download_choice = input("请输入你需要的下载选项\n1.下载指定游戏版本\n2.下载最新测试版本\n3.下载最新正式版本")
        download_game.download_game(download_choice)
    if user_choice == "2":
        items = []
        path = os.path.join(minecraft_folder, "versions")
        if not os.path.exists(path):
            print("未找到.minecraft文件夹")
            exit(1)
        for item in os.listdir(path):
            # 检查每个项是否是文件夹
            if os.path.isdir(os.path.join(path, item)):
                items.append(item)

        start_choice = input("请输入你需要启动的游戏版本" + str(items))
        launcher_game.launcher_game(start_choice)


if __name__ == "__main__":
    main()
