import os
import re
import subprocess
import sys

import jdk

from printer import Printer

printer = Printer()


def find_java_executable_with_version(version):
    # 定义搜索路径
    search_paths = os.environ['PATH'].split(os.pathsep)

    # Linux和macOS系统的回收站通常不在文件系统路径中，所以不需要特别处理
    # 但是，如果需要考虑特定于Linux或macOS的回收站目录，可以在这里添加逻辑

    # 定义搜索深度和文件名
    max_depth = 3
    java_executables = ['java', 'java.exe']

    # 搜索Java可执行文件
    for path in search_paths:
        for root, dirs, files in os.walk(path, topdown=True):
            # 跳过回收站目录（如果适用）
            if os.path.basename(root) == '$Recycle.Bin':
                continue

            # 限制搜索深度
            depth = root[len(path):].count(os.sep)
            if depth > max_depth:
                dirs[:] = []
                continue
            for file in files:
                if file in java_executables:
                    java_executable = os.path.join(root, file)
                    major_version = get_java_major_version(java_executable)
                    if major_version == version:
                        return java_executable
    return None


def get_java_major_version(java_executable):
    try:
        # 获取Java版本信息
        result = subprocess.run([java_executable, '-version'], stderr=subprocess.PIPE, text=True)
        # 解析版本信息
        version_output = result.stderr
        version_match = re.search(r'version "(.*?)"', version_output)
        if version_match:
            version = version_match.group(1)
            # 提取大版本号
            version_parts = version.split('.')
            major_version = version_parts[0]
            # 处理特殊版本号，如1.8.0 -> 8
            if major_version == '1' and len(version_parts) > 1:
                major_version = version_parts[1]
            # 处理beta版本号，如24-beta -> 24
            if '-' in major_version:
                major_version = major_version.split('-')[0]
            return major_version
    except Exception as e:
        pass
    return None


def main(version):
    java_executable = ""
    ecl_folder = os.path.join(os.getcwd(), "ECL")
    ecl_java = str(os.path.join(ecl_folder, "java", version))
    if not os.path.exists(ecl_java):
        java_executable = find_java_executable_with_version(version)
        if java_executable:
            return java_executable
        else:
            os.makedirs(ecl_java, exist_ok=True)
            jdk.install(version, path=ecl_java, vendor="Azul")
    for i in os.listdir(ecl_java):
        java_executable = str(os.path.join(ecl_java, i, "bin", "java.exe"))
    printer.info(f"已找到java{version}:{java_executable}")
    return java_executable


if __name__ == '__main__':
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        version = '8'  # 默认版本号
    main(version)
