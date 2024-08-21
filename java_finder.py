import os

def search_all_java_exe(max_depth=3):
    found_paths = []

    # 获取系统环境变量中的路径，并过滤掉空字符串
    paths = [p for p in os.environ["PATH"].split(os.pathsep) if p]

    # 直接检查文件是否存在，而不是遍历整个目录
    for path in paths:
        java_exe_path = os.path.join(path, 'java.exe')
        if os.path.isfile(java_exe_path):
            found_paths.append(java_exe_path)

    # 搜索每个盘符下的路径，限制搜索深度
    drives = ['%s:\\' % d for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists('%s:' % d)]
    for drive in drives:
        for root, dirs, files in os.walk(drive, topdown=True):
            if 'java.exe' in files:
                found_paths.append(os.path.join(root, 'java.exe'))
            # 限制目录深度
            if root.count(os.sep) - drive.count(os.sep) >= max_depth:
                dirs[:] = []  # 不再深入搜索

    return found_paths if found_paths else "No java.exe found in the system paths or drives within 3 levels."

print(search_all_java_exe())
