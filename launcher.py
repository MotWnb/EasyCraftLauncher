import concurrent.futures
import json
import os
import platform
import subprocess
import sys
import uuid
import jdk_system
import jdk
import requests
import threading
import time
import auth
from requests.adapters import HTTPAdapter


def launch_game(arguments):
    start_time = time.time()
    process = subprocess.Popen(arguments, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               stdin=subprocess.PIPE, text=True)

    while True:
        try:
            current_time = time.time()
            if current_time - start_time > 1:  # 5分钟
                process.stdin.write("System.gc()\n")
                process.stdin.flush()
                start_time = current_time  # 重置计时器

            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        except Exception as e:
            print(e)
    exit_code = process.wait()
    print(f"游戏进程退出代码: {exit_code}")


def main():
    systems = {'win32': 'windows', 'linux': 'linux', 'darwin': 'osx'}
    os_name = systems.get(sys.platform)
    java_path = ""
    cp_list = []
    current_dir = os.getcwd()
    minecraft_dir = os.path.join(current_dir, ".minecraft")
    versions_dir = os.path.join(minecraft_dir, "versions")
    assets_dir = os.path.join(minecraft_dir, "assets")

    adapter = HTTPAdapter(max_retries=5, pool_block=True)
    http = requests.Session()
    http.mount('http://', adapter)
    http.mount('https://', adapter)

    try:
        versions = os.listdir(versions_dir)
        version_choice = input(f"请输入需要启动的版本名称: {versions} ")
        version_json_path = os.path.join(versions_dir, version_choice, f"{version_choice}.json")
        with open(version_json_path, "r") as f:
            version_json = json.load(f)
    except FileNotFoundError:
        print("错误代码：0，找不到版本文件")
        sys.exit(1)
    asset_index = version_json["assetIndex"]
    # 下载JDK
    java_version = str(version_json["javaVersion"]["majorVersion"])
    java = jdk_system.find_java_exe_and_versions_in_all_drives()
    for i in java:
        if java[i] == java_version:
            print(f"JDK{java_version} 已存在")
            java_path = i
            break
    if java_path == "":
        java_path = os.path.join(current_dir, "java", f"jdk{java_version}")
        os.makedirs(java_path)
        jdk_system.download_jdk(jdk.get_download_url(java_version, vendor='Azul'), java_path)
        java_path = os.path.join(java_path, os.listdir(java_path)[0], "bin", "java.exe")
    print(java_path)

    natives_dir = os.path.join(versions_dir, version_choice, version_choice + "-natives")
    with concurrent.futures.ThreadPoolExecutor():
        for library in version_json["libraries"]:
            save_path = os.path.join(current_dir, ".minecraft/libraries", library["downloads"]["artifact"]["path"])
            if "rules" in library and any(
                    rule["action"] == "allow" and rule["os"]["name"] == os_name for rule in library["rules"]):
                cp_list.append(save_path)
            elif "rules" not in library:
                cp_list.append(save_path)

    cp_str = cp_list[0]
    del cp_list[0]
    for i in cp_list:
        cp_str += ";" + i
    cp_str += ";" + os.path.join(versions_dir, version_choice, f"{version_choice}.jar")
    cp_str = cp_str.replace("/", "\\")

    # UUID and player data handling
    while True:
        answer = input("请输入\n1. 使用离线登录\n2. 使用正版登录\n")
        if answer == "1":
            username = input("请输入用户名:")
            uid = str(uuid.uuid4())
            access_token = uid
            break
        elif answer == "2":
            uid, username, access_token = auth.perform_ms_login()
            break
    players_json = {}
    players_file_path = os.path.join(minecraft_dir, "players.json")

    if os.path.exists(players_file_path) and os.path.getsize(players_file_path) > 0:
        with open(players_file_path, "r") as f:
            players_json = json.load(f)

    if username in players_json:
        uid = players_json[username]["uuid"].replace('-', '')
    else:
        players_json[username] = {"uuid": uid}

    with open(players_file_path, "w") as f:
        json.dump(players_json, f, indent=4)

    # Launch game
    with open(version_json_path, "r") as f:
        version_json = json.load(f)

    arguments_jvm = ""
    for i in version_json['arguments']['jvm']:
        if isinstance(i, str):
            if '-' in i:
                if '-cp' in i:
                    arguments_jvm += "-cp ${classpath}\n"
                else:
                    arguments_jvm += i + "\n"
    arguments_jvm = arguments_jvm.replace("${natives_directory}", natives_dir)
    arguments_jvm = arguments_jvm.replace("${launcher_name}", "ECL")
    arguments_jvm = arguments_jvm.replace("${launcher_version}", "1.0.0-PREVIEW")
    arguments_jvm = arguments_jvm.replace("${classpath}", cp_str)
    arguments_jvm = arguments_jvm.replace("\n", " ")
    argument_game = f"net.minecraft.client.main.Main --username {username} --version {version_choice} --gameDir {minecraft_dir}\\{version_choice} --assetsDir {assets_dir} --assetIndex {asset_index['id']} --uuid {uid} --clientId 114514 --accessToken {access_token} --userType msa --versionType ECL"
    arguments = arguments_jvm + argument_game
    arguments = f'"{java_path}" {arguments}'

    with open("launcher.bat", "w+") as f:
        f.write(arguments)

    game_thread = threading.Thread(target=launch_game, args=(arguments,))
    print("正在启动游戏......")
    game_thread.start()
