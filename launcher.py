import shutil
import zipfile
import os
import sys
import json
import requests
import platform
import uuid
from requests.adapters import HTTPAdapter



def get_os_bits():
    return 'x64' if platform.machine().endswith('64') else 'x32'


def get_os_name():
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform.startswith('darwin'):
        return 'osx'
    else:
        print("#Warning# 未知的操作系统类型,将无法自动解压natives文件")
        sys.exit(1)


def download_file(url_download, save_path_download):
    response = http.get(url_download, verify=False)
    save_path_download = os.path.join(current_dir, save_path_download)
    dir_name = os.path.dirname(save_path_download)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(save_path_download, 'wb') as f:
        f.write(response.content)
    print("下载完成 " + save_path_download)


def extract_files(library, version_choice, natives_dir):
    save_path = library["downloads"]["artifact"]["path"]
    save_path = os.path.join(current_dir, ".minecraft/libraries", save_path)
    with zipfile.ZipFile(save_path, 'r') as jar:
        for file_info in jar.infolist():
            if file_info.filename.startswith('META-INF/') or file_info.filename.endswith('/'):
                continue
            if arch not in file_info.filename:
                continue
            filename = os.path.basename(file_info.filename)
            extract_path = os.path.join(natives_dir, filename)
            dir_name = os.path.dirname(extract_path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            source = jar.open(file_info)
            target = open(extract_path, 'wb')
            with source, target:
                shutil.copyfileobj(source, target)


if __name__ == "__main__":
    arch = get_os_bits()
    os_name = get_os_name()
    current_dir = os.getcwd()
    minecraft_dir = os.path.join(current_dir, ".minecraft")
    versions_dir = os.path.join(minecraft_dir, "versions")

    adapter = HTTPAdapter(max_retries=5, pool_block=True)
    http = requests.Session()
    http.mount('http://', adapter)
    http.mount('https://', adapter)

    versions = os.listdir(versions_dir)
    version_choice = "1.20.4"
    # version_choice = input(f"请输入需要启动的版本名称: {str(versions)} ")
    version_json_path = os.path.join(versions_dir, version_choice, f"{version_choice}.json")
    with open(version_json_path, "r") as f:
        version_json = json.load(f)

    # natives_dir = os.path.join(versions_dir, version_choice, f"{version_choice}-natives")
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     for library in version_json["libraries"]:
    #         if "rules" in library:
    #             for rule in library["rules"]:
    #                 if rule["action"] == "allow" and rule["os"]["name"] == os_name:
    #                     executor.submit(extract_files, library, version_choice, natives_dir)
    # 自动生成离线版UUID并储存到players.json
    # username = input("请输入用户名:")
    username = "Breaker"
    uuid = uuid.uuid4()
    with open(os.path.join(minecraft_dir, "players.json"), "w") as f:
        players_json = json.load(f)
        if username in players_json:
            uuid = players_json[username]["id"]
        else:
            players_json[username] = {"id": str(uuid), "name": username}
            json.dump(players_json, f, indent=4)
        f.close()
    



