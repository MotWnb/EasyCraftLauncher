import concurrent.futures
import json
import os
import platform
import shutil
import subprocess
import sys
import uuid
import zipfile
import requests
from requests.adapters import HTTPAdapter


def get_arch():
    return 'x64' if platform.machine().endswith('64') else 'x86'


def get_os():
    systems = {'win32': 'windows', 'linux': 'linux', 'darwin': 'osx'}
    os_name = systems.get(sys.platform)
    if not os_name:
        print("错误代码：2，未知的操作系统类型,将无法自动解压natives文件")
        sys.exit(1)
    return os_name


def extract_files(save_path, natives_dir, arch):
    with zipfile.ZipFile(save_path, 'r') as jar:
        for info in jar.infolist():
            if not info.filename.startswith('META-INF/') and arch in info.filename:
                filename = os.path.basename(info.filename)
                extract_path = os.path.join(natives_dir, filename)
                if not os.path.exists(os.path.dirname(extract_path)):
                    os.makedirs(os.path.dirname(extract_path))
                with jar.open(info) as source, open(extract_path, 'wb') as target:
                    shutil.copyfileobj(source, target)


def main():
    jvm_params = []
    cp_list = []
    arch = get_arch()
    os_name = get_os()
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

    natives_dir = os.path.join(versions_dir, version_choice, version_choice + "-natives")
    with concurrent.futures.ThreadPoolExecutor(max_workers=192) as executor:
        for library in version_json["libraries"]:
            save_path = os.path.join(current_dir, ".minecraft/libraries", library["downloads"]["artifact"]["path"])
            if "rules" in library and any(
                    rule["action"] == "allow" and rule["os"]["name"] == os_name for rule in library["rules"]):
                cp_list.append(save_path)
                executor.submit(extract_files, save_path, natives_dir, arch)
            elif "rules" not in library:
                cp_list.append(save_path)

    cp_str = cp_list[0]
    del cp_list[0]
    for i in cp_list:
        cp_str += ";" + i
    cp_str += ";" + os.path.join(versions_dir, version_choice, f"{version_choice}.jar")
    cp_str = cp_str.replace("/", "\\")

    # UUID and player data handling
    username = input("请输入用户名:")
    uid = str(uuid.uuid4())
    players_json = {}
    players_file_path = os.path.join(minecraft_dir, "players.json")

    if os.path.exists(players_file_path) and os.path.getsize(players_file_path) > 0:
        with open(players_file_path, "r") as f:
            players_json = json.load(f)

    if username in players_json:
        uid = players_json[username]["uuid"]
    else:
        players_json[username] = {"uuid": uid}

    with open(players_file_path, "w") as f:
        json.dump(players_json, f, indent=4)

    # Launch game
    with open(version_json_path, "r") as f:
        version_json = json.load(f)

    with open("arguments_jvm.properties", "w+") as f:
        for i in version_json['arguments']['jvm']:
            if isinstance(i, str):
                if '-' in i:
                    if '-cp' in i:
                        f.write("-cp ${classpath}\n")
                    else:
                        f.write(i + "\n")

    with open("arguments_game.properties", "w+") as f:
        for game_arguments in version_json["arguments"]["game"]:
            if isinstance(game_arguments, str):
                if '-' in game_arguments:
                    f.write(game_arguments + "\n")

    with open("arguments_jvm.properties", "r") as f:
        arguments_jvm = f.read()
    arguments_jvm = arguments_jvm.replace("${natives_directory}", natives_dir)
    arguments_jvm = arguments_jvm.replace("${launcher_name}", "ECL")
    arguments_jvm = arguments_jvm.replace("${launcher_version}", "1.0.0-PREVIEW")
    arguments_jvm = arguments_jvm.replace("${classpath}", cp_str)
    arguments_jvm = arguments_jvm.replace("\n", " ")

    with open("arguments_game.properties", "r") as f:
        arguments_game_list = f.readlines()
    argument_game = "net.minecraft.client.main.Main "
    for arguments_game in arguments_game_list:
        if arguments_game.startswith("--"):
            argument_game += arguments_game.strip() + " "
    argument_game += f"--username {username} --version {version_choice} --gameDir {minecraft_dir}\\{version_choice} --assetsDir {assets_dir} --assetIndex {version_choice} --uuid {uid.replace('-', '')} --clientId 114514 --accessToken {uid.replace('-', '')} --userType msa --versionType ECL"

    arguments = arguments_jvm + argument_game
    java_version = version_json["javaVersion"]["majorVersion"]
    java_path = os.path.join(current_dir, "java", f"jdk{java_version}")
    entries = os.listdir(java_path)[0]
    java_path = os.path.join(java_path, entries, "bin", "java.exe")
    arguments = f'"{java_path}" {arguments}'

    with open("launcher.bat", "w+") as f:
        f.write(arguments)

    process = subprocess.Popen("launcher.bat", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())

    exit_code = process.wait()
    print(f"批处理文件退出代码: {exit_code}")
