import concurrent.futures
import os
import jdk
import json
import requests
from requests.adapters import HTTPAdapter
import urllib3


# 假设 jdk.install 函数已经定义在其他地方，否则需要导入相应的库

def download_minecraft_version():
    # 配置请求会话
    adapter = HTTPAdapter(max_retries=5, pool_block=True)
    http = requests.Session()
    http.mount('http://', adapter)

    # 定义工作目录
    current_dir = os.getcwd()
    minecraft_dir = os.path.join(current_dir, ".minecraft")
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def download_file(url_download, save_path_download):
        response = http.get(url_download, stream=True, verify=False)
        response.raise_for_status()
        save_path_download = os.path.join(minecraft_dir, save_path_download)
        os.makedirs(os.path.dirname(save_path_download), exist_ok=True)
        with open(save_path_download, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

    # 下载并读取版本清单文件
    version_manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
    version_manifest_path = os.path.join(current_dir, "version_manifest.json")
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
            version_json_path = os.path.join(minecraft_dir, "versions", version_choice, f"{version_choice}.json")
            if not os.path.exists(version_json_path):
                download_file(version_json_url, version_json_path)
            with open(version_json_path, "r") as f:
                version_json = json.load(f)

            # 下载客户端文件
            client_download = version_json["downloads"]["client"]
            client_path = os.path.join(minecraft_dir, "versions", version_choice, f"{version_choice}.jar")
            if not os.path.exists(client_path):
                download_file(client_download["url"], client_path)

            # 下载依赖库文件
            with concurrent.futures.ThreadPoolExecutor() as library_executor:
                library_downloads = (
                    (library["downloads"]["artifact"]["url"], library["downloads"]["artifact"]["path"])
                    for library in version_json["libraries"]
                    if "downloads" in library
                )
                for url, path in library_downloads:
                    save_path = os.path.join(minecraft_dir, "libraries", path)
                    if not os.path.exists(save_path):
                        library_executor.submit(download_file, url, save_path)

            # 下载资源文件清单
            asset_index = version_json["assetIndex"]
            asset_index_path = os.path.join(minecraft_dir, "assets", "indexes", f"{version_choice}.json")
            if not os.path.exists(asset_index_path):
                download_file(asset_index["url"], asset_index_path)
            with open(asset_index_path, "r") as f:
                asset_json = json.load(f)

            # 下载资源文件
            with concurrent.futures.ThreadPoolExecutor() as asset_executor:
                for asset, info in asset_json["objects"].items():
                    hash = info["hash"]
                    url = f"https://resources.download.minecraft.net/{hash[:2]}/{hash}"
                    save_path = os.path.join(minecraft_dir, "assets", "objects", hash[:2], hash)
                    if not os.path.exists(save_path):
                        asset_executor.submit(download_file, url, save_path)

            # 下载JDK
            java_version = str(version_json["javaVersion"]["majorVersion"])
            java_install_path = os.path.join(current_dir, "java", f"jdk{java_version}")
            if not os.path.exists(java_install_path):
                print(f"JDK{java_version} 不存在，正在下载...")
                os.makedirs(java_install_path)
                jdk.install(java_version, vendor='Azul', path=java_install_path)
            else:
                print(f"JDK{java_version} 已存在")
            break
