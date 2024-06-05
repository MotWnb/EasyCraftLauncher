import concurrent.futures
import shutil
import zipfile
import os
import sys
import json
import requests
import platform
import uuid
import subprocess
from requests.adapters import HTTPAdapter


def get_os_bits():
    return 'x64' if platform.machine().endswith('64') else 'x32'


def get_os_platforms():
    return 'x64' if platform.machine().endswith('64') else 'x86'


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


def extract_files(save_path, natives_dir, arch):
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
    global username_arguments_game, version_arguments_game, game_dir_arguments_game, index_arguments_game, assets_dir_arguments_game, uuid_arguments_game, clientid_arguments_game, access_token_arguments_game, user_type_arguments_game, version_type_arguments_game
    jvm_params = ""
    cp_list = []
    arch = get_os_bits()
    os_name = get_os_name()
    current_dir = os.getcwd()
    minecraft_dir = os.path.join(current_dir, ".minecraft")
    versions_dir = os.path.join(minecraft_dir, "versions")
    assets_dir = os.path.join(minecraft_dir, "assets")

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
            save_path = str(os.path.join(current_dir, ".minecraft/libraries", library["downloads"]["artifact"]["path"]))
            if "rules" in library:
                for rule in library["rules"]:
                    if rule["action"] == "allow" and rule["os"]["name"] == os_name:
                        cp_list.append(save_path)
                        executor.submit(extract_files, save_path, natives_dir, arch)
            else:
                cp_list.append(save_path)
    cp_str = cp_list[0]
    del cp_list[0]
    for i in cp_list:
        cp_str = cp_str + ";" + i
    cp_str = cp_str + ";" + str(os.path.join(versions_dir, version_choice, f"{version_choice}.jar"))
    cp_str = cp_str.replace("/", "\\")
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
    version_json_path = os.path.join(minecraft_dir, "versions", version_choice, f"{version_choice}.json")
    with open(version_json_path, "r") as f:
        version_json = json.load(f)
    with open("arguments_jvm.properties", "w+") as f:
        for i in range(len(version_json['arguments']['jvm'])):
            if type(version_json["arguments"]["jvm"][i]) == dict:
                if "arch" in version_json["arguments"]["jvm"][i]["rules"][0]["os"]:
                    if get_os_platforms() == version_json["arguments"]["jvm"][i]["rules"][0]["os"]["arch"]:
                        f.write("-Xss1M\n")
                    continue
                if "osx" in version_json["arguments"]["jvm"][i]["rules"][0]["os"]["name"]:
                    if get_os_name() == version_json["arguments"]["jvm"][i]["rules"][0]["os"]["name"]:
                        f.write("-XstartOnFirstThread\n")
                    continue
                if "windows" in version_json["arguments"]["jvm"][i]["rules"][0]["os"]["name"]:
                    if get_os_name() == version_json["arguments"]["jvm"][i]["rules"][0]["os"]["name"]:
                        if version_json["arguments"]["jvm"][i][
                            "value"] == ("-XX:HeapDumpPath=MojangTricksIntelDriversForPerformance_javaw.exe_minecraft"
                                         ".exe.heapdump"):
                            f.write(
                                "-XX:HeapDumpPath=MojangTricksIntelDriversForPerformance_javaw.exe_minecraft.exe"
                                ".heapdump\n")
                    continue
        f.write("-XX:+UseG1GC\n")
        f.write("-XX:-OmitStackTraceInFastThrow\n")
        for jvm_arguments in version_json["arguments"]["jvm"]:
            if isinstance(jvm_arguments, str):
                if '-' in jvm_arguments:
                    if '-cp' in jvm_arguments:
                        f.write("-cp ${classpath}\n")
                    else:
                        f.write(jvm_arguments + "\n")

    with open("arguments_game.properties", "w+") as f:
        for game_arguments in version_json["arguments"]["game"]:
            if isinstance(game_arguments, str):
                if '-' in game_arguments:
                    f.write(game_arguments + "\n")

    with open("arguments_jvm.properties", "r") as f:
        arguments_jvm = f.read()
    arguments_jvm = arguments_jvm.replace("${natives_directory}", '"' + natives_dir + '"')
    arguments_jvm = arguments_jvm.replace("${launcher_name}", "ECL")
    arguments_jvm = arguments_jvm.replace("${launcher_version}", "1.0.0-PREVIEW")
    arguments_jvm = arguments_jvm.replace("${classpath}", cp_str)
    arguments_jvm = arguments_jvm.replace("\n", " ")

    with open("arguments_game.properties", "r") as f:
        arguments_game_list = f.readlines()
    for arguments_game in arguments_game_list:
        if arguments_game == "--username\n":
            username_arguments_game = "--username " + username + " "
        if arguments_game == "--version\n":
            version_arguments_game = "--version " + version_choice + " "
        if arguments_game == "--gameDir\n":
            game_dir_arguments_game = "--gameDir " + minecraft_dir + "\\" + version_choice + " "
        if arguments_game == "--assetsDir\n":
            assets_dir_arguments_game = "--assetsDir " + assets_dir + " "
        if arguments_game == "--assetIndex\n":
            index_arguments_game = "--assetIndex " + version_choice + " "
        if arguments_game == "--uuid\n":
            uuid_arguments_game = "--uuid " + uid.replace("-", "") + " "
        if arguments_game == "--clientId\n":
            clientid_arguments_game = "--clientId " + "114514" + " "
        if arguments_game == "--accessToken\n":
            access_token_arguments_game = "--accessToken " + uid.replace("-", "") + " "
        if arguments_game == "--userType\n":
            user_type_arguments_game = "--userType msa" + " "
        if arguments_game == "--versionType\n":
            version_type_arguments_game = "--versionType ECL" + " "
    argument_game = "net.minecraft.client.main.Main" + username_arguments_game + version_arguments_game + game_dir_arguments_game + assets_dir_arguments_game + index_arguments_game + uuid_arguments_game + clientid_arguments_game + access_token_arguments_game + user_type_arguments_game + version_type_arguments_game
    arguments = arguments_jvm + argument_game
    print(arguments)
    java_version = str(version_json["javaVersion"]["majorVersion"])
    java_path = os.path.join(current_dir, "java", "jdk" + java_version)
    entries = os.listdir(java_path)[0]
    java_path = os.path.join(java_path, entries, "bin", "java.exe")