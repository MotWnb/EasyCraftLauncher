import json
import os
import platform
import sys
import zipfile


def get_system_type():
    return {
        'nt': 'windows',
        'posix': 'linux',
        'java': 'osx'
    }.get(os.name, 'unknown')


def get_system_arch_type():
    os_name = platform.system().lower()
    arch = platform.machine().lower()
    is_64bits = sys.maxsize > 2 ** 32

    if os_name == 'linux':
        return 'linux'
    elif os_name == 'darwin':
        return 'macos-arm64.' if arch == 'arm' else 'macos.'
    elif os_name == 'windows':
        return {
            'amd64': 'windows.',
            'arm64': 'windows-arm64.',
            'x86': 'windows-x86.',
        }.get(arch, 'windows.')
    else:
        return 'unknown'


def get_system_architecture():
    is_64bits = sys.maxsize > 2 ** 32
    os_name = platform.system().lower()

    if os_name == 'darwin':
        return '64' if is_64bits else 'x86'

    arch = platform.machine().lower()
    if arch in ('amd64', 'x86_64', 'ia64'):
        return '64'
    elif arch in ('i386', 'i686'):
        return 'x86'
    elif arch == 'arm64':
        return 'arm64'
    elif arch.startswith('arm'):
        return 'arm64' if is_64bits else 'x86'

    return '64' if is_64bits else 'x86'


def unzip_jar(jar_file_path, destination_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    with zipfile.ZipFile(jar_file_path, 'r') as jar:
        files_to_extract = [f for f in jar.namelist() if not f.startswith('META-INF/') and not f.endswith('/')]
        for file_info in files_to_extract:
            file_data = jar.read(file_info)
            destination_file_path = os.path.join(destination_folder, os.path.basename(file_info))
            os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)
            with open(destination_file_path, 'wb') as dest_file:
                dest_file.write(file_data)


def launcher_game(version_choice, minecraft_folder):
    system_type = get_system_type()
    system_arch_type = get_system_arch_type()
    system_architecture = get_system_architecture()
    classpath = []
    jvm_arguments = ""
    game_arguments = ""
    folder = os.getcwd()
    ecl_folder = os.path.join(folder, "ecl")
    temp_folder = os.path.join(ecl_folder, "temp")
    bat_file_path = os.path.join(temp_folder, "run.bat")
    version_choice = str(version_choice)
    versions_folder = os.path.join(minecraft_folder, "versions")
    version_folder = os.path.join(versions_folder, version_choice)
    native_folder = os.path.join(version_folder, f"{version_choice}-natives")
    libraries_folder = os.path.join(minecraft_folder, "libraries")
    version_json_file_path = os.path.join(version_folder, f"{version_choice}.json")
    version_jar_file_path = os.path.join(version_folder, f"{version_choice}.jar")

    version_json = json.load(open(version_json_file_path, "r", encoding="utf-8"))
    for i in version_json["libraries"]:
        if "classifiers" in i["downloads"]:
            for j in i["downloads"]["classifiers"]:
                if j == f"natives-{system_type}":
                    library_file_path = os.path.join(libraries_folder, i["downloads"]["classifiers"][j]["path"])
                    classpath.append(library_file_path)
                    unzip_jar(library_file_path, native_folder)
        else:
            library_file_path = os.path.join(libraries_folder, i["downloads"]["artifact"]["path"])
            classpath.append(library_file_path)
            if "rules" in i:
                for f in i["rules"]:
                    if f["action"] == "allow":
                        if system_arch_type in i["downloads"]["artifact"]["path"]:
                            unzip_jar(library_file_path, native_folder)
    classpath.append(version_jar_file_path)
    if "arguments" in version_json:
        for i in version_json["arguments"]["jvm"]:
            if "rules" in i:
                if i["rules"][0]["action"] == "allow":
                    if "arch" in i["rules"][0]["os"]:
                        if i["rules"][0]["os"]["arch"] == system_architecture:
                            jvm_arguments = jvm_arguments + " " + i["value"]
                    if "name" in i["rules"][0]["os"]:
                        if i["rules"][0]["os"]["name"] == system_type:
                            jvm_arguments = jvm_arguments + " " + i["value"]
            else:
                jvm_arguments = jvm_arguments + " " + i
        for i in version_json["arguments"]["game"]:
            if isinstance(i, str):
                game_arguments = game_arguments + " " + i
        jvm_arguments = jvm_arguments.lstrip() + " "
        game_arguments= game_arguments.lstrip()

    if "minecraftArguments" in version_json:
        game_arguments = version_json["minecraftArguments"]

    print(jvm_arguments)
    print(game_arguments)
