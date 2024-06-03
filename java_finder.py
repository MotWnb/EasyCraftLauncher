import os
import subprocess
import threading


# 定义一个线程函数，用于遍历指定盘符的所有目录
def scan_drive(drive, results):
    for root, dirs, files in os.walk(drive):
        if 'java.exe' in files:
            java_exe_path = os.path.join(root, 'java.exe')
            try:
                # 执行java.exe -version命令并捕获输出
                output = subprocess.check_output([java_exe_path, '-version'], stderr=subprocess.STDOUT, text=True)
                # 提取版本信息
                version_lines = output.strip().split('\n')
                for line in version_lines:
                    if 'version' in line.lower():
                        # 提取主版本号
                        version = line.split()[2].replace('"', '').split('.')[0]
                        # 将结果添加到字典中
                        results[java_exe_path] = version
            except subprocess.CalledProcessError as e:
                print("无法获取Java版本信息:", e.output.decode('utf-8'))


# 创建并启动线程的函数
def find_java_exe_and_versions_in_all_drives():
    drives = ['%s:\\' % d for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists('%s:' % d)]

    # 创建一个字典来存储结果
    results = {}

    # 创建线程列表
    threads = []

    # 为每个盘符创建并启动一个线程
    for drive in drives:
        thread = threading.Thread(target=scan_drive, args=(drive, results))
        thread.start()
        threads.append(thread)

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    # 输出结果字典
    print(results)


# 遍历所有盘符并输出Java版本
find_java_exe_and_versions_in_all_drives()
