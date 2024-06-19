import logging
import os
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

import requests

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 定义查找Java执行文件的函数
def find_java_exe_and_versions_in_all_drives(desired_version):
    results = {}
    found = threading.Event()

    def scan_drive(drive):
        with os.scandir(drive) as it:
            for entry in it:
                if found.is_set():
                    return
                if entry.is_file() and entry.name == 'java.exe' and '$' not in entry.path:
                    try:
                        output = subprocess.run([entry.path, '-version'], capture_output=True, text=True, check=True)
                        for line in output.stderr.split('\n'):
                            if 'version' in line.lower():
                                version = line.split()[2].replace('"', '')[0:2]  # 提取版本号的前两位
                                if version == desired_version:
                                    results[entry.path] = version
                                    found.set()
                                    break
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Error running java.exe: {e}")

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
