import threading
import time
import winreg
import urllib3
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.edge.options import Options
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def find_browser_reg_path(browser_name):
    paths = {
        'Chrome': r'Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe',
        'Edge': r'Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe'
    }
    key = paths.get(browser_name)
    if not key:
        return None

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as hkey:
            return winreg.QueryValue(hkey, None)
    except WindowsError:
        return None


def get_authorization_code():
    options = Options()
    options.add_argument("--no-proxy-server")
    browser_path = find_browser_reg_path('Edge') or find_browser_reg_path('Chrome')
    if browser_path:
        print(f"Browser found: {browser_path}")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options) \
            if 'Chrome' in browser_path else \
            webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
    else:
        raise Exception("Neither Chrome nor Edge found.")

    url = ("http://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?prompt=login&client_id=00000000402b5328"
           "&response_type=code&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL&redirect_uri=https:%2F%2Flogin"
           ".live.com%2Foauth20_desktop.srf")
    driver.get(url)

    while True:
        current_url = driver.current_url
        if "https://login.live.com/oauth20_desktop.srf?code=" in current_url:
            code = current_url.split("code=")[1].split("&")[0]
            threading.Thread(target=driver.quit).start()
            return code
        time.sleep(1)


def ms_login_step2(code, is_refresh=False):
    url = "https://login.live.com/oauth20_token.srf"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "client_id": "00000000402b5328",
        "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
        "scope": "service::user.auth.xboxlive.com::MBI_SSL"
    }
    payload["grant_type"] = "refresh_token" if is_refresh else "authorization_code"
    if is_refresh:
        payload["refresh_token"] = code
    else:
        payload["code"] = code

    with requests.Session() as session:
        response = session.post(url, headers=headers, data=payload, verify=False)
        response.raise_for_status()
        result_json = response.json()
        access_token = result_json.get("access_token")
        refresh_token = result_json.get("refresh_token")
        return access_token, refresh_token


def ms_login_step3(access_token):
    url = "https://user.auth.xboxlive.com/user/authenticate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": access_token
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }

    with requests.Session() as session:
        response = session.post(url, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        return response.json().get("Token")


def ms_login_step4(xbl_token):
    url = "https://xsts.auth.xboxlive.com/xsts/authorize"
    headers = {
        "Content-Type": "application/json"
    }

    request_body = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [xbl_token]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }

    with requests.Session() as session:
        response = session.post(url, headers=headers, json=request_body, verify=False)
        response.raise_for_status()
        result_json = response.json()
        xsts_token = result_json.get("Token")
        uhs = result_json.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs")
        return xsts_token, uhs


def ms_login_step5(tokens):
    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
    headers = {"Content-Type": "application/json"}
    identity_token = f"XBL3.0 x={tokens[1]};{tokens[0]}"
    request_body = {
        "identityToken": identity_token
    }

    with requests.Session() as session:
        response = session.post(url, headers=headers, json=request_body, verify=False)
        response.raise_for_status()
        return response.json().get("access_token")


def check_game_ownership(access_token):
    url = "https://api.minecraftservices.com/entitlements/mcstore"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    with requests.Session() as session:
        response = session.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return bool(response.json().get("items"))


def ms_login_step7(access_token):
    url = "https://api.minecraftservices.com/minecraft/profile"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    with requests.Session() as session:
        response = session.get(url, headers=headers, verify=False)
        response.raise_for_status()
        result_json = response.json()
        return result_json.get("id"), result_json.get("name"), response.text


def perform_ms_login():
    refresh_token = ""
    try:
        with open("latest.log", "r") as f:
            refresh_token = f.read()
    except Exception:
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
        print("用户没有Minecraft游戏。请检查是否购买了Minecraft或设置Minecraft档案")

    uuid, username, result = ms_login_step7(access_token)  # 7
    if uuid and username:
        print("玩家ID (UUID):", uuid)
        print("玩家昵称:", username)
        print("access_token:", access_token)
    else:
        print("获取玩家信息失败。")
    return uuid, username, access_token

# perform_ms_login()
