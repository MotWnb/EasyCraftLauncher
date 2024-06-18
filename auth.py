import threading
import time
import winreg
import requests
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


def find_browser_reg_path(browser_name):
    browser_path = None
    if browser_name == 'Chrome':
        key = r'Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe'
    elif browser_name == 'Edge':
        key = r'Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe'
    else:
        return None

    try:
        hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key)
        browser_path = winreg.QueryValue(hkey, None)
        winreg.CloseKey(hkey)
    except WindowsError:
        pass

    return browser_path


def get_authorization_code():
    # 检测Microsoft Edge
    edge_path = find_browser_reg_path('Edge')
    chrome_path = find_browser_reg_path('Chrome')
    if edge_path:
        print(f"Microsoft Edge 已安装: {edge_path}")
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()))
    else:
        print(f"Google Chrome 已安装: {chrome_path}")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

    url = ("https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?prompt=login&client_id=00000000402b5328"
           "&response_type=code&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL&redirect_uri=https:%2F%2Flogin"
           ".live.com%2Foauth20_desktop.srf")
    driver.get(url)

    # 循环检查当前URL
    while True:
        current_url = driver.current_url
        if "https://login.live.com/oauth20_desktop.srf?code=" in current_url:
            code = current_url.split("code=")[1].split("&")[0]
            threading.Thread(target=driver.quit).start()
            return code
        time.sleep(1)


def ms_login_step2(code, is_refresh=False):
    print("开始微软登录步骤 2(刷新登录)" if is_refresh else "开始微软登录步骤 2(非刷新登录)")

    url = "https://login.live.com/oauth20_token.srf"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    if is_refresh:
        payload = {
            "client_id": "00000000402b5328",
            "refresh_token": code,
            "grant_type": "refresh_token",
            "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
            "scope": "service::user.auth.xboxlive.com::MBI_SSL"
        }
    else:
        payload = {
            "client_id": "00000000402b5328",
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
            "scope": "service::user.auth.xboxlive.com::MBI_SSL"
        }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        result_json = response.json()
    except requests.exceptions.HTTPError as e:
        print(e)

    access_token = result_json.get("access_token")
    refresh_token = result_json.get("refresh_token")
    return access_token, refresh_token


def ms_login_step3(access_token):
    print("开始微软登录步骤 3")

    url = "https://user.auth.xboxlive.com/user/authenticate"
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": access_token
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result_json = response.json()
    except requests.exceptions.HTTPError as e:
        raise

    xbl_token = result_json.get("Token")
    return xbl_token


def ms_login_step4(xbl_token):
    print("开始微软登录步骤 4")

    request_body = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [xbl_token]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }

    url = "https://xsts.auth.xboxlive.com/xsts/authorize"
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=request_body)
        response.raise_for_status()
        result_json = response.json()
    except requests.exceptions.HTTPError as e:
        raise

    xsts_token = result_json.get("Token")
    uhs = result_json.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs")
    return xsts_token, uhs


def ms_login_step5(tokens):
    print("开始微软登录步骤 5")

    identity_token = f"XBL3.0 x={tokens[1]};{tokens[0]}"
    request_body = {
        "identityToken": identity_token
    }

    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=request_body)
        response.raise_for_status()
        result_json = response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("微软登录第 5 步汇报 429")
            raise Exception("登录尝试太过频繁，请等待几分钟后再试！")
        elif e.response.status_code == 403:
            print("微软登录第 5 步汇报 403")
            raise Exception(
                "当前 IP 的登录尝试异常。" + "\n" + "如果你使用了 VPN 或加速器，请把它们关掉或更换节点后再试！")
        else:
            raise

    access_token = result_json.get("access_token")
    return access_token


def check_game_ownership(access_token):
    url = "https://api.minecraftservices.com/entitlements/mcstore"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result_json = response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return False

    if "items" in result_json and result_json["items"]:
        return True
    else:
        return False


def ms_login_step7(access_token):
    print("开始微软登录步骤 7")

    url = "https://api.minecraftservices.com/minecraft/profile"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result_json = response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return None, None, None

    uuid = result_json.get("id")
    username = result_json.get("name")
    return uuid, username, response.text


def perform_ms_login():
    refresh_token = ""
    try:
        with open("latest.log", "r") as f:
            refresh_token = f.read()
    except Exception as e:
        pass

    if not refresh_token:
        print("开始微软登录步骤1：请在弹出的浏览器窗口中登录你的Microsoft账号")
        authorization_code = get_authorization_code()  # 1
        access_token, refresh_token = ms_login_step2(authorization_code)  # 2
    else:
        access_token, refresh_token = ms_login_step2(refresh_token, True)  # 2

    with open("latest.log", "w+") as f:
        f.write(refresh_token)

    xbl_token = ms_login_step3(access_token)  # 3
    xsts_token, uhs = ms_login_step4(xbl_token)  # 4
    tokens = [xsts_token, uhs]  # 5
    access_token = ms_login_step5(tokens)  # 6

    if check_game_ownership(access_token):
        print("用户拥有Minecraft游戏。")
    else:
        print("用户没有Minecraft游戏。")

    uuid, username, result = ms_login_step7(access_token)  # 7
    if uuid and username:
        print("玩家ID (UUID):", uuid)
        print("玩家昵称:", username)
        print("access_token:", access_token)
    else:
        print("获取玩家信息失败。")
    return uuid, username, access_token


# perform_ms_login()
