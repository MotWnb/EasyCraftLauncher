import concurrent.futures
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


def extract_files(library, natives_dir, current_dir, arch):
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


def main():
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
    version_choice = input(f"请输入需要启动的版本名称: {str(versions)} ")
    version_json_path = os.path.join(versions_dir, version_choice, f"{version_choice}.json")
    with open(version_json_path, "r") as f:
        version_json = json.load(f)

    natives_dir = os.path.join(versions_dir, version_choice, f"{version_choice}-natives")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for library in version_json["libraries"]:
            if "rules" in library:
                for rule in library["rules"]:
                    if rule["action"] == "allow" and rule["os"]["name"] == os_name:
                        executor.submit(extract_files, library, natives_dir, current_dir, arch)
    # 自动生成离线版UUID并储存到players.json
    username = input("请输入用户名:")
    uid = uuid.uuid4()
    players_json = {}
    players_file_path = os.path.join(minecraft_dir, "players.json")

    # 检查文件是否存在且不为空
    if os.path.exists(players_file_path) and os.path.getsize(players_file_path) > 0:
        with open(players_file_path, "r") as f:
            players_json = json.load(f)

    # 处理用户名和UUID
    if username in players_json:
        uid = players_json[username]["uuid"]
    else:
        players_json[username] = {"uuid": str(uid)}

    # 将更新后的数据写回文件
    with open(players_file_path, "w") as f:
        json.dump(players_json, f, indent=4)

    # 启动游戏
