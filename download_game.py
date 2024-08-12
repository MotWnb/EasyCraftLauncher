import asyncio
import json
import os

import aiohttp


async def download_file(session, url, save_path):
    try:
        # 确保保存路径的目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.read()
            with open(save_path, 'wb') as f:
                f.write(data)
            return save_path
    except Exception:
        await download_file(session, url, save_path)
        return save_path


async def download_files(file_info_dict):
    async with aiohttp.ClientSession() as session:
        tasks = [download_file(session, url, save_path) for url, save_path in file_info_dict.items()]
        for save_path in await asyncio.gather(*tasks):
            if save_path:
                # 文件已保存，你可以在这里进行进一步处理
                print(f"文件已保存到 {save_path}")


def download_game(choice, minecraft_folder):
    folder = os.getcwd()
    ecl_folder = os.path.join(folder, "ecl")
    temp_folder = os.path.join(ecl_folder, "temp")
    version_manifest_save_path = os.path.join(temp_folder, "version_manifest.json")
    versions_folder = os.path.join(minecraft_folder, "versions")
    assets_folder = os.path.join(minecraft_folder, "assets")
    libraries_folder = os.path.join(minecraft_folder, "libraries")
    version_info = ""
    download_file_dict = {}
    asyncio.run(download_files(
        {"https://piston-meta.mojang.com/mc/game/version_manifest.json": version_manifest_save_path}))

    version_manifest = json.load(open(version_manifest_save_path, "r"))
    choice = int(choice)
    if choice == 1:
        version_choice = version_manifest["latest"]["release"]
        print(f"尝试下载最新版本: {version_choice}")
    elif choice == 2:
        version_choice = version_manifest["latest"]["snapshot"]
        print(f"尝试下载最新快照版本: {version_choice}")
    elif choice == 3:
        version_choice = input("请输入要下载的版本号: ")
        print(f"尝试下载指定版本: {version_choice}")
    else:
        return "1"

    version_choice = str(version_choice)
    version_folder = os.path.join(versions_folder, version_choice)
    version_json_save_path = os.path.join(version_folder, f"{version_choice}.json")
    version_jar_save_path = os.path.join(version_folder, f"{version_choice}.jar")
    for e in list(version_manifest["versions"]):
        if e["id"] == version_choice:  # 查找版本号
            version_info = e["url"]
            break
    if version_info == "":
        return "2"
    print(version_info)
    asyncio.run(download_files({version_info: version_json_save_path}))  # 下载版本json
    version_json = json.load(open(version_json_save_path, "r"))
    version_assets_index_url = version_json["assetIndex"]["url"]
    index_version = version_json["assetIndex"]["id"]
    asyncio.run(download_files({version_assets_index_url:
                                    os.path.join(assets_folder, "indexes", f"{index_version}.json")}))  # 下载版本json
    version_jar_url = version_json["downloads"]["client"]["url"]
    download_file_dict[version_jar_url] = version_jar_save_path
    version_assets_index = json.load(open(os.path.join(assets_folder, "indexes", f"{index_version}.json"), "r"))
    for f in version_assets_index["objects"]:
        asset_hash = version_assets_index["objects"][f]["hash"]
        asset_url = f"https://resources.download.minecraft.net/{asset_hash[:2]}/{asset_hash}"
        asset_save_path = os.path.join(assets_folder, "objects", asset_hash[:2], asset_hash)
        download_file_dict[asset_url] = asset_save_path
    for g in version_json["libraries"]:
        library_url = g["downloads"]["artifact"]["url"]
        library_save_path = os.path.join(libraries_folder,
                                         g["downloads"]["artifact"]["path"])
        download_file_dict[library_url] = library_save_path
    asyncio.run(download_files(download_file_dict))

    # asyncio.run(download_files({version_json["downloads"]["client"]["url"]: version_jar_save_path}))  # 下载版本jar
