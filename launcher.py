import concurrent.futures
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
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
            if current_time - start_time > 1:  # Increased to 5 minutes
                process.stdin.write("System.gc()\n")
                process.stdin.flush()
                start_time = current_time  # Reset the timer
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
        except Exception:
            pass


def main():
    systems = {'win32': 'windows', 'linux': 'linux', 'darwin': 'osx'}
    os_name = systems.get(sys.platform)
    minecraft_dir = Path(".minecraft")
    versions_dir = minecraft_dir / "versions"
    assets_dir = minecraft_dir / "assets"

    http = requests.Session()
    http.mount('http://', requests.adapters.HTTPAdapter(max_retries=5, pool_block=True))
    http.mount('https://', requests.adapters.HTTPAdapter(max_retries=5, pool_block=True))

    try:
        versions = os.listdir(versions_dir)
        version_choice = input(f"请输入需要启动的版本名称: {versions} ")
        version_path = versions_dir / version_choice
        version_json_path = versions_dir / version_choice / f"{version_choice}.json"
        with open(version_json_path, "r") as f:
            version_json = json.load(f)
    except FileNotFoundError:
        print("错误代码：0，找不到版本文件")
        sys.exit(1)
    asset_index = version_json["assetIndex"]
    mainclass = version_json["mainClass"]
    # Download JDK
    java_version = str(version_json["javaVersion"]["majorVersion"])
    java_exe_paths = jdk_system.find_java_exe_and_versions_in_all_drives(java_version)

    # Check for the existence of the specified version of Java
    if java_exe_paths:
        print(f"JDK{java_version} 已存在")
        java_path = next(iter(java_exe_paths))  # Return the first found java.exe path
    else:
        # If it does not exist, download and set the Java environment
        java_dir = Path.cwd() / "java" / f"jdk{java_version}"
        java_dir.mkdir(parents=True, exist_ok=True)
        jdk_system.download_jdk(jdk.get_download_url(java_version, vendor='Azul'), str(java_dir))
        java_path = next(java_dir.glob('*')) / 'bin' / 'java.exe'

    natives_dir = versions_dir / version_choice / (version_choice + "-natives")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        cp_list = []
        for library in version_json["libraries"]:
            if "rules" in library and any(
                    rule["action"] == "allow" and rule["os"]["name"] == os_name for rule in library["rules"]):
                save_path = os.path.join(".minecraft", "libraries", library["downloads"]["artifact"]["path"])
                cp_list.append(save_path)
            elif "rules" not in library:
                save_path = os.path.join(".minecraft", "libraries", library["downloads"]["artifact"]["path"])
                cp_list.append(save_path)

    # Join the classpath string
    cp_str = ";".join(cp_list)
    cp_str += ";" + str(versions_dir / version_choice / f"{version_choice}.jar")
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
    players_file_path = minecraft_dir / "players.json"

    if players_file_path.exists() and players_file_path.stat().st_size > 0:
        with open(players_file_path, "r") as f:
            players_json = json.load(f)

    if username in players_json:
        uid = players_json[username]["uuid"].replace('-', '')
    else:
        players_json[username] = {"uuid": uid}

    arguments_jvm = ""
    for i in version_json['arguments']['jvm']:
        if isinstance(i, str):
            if '-' in i:
                if '-cp' in i:
                    arguments_jvm += "-cp ${classpath}\n"
                else:
                    arguments_jvm += i + "\n"
    arguments_jvm = arguments_jvm.replace("${natives_directory}", str(natives_dir))
    arguments_jvm = arguments_jvm.replace("${launcher_name}", "ECL")
    arguments_jvm = arguments_jvm.replace("${launcher_version}", "1.0.0-PREVIEW")
    arguments_jvm = arguments_jvm.replace("${classpath}", cp_str)
    arguments_jvm = arguments_jvm.replace("\n", " ")
    arguments_game = ""

    for i in version_json['arguments']['game']:
        if isinstance(i, str):
            arguments_game += i + " "

    arguments_game = arguments_game.replace("${auth_player_name}", username)
    arguments_game = arguments_game.replace("${version_name}", version_choice)
    arguments_game = arguments_game.replace("${game_directory}", str(version_path))
    arguments_game = arguments_game.replace("${assets_root}", str(assets_dir))
    arguments_game = arguments_game.replace("${assets_index_name}", asset_index['id'])
    arguments_game = arguments_game.replace("${auth_uuid}", uid)
    arguments_game = arguments_game.replace("${auth_access_token}", access_token)
    arguments_game = arguments_game.replace("${user_type}", "msa")
    arguments_game = arguments_game.replace("${version_type}", "release")
    arguments_game = arguments_game.replace("${natives_directory}", str(natives_dir))
    arguments_game = arguments_game.replace("${classpath}", cp_str)
    arguments_game = arguments_game.replace("${launcher_name}", "ECL")
    arguments_game = arguments_game.replace("${launcher_version}", "1.0.0")
    arguments_game = arguments_game.replace("${classpath}", cp_str)

    argument_game = f"{mainclass} {arguments_game}"
    arguments = arguments_jvm + argument_game
    arguments = f'"{java_path}" {arguments}'

    with open("launcher.bat", "w+") as f:
        f.write(arguments)

    game_thread = threading.Thread(target=launch_game, args=(arguments,))
    print("正在启动游戏......")
    game_thread.start()

    if __name__ == "__main__":
        main()
