import os
import shutil
import subprocess
import logging
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)


# 定义一个线程函数，用于遍历指定盘符的所有目录
def scan_drive(drive, results):
    for root, dirs, files in os.walk(drive):
        # 找java.exe并排除回收站文件夹
        if 'java.exe' in files and '$' not in root:
            java_exe_path = root + '\\java.exe'
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
                print("错误代码：1，无法获取Java版本信息:", e.output.decode('utf-8'))


# 创建并启动线程的函数
def find_java_exe_and_versions_in_all_drives():
    drives = ['%s:\\' % d for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists('%s:' % d)]

    # 创建一个字典来存储结果
    results = {}

    # 创建线程列表
    threads = [threading.Thread(target=scan_drive, args=(drive, results)) for drive in drives[:192]]

    # 启动线程
    for thread in threads:
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    # 输出结果字典
    return results



def download_range(url, start, end, filename):
    headers = {'Range': f'bytes={start}-{end}'}
    req = requests.get(url, headers=headers, stream=True)
    with open(filename, 'wb') as fp:
        for chunk in req.iter_content(chunk_size=8192):
            if chunk:
                fp.write(chunk)
    print(f"Part downloaded: {filename}")


def download_jdk(url, install_path):
    url = url.replace("https://", "http://")
    num_threads = os.cpu_count()
    # 获取文件总大小
    req = requests.head(url)
    file_size = int(req.headers.get('content-length', 0))
    # 分割文件
    filename = urlsplit(url).path.split('/')[-1]
    part_size = file_size // num_threads
    print(part_size)
    futures = []

    # 创建线程池
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        for i in range(num_threads):
            start = part_size * i
            end = start + part_size if i < num_threads - 1 else file_size - 1
            part_filename = f"{filename}.part{i}"
            futures.append(executor.submit(download_range, url, start, end, part_filename))

        # 等待所有线程完成
        for future in as_completed(futures):
            pass

    # 合并文件
    with open(filename, 'wb') as fp:
        for i in range(num_threads):
            part_filename = f"{filename}.part{i}"
            with open(part_filename, 'rb') as part_fp:
                shutil.copyfileobj(part_fp, fp)
            os.remove(part_filename)
    shutil.unpack_archive(filename, install_path, format='zip')
    os.remove(filename)

# 遍历所有盘符并输出Java版本
# find_java_exe_and_versions_in_all_drives()
