from downloader import download_minecraft_version as d
from launcher import main as l
import os


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
    ecl_folder = "ECL"
    init_name = "init.successfully"
    init_path = os.path.join(ecl_folder, init_name)
    if os.path.exists(init_path):
        while True:
            main()
    else:
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
        with open(launcher_profiles_path, "w") as f:
            f.write(str(launcher_profiles))
        '''新建init文件'''
        with open(init_path, "w") as f:
            f.write("")
