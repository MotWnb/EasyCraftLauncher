import os
import json


def java_settings(settings):
    is_java_auto = settings["auto"]
    java_choice = settings["java_choice"]
    choice = input("请选择你需要的\n1.java选择\n2.重置java设置\n3.查看当前的java设置\n4.退出\n")
    if choice == "1":
        is_java_auto = False
        game_version = input("请输入需要设置的游戏版本(例如: 1.8.9)\n")
        for i in java_choice:
            if i == game_version:
                i = settings[i]
                print(f"版本 {game_version} 当前设置的java为 {i}")
        java_path = input("请输入java路径(例如: E:\\java\\bin\\java.exe)\n")
        java_choice[game_version] = java_path
    elif choice == "2":
        is_java_auto = True
        java_choice = {}

    elif choice == "3":
        if is_java_auto:
            print("当前的java设置为: 自动选择")
        else:
            for i in java_choice:
                print(f"版本 {i} 当前设置的java为: {java_choice[i]}")
    else:
        print("无效选项")
    java = {"auto": is_java_auto, "java_choice": java_choice}
    return java


def download_settings(settings):
    thread_count = settings["download_settings"]["thread_count"]
    download_source = settings["download_settings"]["download_source"]
    choice = input("请选择你需要的\n1.手动设置下载线程数而不是无限制\n2.设置使用的源(官方或BMCLAPI)\n3.退出\n")
    if choice == "1":
        pass

    elif choice == "2":
        pass

    elif choice == "3":
        exit()
    else:
        print("无效选项")
        download_settings(settings)


def main_settings():
    ecl_folder = "ECL"
    settings_path = os.path.join(ecl_folder, "settings.json")
    if not os.path.exists(settings_path):
        print("找不到设置文件,请尝试删除ECL文件夹中的init文件后重新运行")
        exit()
    else:
        settings_json = open(settings_path, "r+")
        settings = json.load(settings_json)
        java = settings["java_settings"]
    choice = input("请选择你需要设置的选项\n1.java设置\n2.下载设置\n3.退出\n")
    if choice == "1":
        set_java = java_settings(java)
        settings["java_settings"] = set_java
        settings_json.seek(0)
        settings_json.write(json.dumps(settings, indent=4))
        settings_json.close()
        main_settings()
    elif choice == "2":
        download_settings(settings)
        main_settings()
    elif choice == "3":
        pass
    else:
        print("无效选项")
        main_settings()
