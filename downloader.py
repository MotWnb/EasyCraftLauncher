import concurrent.futures
import os
import json
import requests
import jdk
import urllib3
from requests.adapters import HTTPAdapter

# 配置请求会话
adapter = HTTPAdapter(max_retries=5, pool_block=True)
http = requests.Session()
http.mount('http://', adapter)

# 定义工作目录
current_dir = os.getcwd()
minecraft_dir = os.path.join(current_dir, ".minecraft")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def download_file(url_download, save_path_download):
    response = http.get(url_download, verify=False)
    save_path_download = os.path.join(current_dir, save_path_download)
    # 创建文件所在的目录（如果需要）
    dir_name = os.path.dirname(save_path_download)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(save_path_download, 'wb') as f:
        f.write(response.content)
        f.close()


# 下载并读取版本清单文件
version_manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
version_manifest_path = os.path.join(current_dir, "version_manifest.json")
download_file(version_manifest_url, version_manifest_path)
with open(version_manifest_path, "r") as f:
    version_manifest = json.load(f)

# 输出最新版本信息并请求用户输入
latest_list = version_manifest["latest"]
print(f"最新的预览版是: {latest_list['snapshot']}")
print(f"最新的正式版是: {latest_list['release']}")
version_choice = input("请输入您要下载的版本(例如1.16.5): ")

# 下载并处理所选版本的文件
for version in version_manifest["versions"]:
    if version["id"] == version_choice:
        version_json_url = version["url"]
        version_json_path = os.path.join(minecraft_dir, "versions", version_choice, f"{version_choice}.json")
        download_file(version_json_url, version_json_path)
        with open(version_json_path, "r") as f:
            version_json = json.load(f)

        # 下载客户端文件
        client_download = version_json["downloads"]["client"]
        client_path = os.path.join(minecraft_dir, "versions", version_choice, f"{version_choice}.jar")
        download_file(client_download["url"], client_path)

        # 下载依赖库文件
        print("开始下载依赖库文件")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            library_downloads = (
                (library["downloads"]["artifact"]["url"], library["downloads"]["artifact"]["path"])
                for library in version_json["libraries"]
                if "downloads" in library
            )
            for url, path in library_downloads:
                save_path = os.path.join(minecraft_dir, "libraries", path)
                executor.submit(download_file, url, save_path)

        # 下载资源文件清单
        print("开始下载资源文件")
        asset_index = version_json["assetIndex"]
        asset_index_path = os.path.join(minecraft_dir, "assets", "indexes", f"{asset_index['id']}.json")
        download_file(asset_index["url"], asset_index_path)
        with open(asset_index_path, "r") as f:
            asset_json = json.load(f)

        # 下载资源文件
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for asset, info in asset_json["objects"].items():
                hash = info["hash"]
                url = f"https://resources.download.minecraft.net/{hash[:2]}/{hash}"
                save_path = os.path.join(minecraft_dir, "assets", "objects", hash[:2], hash)
                executor.submit(download_file, url, save_path)

        # 下载JDK
        java_version = version_json["javaVersion"]["majorVersion"]
        java_install_path = os.path.join(current_dir, "java", f"jdk{java_version}")
        if not os.path.exists(java_install_path):
            print(f"JDK{java_version} 不存在，正在下载...")
            os.makedirs(java_install_path)
            print(java_version)
            jdk.install(java_version, vendor='Azul', path=java_install_path)
        else:
            print(f"JDK{java_version} 已存在")

        break
