import json
import os
import platform
import subprocess
import sys
import threading
import uuid
import zipfile


def generate_uuid_from_string(namespace, string):
    return uuid.uuid5(namespace, string)


def generate_script_file(script_content, script_name):
    # 根据操作系统添加合适的文件扩展名
    extension = '.bat' if get_system_type() == 'windows' else '.sh'
    script_path = script_name + extension
    with open(script_path, 'w') as file:
        file.write(script_content)
    return script_path


def run_command_in_thread(script_path):
    def thread_function(path):
        try:
            # 在新线程中设置当前工作目录
            original_cwd = os.getcwd()
            os.chdir(os.path.dirname(path))  # 改变到脚本所在目录

            if get_system_type() == 'windows':  # Windows
                shell_cmd = ['cmd', '/c', os.path.basename(path)]
            else:  # Unix/Linux/MacOS
                shell_cmd = ['bash', os.path.basename(path)]
                os.chmod(path, 0o755)  # 设置执行权限

            # 设置subprocess.Popen的encoding为utf-8，并使用'replace'来处理无效的字节
            with subprocess.Popen(shell_cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding='utf-8', errors='replace') as process:
                for line in process.stdout:
                    print(line, end='')
                for line in process.stderr:
                    print(line, end='')
                process.wait()

            # 恢复原始工作目录
            os.chdir(original_cwd)
        except Exception as e:
            print(f"An error occurred: {e}")

    thread = threading.Thread(target=thread_function, args=(script_path,))
    thread.start()


def get_system_type():
    return {
        'nt': 'windows',
        'posix': 'linux',
        'java': 'osx'
    }.get(os.name, 'unknown')


def get_system_arch_type():
    os_name = platform.system().lower()
    arch = platform.machine().lower()

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


def determine_version_type(version_str):
    version_parts = [int(part) for part in version_str.split('.')]

    if len(version_parts) < 3:
        return "Invalid version format"

    last_two_parts = version_parts[-2:]

    if last_two_parts[0] != 0 or last_two_parts[1] != 0:
        return "preview"
    else:
        return "release"


def replace_arguments(arguments, replacements):
    for key, value in replacements.items():
        arguments = arguments.replace(key, value)
    return arguments


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


def launcher_game(version_choice):
    config = json.load(open("ECL/ecl.config"))
    minecraft_folder = config["minecraft_folder"]
    ecl_version = config["ECL_version"]
    ecl_type = determine_version_type(ecl_version)
    system_type = get_system_type()
    system_arch_type = get_system_arch_type()
    system_architecture = get_system_architecture()
    classpath = []
    jvm_arguments = ""
    game_arguments = ""
    folder = os.getcwd()
    ecl_folder = os.path.join(folder, "ecl")
    temp_folder = os.path.join(ecl_folder, "temp")
    version_choice = str(version_choice)
    versions_folder = os.path.join(minecraft_folder, "versions")
    version_folder = str(os.path.join(versions_folder, version_choice))
    native_folder = str(os.path.join(version_folder, f"{version_choice}-natives"))
    assets_folder = os.path.join(minecraft_folder, "assets")
    libraries_folder = os.path.join(minecraft_folder, "libraries")
    version_json_file_path = os.path.join(version_folder, f"{version_choice}.json")
    version_jar_file_path = os.path.join(version_folder, f"{version_choice}.jar")

    version_json = json.load(open(version_json_file_path, "r", encoding="utf-8"))
    assets_index_name = version_json["assetIndex"]["id"]
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
        game_arguments = game_arguments.lstrip()

    if "minecraftArguments" in version_json:
        jvm_arguments = "-Djava.library.path=" + native_folder + " " + "-cp" + " " + ";".join(classpath) + " "
        game_arguments = version_json["minecraftArguments"]
    user_name = input("请输入用户名：")
    namespace_uuid = uuid.UUID('12345678-1234-5678-1234-567812345678')

    # 生成UUID
    user_uuid = str(generate_uuid_from_string(namespace_uuid, user_name)).replace('-', '')
    classpath = ";".join(classpath)
    # 定义替换字典
    jvm_replacements = {
        "${natives_directory}": native_folder,
        "${launcher_name}": "ECL",
        "${classpath}": classpath,
        "${launcher_version}": ecl_version
    }

    game_replacements = {
        "${auth_player_name}": user_name,
        "${version_name}": version_choice,
        "${game_directory}": version_folder,
        "${assets_root}": assets_folder,
        "${assets_index_name}": assets_index_name,
        "${auth_uuid}": user_uuid,
        "${auth_access_token}": user_uuid,
        "${user_type}": "msa",
        "${version_type}": ecl_type,
        "${natives_directory}": native_folder,
        "${launcher_name}": "ECL",
        "${launcher_version}": ecl_version,
        "${user_properties}": user_name
    }

    # 使用函数进行替换
    jvm_arguments = replace_arguments(jvm_arguments, jvm_replacements)
    game_arguments = replace_arguments(game_arguments, game_replacements)

    java_path = input("请输入Java路径:")

    command = java_path + " " + jvm_arguments + " net.minecraft.client.main.Main " + game_arguments
    script_name = "run_game"
    script_name = os.path.join(temp_folder, script_name)
    script_path = generate_script_file(command, script_name)

    # 在新线程中运行命令
    run_command_in_thread(script_path)
    print("正在启动游戏......")
