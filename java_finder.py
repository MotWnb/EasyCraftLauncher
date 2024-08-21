import os
import platform

def find_java_executable():
    java_paths = []

    # Windows 系统
    if platform.system() == 'Windows':
        # 获取系统环境变量中的路径
        env_paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in env_paths:
            if os.path.exists(os.path.join(path, 'java.exe')):
                java_paths.append(os.path.join(path, 'java.exe'))

        drives = ['{}:\\'.format(d) for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists('{}:\\'.format(d))]
        for drive in drives:
            for root, dirs, files in os.walk(drive):
                if 'java.exe' in files:
                    java_paths.append(os.path.join(root, 'java.exe'))
                depth = root[len(drive):].count(os.sep)
                if depth >= 3:
                    break
    # Linux 和 macOS 系统
    else:
        # 检查常见路径
        common_paths = [
            '/usr/bin',
            '/usr/local/bin',
            os.path.expanduser('~/bin')
        ]
        for path in common_paths:
            if os.path.exists(os.path.join(path, 'java')):
                java_paths.append(os.path.join(path, 'java'))

        for root, dirs, files in os.walk('/'):
            if 'java' in files:
                java_paths.append(os.path.join(root, 'java'))
            depth = root.count(os.sep)
            if depth >= 3:
                break

    return java_paths

java_paths = find_java_executable()
if java_paths:
    for path in java_paths:
        print(f"Java executable found at: {path}")
else:
    print("Java executable not found.")