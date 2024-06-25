import os
import json
import platform
import shutil
import sys

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from zipfile import ZipFile

# 定义常量
CURRENT_DIR = os.getcwd()
MINECRAFT_DIR = os.path.join(CURRENT_DIR, ".minecraft")
LIBRARIES_DIR = os.path.join(MINECRAFT_DIR, "libraries")
VERSIONS_DIR = os.path.join(MINECRAFT_DIR, "versions")
ASSETS_DIR = os.path.join(MINECRAFT_DIR, "assets")
INDEXES_DIR = os.path.join(ASSETS_DIR, "indexes")
OBJECTS_DIR = os.path.join(ASSETS_DIR, "objects")

# 配置请求会话
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=5, pool_maxsize=114514)
session.mount('http://', adapter)
session.mount('https://', adapter)


# 定义下载函数
def download_file(url, save_path):
    response = session.get(url, stream=True)
    response.raise_for_status()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)  # 确保目录存在
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


# 定义解压函数
def extract_files(zip_path, extract_dir, arch):
    with ZipFile(zip_path, 'r') as jar:
        for info in jar.infolist():
            if arch in info.filename and not info.filename.endswith('/'):
                filename = os.path.basename(info.filename)
                extract_path = os.path.join(extract_dir, filename)
                if not os.path.exists(extract_dir):
                    os.makedirs(extract_dir)
                with jar.open(info) as source, open(extract_path, 'wb') as target:
                    shutil.copyfileobj(source, target)


# 主函数
def download_minecraft_version():
    # 下载并读取版本清单文件
    version_manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
    version_manifest_path = os.path.join(CURRENT_DIR, "version_manifest.json")
    if not os.path.exists(version_manifest_path):
        download_file(version_manifest_url, version_manifest_path)
    with open(version_manifest_path, "r") as f:
        version_manifest = json.load(f)

    # 输出最新版本信息并请求用户输入
    version_choice = input("请输入您要下载的版本(例如1.19.4)：")

    # 下载并处理所选版本的文件
    for version in version_manifest["versions"]:
        if version["id"] == version_choice:
            version_json_url = version["url"]
            version_json_path = os.path.join(VERSIONS_DIR, version_choice, f"{version_choice}.json")
            if not os.path.exists(version_json_path):
                download_file(version_json_url, version_json_path)
            with open(version_json_path, "r") as f:
                version_json = json.load(f)

            # 下载客户端文件
            client_download = version_json["downloads"]["client"]
            print(client_download["url"])
            client_path = os.path.join(VERSIONS_DIR, version_choice, f"{version_choice}.jar")
            if not os.path.exists(client_path):
                download_file(client_download["url"], client_path)
            print("开始下载依赖")
            # 下载依赖库文件
            with ThreadPoolExecutor() as executor:
                library_downloads = (
                    (library["downloads"]["artifact"]["url"], library["downloads"]["artifact"]["path"])
                    for library in version_json["libraries"]
                    if "downloads" in library
                )
                for url, path in library_downloads:
                    save_path = os.path.join(LIBRARIES_DIR, path)
                    if not os.path.exists(save_path):
                        executor.submit(download_file, url, save_path)

            # 下载资源文件清单
            asset_index = version_json["assetIndex"]
            asset_index_path = os.path.join(INDEXES_DIR, f"{asset_index['id']}.json")
            if not os.path.exists(asset_index_path):
                download_file(asset_index["url"], asset_index_path)
            with open(asset_index_path, "r") as f:
                asset_json = json.load(f)
            print("开始下载资源文件")
            # 下载资源文件
            with ThreadPoolExecutor() as executor:
                for asset, info in asset_json["objects"].items():
                    hash_assets = info["hash"]
                    url = f"https://bmclapi2.bangbang93.com/assets/{hash_assets[:2]}/{hash_assets}"
                    save_path = os.path.join(OBJECTS_DIR, hash_assets[:2], hash_assets)
                    if not os.path.exists(save_path):
                        executor.submit(download_file, url, save_path)

            # 解压本地库文件
            systems = {'win32': 'windows', 'linux': 'linux', 'darwin': 'osx'}
            os_name = systems.get(sys.platform)
            arch = 'x64' if platform.machine().endswith('64') else 'x86'
            natives_dir = os.path.join(VERSIONS_DIR, version_choice, version_choice + "-natives")
            with ThreadPoolExecutor() as executor:
                for library in version_json["libraries"]:
                    if "rules" in library and any(
                            rule["action"] == "allow" and rule["os"]["name"] == os_name for rule in library["rules"]):
                        save_path = os.path.join(LIBRARIES_DIR, library["downloads"]["artifact"]["path"])
                        executor.submit(extract_files, save_path, natives_dir, arch)
