import os
import shutil
import subprocess
import logging
import threading
from pathlib import Path

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)



# 创建并启动线程的函数
def find_java_exe_and_versions_in_all_drives(desired_version):
    results = {}
    found = threading.Event()  # 事件对象用于通知线程停止

    def scan_drive(drive):
        for root, dirs, files in os.walk(drive):
            if found.is_set():  # 如果事件被设置，则停止扫描
                break
            if 'java.exe' in files and '$' not in root:
                java_exe_path = os.path.join(root, 'java.exe')
                try:
                    output = subprocess.check_output([java_exe_path, '-version'], stderr=subprocess.STDOUT, text=True)
                    version_info = output.strip().split('\n')
                    for line in version_info:
                        if 'version' in line.lower():
                            version = line.split()[2].replace('"', '').split('.')[0]
                            if version == desired_version:
                                results[java_exe_path] = version
                                found.set()  # 设置事件，通知其他线程停止扫描
                                break
                except subprocess.CalledProcessError:
                    pass  # 可以添加日志记录错误，但不要中断程序的执行

    drives = [f"{drive}:" for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{drive}:").exists()]

    threads = [threading.Thread(target=scan_drive, args=(drive,)) for drive in drives]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

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
