import json
import os
import sys

import requests
import urllib3
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QApplication

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_authorization_code():
    class Browser(QWebEngineView):
        def __init__(self):
            super().__init__()
            url = "http://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?prompt=login&client_id=00000000402b5328&response_type=code&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL&redirect_uri=https:%2F%2Flogin.live.com%2Foauth20_desktop.srf"
            self.load(QUrl(url))
            self.loadFinished.connect(self.on_load_finished)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.check_url)
            self.timer.start(1000)
            self.current_url = None

        def on_load_finished(self, ok):
            if ok:
                self.current_url = self.url().toString()

        def check_url(self):
            if self.current_url:
                if "https://login.live.com/oauth20_desktop.srf?code=" in self.current_url:
                    code = self.current_url.split("code=")[1].split("&")[0]
                    self.close()
                    return code
            return None

    app = QApplication(sys.argv)
    browser = Browser()
    browser.show()
    code = None
    while not code:
        QApplication.processEvents()
        code = browser.check_url()
    app.quit()
    return code


def ms_login_step2(code, is_refresh=False):
    url = "https://login.live.com/oauth20_token.srf"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {"client_id": "00000000402b5328", "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
               "scope": "service::user.auth.xboxlive.com::MBI_SSL",
               "grant_type": "refresh_token" if is_refresh else "authorization_code"}
    if is_refresh:
        payload["refresh_token"] = code
    else:
        payload["code"] = code
    response = requests.post(url, headers=headers, data=payload, verify=False)
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
    response = requests.post(url, headers=headers, json=payload, verify=False)
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
    response = requests.post(url, headers=headers, json=request_body, verify=False)
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
    response = requests.post(url, headers=headers, json=request_body, verify=False)
    response.raise_for_status()
    return response.json().get("access_token")


def check_game_ownership(access_token):
    url = "https://api.minecraftservices.com/entitlements/mcstore"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()
    return bool(response.json().get("items"))


def ms_login_step7(access_token):
    url = "https://api.minecraftservices.com/minecraft/profile"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()
    result_json = response.json()
    return result_json.get("id"), result_json.get("name"), response.text


def perform_ms_login():
    refresh_token = ""
    user_name = ""
    refresh_tokens = {}
    if os.path.exists("ECL/account.config"):
        with open("ECL/account.config", "r") as f:
            refresh_tokens = json.load(f)
    if refresh_tokens:
        user_names = [i for i in refresh_tokens]
        user_name = input("请输入你的用户名,如果你想要添加新账号，请输入 y " + str(user_names) + "\n")
    if not refresh_tokens or user_name == "y":
        print("开始微软登录步骤 1：请在弹出的浏览器窗口中登录你的 Microsoft 账号")
        authorization_code = get_authorization_code()
        access_token, refresh_token = ms_login_step2(authorization_code)
    else:
        access_token, refresh_token = ms_login_step2(refresh_tokens[user_name], True)
    xbl_token = ms_login_step3(access_token)
    xsts_token, uhs = ms_login_step4(xbl_token)
    tokens = [xsts_token, uhs]
    access_token = ms_login_step5(tokens)
    if check_game_ownership(access_token):
        print("用户拥有 Minecraft 游戏。")
    else:
        print("用户没有 Minecraft 游戏。")
    uuid, username, result = ms_login_step7(access_token)
    if uuid and username:
        pass
    else:
        print("获取玩家信息失败。")
    refresh_tokens[username] = refresh_token
    with open("ECL/account.config", "w+") as f:
        json.dump(refresh_tokens, f, indent=4)
    return uuid, username, access_token
