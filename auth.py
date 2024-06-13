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
    # 检测Google Chrome
    chrome_path = find_browser_reg_path('Chrome')
    driver = None
    if edge_path:
        print(f"Microsoft Edge 已安装: {edge_path}")
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()))
    elif chrome_path:
        print(f"Google Chrome 已安装: {chrome_path}")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

    if driver is None:
        print("没有找到合适的浏览器。")
        return None

    url = (
        "https://login.live.com/oauth20_authorize.srf"
        "?client_id=00000000402b5328"
        "&response_type=code"
        "&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL"
        "&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf"
    )
    driver.get(url)

    # 循环检查当前URL
    while True:
        current_url = driver.current_url
        # 检查URL是否包含授权码
        if "https://login.live.com/oauth20_desktop.srf?code=" in current_url:
            # 提取授权码
            code = current_url.split("code=")[1].split("&")[0]
            print("授权码:", code)
            driver.quit()  # 关闭浏览器
            return code

        # 等待一段时间再检查，避免过于频繁的检查消耗CPU资源
        time.sleep(1)


def exchange_auth_code_for_token(auth_code):
    # POST请求的URL
    url = "https://login.live.com/oauth20_token.srf"

    # POST请求的数据
    data = {
        "client_id": "00000000402b5328",
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
        "scope": "service::user.auth.xboxlive.com::MBI_SSL"
    }

    # 设置请求头
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # 发送POST请求
    response = requests.post(url, data=data, headers=headers)

    # 检查响应状态码
    if response.status_code == 200:
        # 解析响应数据
        token_data = response.json()
        access_token = token_data.get("access_token")
        return access_token
    else:
        # 如果响应状态码不是200，打印错误信息
        print("Error exchanging auth code for token:", response.status_code, response.text)
        return None
def xbox_live_authentication(access_token):
    # Xbox Live身份验证的URL
    url = "https://user.auth.xboxlive.com/user/authenticate"

    # POST请求的数据
    data = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": f"d={access_token}"  # 第二步中获取的访问令牌
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }

    # 设置请求头
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 发送POST请求
    response = requests.post(url, json=data, headers=headers)

    # 检查响应状态码
    if response.status_code == 200:
        # 解析响应数据
        xbox_live_data = response.json()
        xbox_live_token = xbox_live_data.get("Token")
        uhs = xbox_live_data.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs")
        return xbox_live_token, uhs
    else:
        # 如果响应状态码不是200，打印错误信息
        print("Error during Xbox Live authentication:", response.status_code, response.text)
        return None, None




# 使用函数
print("开始步骤1：请在弹出的浏览器窗口中登录你的Microsoft账号")
authorization_code = get_authorization_code()
print("步骤1完成：授权码已获取:", authorization_code)
access_token = exchange_auth_code_for_token(authorization_code)
print("步骤2完成：访问令牌已获取:", access_token)
xbox_live_token, uhs = xbox_live_authentication(access_token)
if xbox_live_token and uhs:
    print("Xbox Live authentication successful.")
    print("Xbox Live Token:", xbox_live_token)
    print("User Hash (uhs):", uhs)
else:
    print("Xbox Live authentication failed.")