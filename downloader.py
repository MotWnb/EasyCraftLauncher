import concurrent.futures
import os
import jdk
import json
import urllib3
import requests
import zipfile
from requests.adapters import HTTPAdapter

# 使用连接池复用
adapter = HTTPAdapter(max_retries=5, pool_block=True)
http = requests.Session()
http.mount('http://', adapter)

# 定义一些变量
version_json = None  # 版本json文件
asset_json = None  # 资源json文件
current_dir = os.getcwd()
# 关闭ssl禁用警告
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
    print("下载完成 " + save_path_download)


# urls = ['http://example.com/file1', 'http://example.com/file2', 'http://example.com/file3']
# save_paths = ['/path/to/file1', '/path/to/file2', '/path/to/file3']


# # 使用多线程
# with ThreadPoolExecutor() as executor:
#     for url, save_path in zip(urls, save_paths):
#         executor.submit(download_file, url, save_path)

# 下载版本清单文件到工作目录
download_file("https://piston-meta.mojang.com/mc/game/version_manifest.json", "version_manifest.json")

# 读取版本清单文件
with open("version_manifest.json", "r") as f:
    version_manifest = json.load(f)

# 读取版本列表
version_list = version_manifest["versions"]
latest_list = version_manifest["latest"]

# 遍历版本列表并告诉用户最新的snapshot(预览版)和release(正式版)
print("最新的预览版是: " + latest_list["snapshot"])
print("最新的正式版是: " + latest_list["release"])
# 询问下哪个版本
version_choice = input("请输入您要下载的版本(例如1.16.5): ")

for version in version_list:
    if version["id"] == version_choice:
        # 下载版本json文件到工作目录
        download_file(version["url"], f".minecraft/versions/{version_choice}/{version_choice}.json")

        # 读取版本json文件
        with open(f".minecraft/versions/{version_choice}/{version_choice}.json", "r") as f:
            version_json = json.load(f)

        # 下载版本文件到工作目录
        download_file(version_json["downloads"]["client"]["url"],
                      f".minecraft/versions/{version_choice}/{version_choice}.jar")

        # 下载依赖库文件到工作目录(通过多线程)
        print("开始下载依赖库文件")
        with (concurrent.futures.ThreadPoolExecutor() as executor):
            for library in version_json["libraries"]:
                '''
                libraries
                游戏所有依赖库，包含其下载地址等信息。
                downloads下均含有artifact键，有些含有classifiers键。
                只含有artifact键的为-cp参数后所需拼接的路径，注意path键中为不完整路径，请补全为完整路径。
                含有rules键的为natives库，在游戏启动前将对应平台的含有jar文件解压至natives文件夹。
                '''
                url = library["downloads"]["artifact"]["url"]
                save_path = library["downloads"]["artifact"]["path"]
                save_path = os.path.join(".minecraft/libraries/", save_path)
                executor.submit(download_file, url, save_path)
        # 下载资源文件清单到工作目录
        print("开始下载资源文件")
        asset_name = version_json["assets"]
        asset_name = f".minecraft/assets/indexes/{asset_name}.json"
        download_file(version_json["assetIndex"]["url"], asset_name)
        # 下载资源文件
        with open(asset_name, "r") as f:
            asset_json = json.load(f)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for asset in asset_json["objects"]:
                '''
                objects文件的下载地址为：

                https://resources.download.minecraft.net/<hash的前两位字符>/<hash>
                存储路径为：

                .minecraft/assets/objects/<hash的前两位字符>/<hash
                '''
                hash = asset_json["objects"][asset]["hash"]
                url = "https://resources.download.minecraft.net/" + hash[:2] + "/" + hash
                save_path = os.path.join(".minecraft/assets/objects/", hash[:2], hash)
                executor.submit(download_file, url, save_path)

        # 下载JDK到工作目录
        java_version = str(version_json["javaVersion"]["majorVersion"])
        java_install_path = os.path.join(current_dir, "java", f"jdk{java_version}")
        # 创建文件所在的目录（如果需要）
        if not os.path.exists(java_install_path):
            print(f"JDK{java_version} 不存在，正在下载...")
            os.makedirs(java_install_path)
            jdk.install(java_version, vendor='Azul', path=java_install_path)
        else:
            print(f"JDK{java_version} 已存在")

        break
