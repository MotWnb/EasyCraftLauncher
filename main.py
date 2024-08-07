import json

from downloader import download_minecraft_version as d
from launcher import main as l
from settings import main_settings as s
import os


def main():
    ecl_folder = "ECL"
    init_name = "init"
    init_path = os.path.join(ecl_folder, init_name)
    if os.path.exists(init_path):
        while True:
            choice = input("请输入你想要选项\n"
                           "1.下载版本与依赖\n"
                           "2.启动游戏\n"
                           "3.设置\n")
            if choice == "1":
                d()
            elif choice == "2":
                l()
            elif choice == "3":
                s()
    else:
        settings_path = os.path.join(ecl_folder, "settings.json")
        folder_path = os.getcwd()
        minecraft_folder = ".minecraft"
        minecraft_folder = os.path.join(folder_path, minecraft_folder)
        asset_folder = "assets"
        asset_folder = os.path.join(minecraft_folder, asset_folder)
        libraries_folder = "libraries"
        libraries_folder = os.path.join(minecraft_folder, libraries_folder)

        launcher_profiles_path = os.path.join(minecraft_folder, "launcher_profiles.json")

        '''开始初始化'''

        '''
        检测py文件的运行路径是否在TEMP文件夹或者download文件夹中
        如果是，弹窗警告用户
        '''
        py_path = os.path.abspath(__file__)
        if "download".lower() in py_path.lower() or "temp".lower() in py_path.lower():
            print("警告：你正在运行的文件在TEMP或download文件夹中，这可能会导致一些问题。")

        '''新建ECL文件夹'''
        os.makedirs(ecl_folder, exist_ok=True)

        '''新建minecraft文件夹及一系列应有的文件夹'''
        os.makedirs(minecraft_folder, exist_ok=True)

        os.makedirs(asset_folder, exist_ok=True)

        os.makedirs(libraries_folder, exist_ok=True)

        '''新建launcher_profiles.json'''
        launcher_profiles = {
            "profiles": {
                "ECL": {
                    "icon": "icon.png",
                    "gameDir": f"{minecraft_folder}",
                    "lastVersionId": "latest-release",
                    "name": "Easy Craft Launcher"
                }
            },
            "settings": {
                "keepLauncherOpen": True,
                "showGameLog": True,
                "version": "1"
            }
        }

        settings_json = {
            "java_settings": {
                "auto": True,
                "java_choice": {}
            },
            "download_settings": {
                "thread_count": os.cpu_count() - 4 if os.cpu_count() - 4 > 0 else 1,
                "download_source": "official"
            }
        }

        with open(launcher_profiles_path, "w") as f:
            json.dump(launcher_profiles, f, indent=4)
        with open(settings_path, 'w') as f:
            # 使用 json.dump() 将字典转换为 JSON 格式并写入文件
            json.dump(settings_json, f, indent=4)
        '''新建init文件'''
        with open(init_path, "w") as f:
            f.write("")


if __name__ == '__main__':
    while True:
        main()
