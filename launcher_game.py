import json
import os
import platform
import zipfile


def get_system_type():
    if os.name == 'nt':  # 检查是否为Windows系统
        system_type = 'windows'
    else:
        # 对于非Windows系统，使用platform.system()
        system_type = platform.system().lower()

    if system_type == 'linux':
        return 'linux'
    elif system_type == 'windows':
        return 'windows'
    elif system_type == 'darwin':
        return 'osx'
    else:
        return 'unknown'


def get_system_architecture():
    os_name = platform.system().lower()

    if os_name == 'linux':
        return 'linux.'
    elif os_name == 'darwin':  # macOS
        cpu_arch = platform.processor()
        if cpu_arch == 'arm':
            return 'macos-arm64.'
        else:
            return 'macos.'
    elif os_name == 'windows':  # Windows
        arch = platform.machine().lower()
        if arch == 'amd64':
            return 'windows.'
        elif arch == 'arm64':
            return 'windows-arm64.'
        elif arch == 'x86':
            return 'windows-x86.'
        else:
            return 'windows.'  # 默认返回 windows，以防其他未知架构
    else:
        return 'unknown'


def unzip_jar(jar_file_path, destination_folder):
    # 确保目标目录存在，如果不存在，则创建它
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    with zipfile.ZipFile(jar_file_path, 'r') as jar:
        # 列出jar文件中的所有文件
        list_of_files = jar.namelist()

        # 过滤掉META-INF文件夹以及它里面的所有文件和所有目录
        files_to_extract = [f for f in list_of_files if not f.startswith('META-INF/') and not f.endswith('/')]

        # 提取文件到指定文件夹
        for file_info in files_to_extract:
            # 从jar文件中读取文件内容
            file_data = jar.read(file_info)

            # 构建目标文件的完整路径
            destination_file_path = os.path.join(destination_folder, os.path.basename(file_info))

            # 确保目标文件所在的目录存在
            os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)

            # 将文件写入到目标文件夹
            with open(destination_file_path, 'wb') as dest_file:
                dest_file.write(file_data)


# 定义一个函数，用于启动游戏
def launcher_game(version_choice, minecraft_folder):
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
    # 检测系统类型(linux/windows/osx)
    sys_typ = get_system_type()
    sys_arc = get_system_architecture()
    version_json = json.load(open(version_json_file_path, "r", encoding="utf-8"))
    for i in version_json["libraries"]:
        if "rules" in i:
            for f in i["rules"]:
                if f["action"] == "allow":
                    if sys_arc in i["downloads"]["artifact"]["path"]:
                        library_file_path = os.path.join(libraries_folder,
                                                         i["downloads"]["artifact"]["path"])
                        unzip_jar(library_file_path, native_folder)

