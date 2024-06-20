import os

import requests
from urllib.parse import urlsplit
import subprocess
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

version = "1.20.4"
latest_version_forge = \
requests.get(f"https://bmclapi2.bangbang93.com/forge/minecraft/{version}", verify=False).json()[-1]["build"]
download_forge_url = f"https://bmclapi2.bangbang93.com/forge/download/{latest_version_forge}"

# 获取最终的重定向URL和文件名
response = requests.head(download_forge_url, allow_redirects=True, verify=False)
final_url = response.url
response = requests.get(final_url, stream=True, verify=False)
content_disposition = response.headers.get('content-disposition')
filename = None
if content_disposition:
    params = content_disposition.split(';')
    for param in params:
        param = param.strip()
        if param.startswith('filename='):
            filename = param[len('filename="'):-1]
            break
if not filename:
    # 如果头部中没有文件名，则从URL中获取
    filename = urlsplit(final_url).path.split('/')[-1]

# 下载文件
with open(filename, 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)

subprocess.run([
    "java", "-jar", filename,
    "--installClient", r"D:\EasyCraftLauncher_download\.minecraft"
], check=True)
