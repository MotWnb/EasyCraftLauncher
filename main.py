import asyncio
import hashlib
import json
import os.path
import sys
import time
from typing import List, Dict, Literal

import aiofiles
import aiohttp
import qasync
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QStackedWidget,
                               QProgressBar, QTextEdit, QComboBox, QLineEdit, QFormLayout)

import TypedDict


class VersionNotFoundError(Exception):
    """当用户请求的 Minecraft 版本不存在时抛出"""
    pass


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        label = QLabel("欢迎使用 EasyCraftLauncher")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        label.setFont(font)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()


class SmartDownloader:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    @staticmethod
    async def calculate_sha1(file_path: str) -> str:
        """异步计算文件的SHA1哈希值"""
        sha1 = hashlib.sha1()
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(64 * 1024)  # 64KB块大小
                if not chunk:
                    break
                sha1.update(chunk)
        return sha1.hexdigest()

    async def download(self, url: str, target_path: str, retry: int = 3, timeout_per_chunk: float = 10.0,
                       expected_sha1: TypedDict.Optional[str] = None):
        # 检查文件是否存在且SHA1匹配
        if os.path.exists(target_path) and expected_sha1:
            actual_sha1 = await self.calculate_sha1(target_path)
            if actual_sha1 == expected_sha1:
                print(f"文件已存在且SHA1匹配: {target_path}")
                return True
            else:
                print(f"文件存在但SHA1不匹配 ({actual_sha1} vs {expected_sha1})，重新下载")
                os.remove(target_path)  # 删除不匹配的文件
        existing_size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
        headers = {}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        try:
            async with self.session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status not in (200, 206):
                    if retry > 0:
                        return await self.download(url, target_path, retry - 1)
                    else:
                        raise Exception(f"下载失败：状态码 {resp.status}")

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                mode: Literal["ab", "wb"] = "ab" if existing_size > 0 else "wb"
                start_time = time.time()
                total_downloaded = 0

                async with aiofiles.open(target_path, mode=mode) as f:
                    while True:
                        chunk = await asyncio.wait_for(resp.content.read(1024), timeout=timeout_per_chunk)
                        if not chunk:
                            break
                        await f.write(chunk)  # 异步写入
                        total_downloaded += len(chunk)

                        elapsed = time.time() - start_time
                        if elapsed > 5 and total_downloaded / elapsed < 1024:
                            raise Exception("下载速度过慢，已自动中断并准备重试")

            # 下载完成后验证SHA1
            if expected_sha1:
                actual_sha1 = await self.calculate_sha1(target_path)
                if actual_sha1 != expected_sha1:
                    # SHA1不匹配时删除文件并重试
                    print(f"SHA1校验失败: 期望 {expected_sha1}, 实际 {actual_sha1}")
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    if retry > 0:
                        print(f"SHA1校验失败，尝试重新下载（剩余重试次数: {retry})")
                        return await self.download(url, target_path, retry - 1, timeout_per_chunk, expected_sha1)
                    else:
                        raise Exception(f"SHA1校验失败: 期望 {expected_sha1}, 实际 {actual_sha1}")
                else:
                    print(f"SHA1校验通过: {target_path}")
            return True  # 下载成功

        except Exception as e:

            # 发生异常时删除可能损坏的文件
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except:
                    pass
            if retry > 0:
                print(f"下载出错: {e}, 尝试重新下载（剩余重试次数: {retry})")
                await asyncio.sleep(1)
                return await self.download(url, target_path, retry - 1, timeout_per_chunk, expected_sha1)
            else:
                raise Exception(f"下载失败：{e}")


class DownloadPage(QWidget):
    def __init__(self):
        super().__init__()
        self.session = None
        self.versions = None
        self.version_manifest_v2_url = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.version_combo = QComboBox()
        form_layout.addRow("选择版本:", self.version_combo)

        self.progress = QProgressBar()
        self.label = QLabel("点击“开始下载”开始下载选中的版本")

        self.download_btn = QPushButton("开始下载")
        self.download_btn.clicked.connect(self.start_download)

        layout.addLayout(form_layout)
        layout.addWidget(self.progress)
        layout.addWidget(self.label)
        layout.addWidget(self.download_btn)

        self._task = None
        self.downloader = None

        # 用 QTimer 单次触发启动异步任务，利用 qasync 事件循环
        QTimer.singleShot(0, lambda: asyncio.create_task(self.get_versions()))

    async def initialize_session(self):
        self.session = aiohttp.ClientSession()
        self.downloader = SmartDownloader(self.session)

    async def get_versions(self) -> list[TypedDict.VersionInfo] | None:
        if self.session is None:
            await self.initialize_session()
        try:
            async with self.session.get(self.version_manifest_v2_url) as resp:
                version_manifest: Dict = await resp.json()
                self.versions: List[TypedDict.VersionInfo] = version_manifest.get("versions")
                versions_list: List[str] = []
                for version in self.versions:
                    i_version_info: TypedDict.VersionInfo = version
                    versions_list.append(i_version_info["id"])
                self.version_combo.addItems(versions_list)
                return self.versions
        except Exception as e:
            self.label.setText(f"获取版本列表失败: {e}")

    def start_download(self):
        if self._task is None or self._task.done():
            self.download_btn.setEnabled(False)
            self.progress.setValue(0)
            self._task = asyncio.create_task(self.download())

    async def download(self):
        async def output(info: str):
            self.label.setText(info)

        try:
            if self.session is None:
                await self.initialize_session()
            version: str = self.version_combo.currentText()
            asyncio.create_task(output(f"开始下载版本 {version}..."))
            versions = await self.get_versions()
            selected_version_info = next((v for v in versions if v["id"] == version), None)
            if selected_version_info is None:
                raise VersionNotFoundError(f"找不到版本：{version}")

            selected_version_json_url = selected_version_info["url"]
            selected_version_json_sha1 = selected_version_info["sha1"]
            asyncio.create_task(output(f"已找到版本 {version}，准备从 {selected_version_json_url} 下载..."))

            await self.downloader.download(selected_version_json_url, f"{version}.json", selected_version_json_sha1)

            async with aiofiles.open(f"{version}.json", "r", encoding="utf-8") as f:
                selected_version_json: TypedDict.VersionJsonInfo = json.loads(await f.read())



        except VersionNotFoundError as e:
            asyncio.create_task(output(str(e)))
            print(f"[Version Error] {e}")
        except Exception as e:
            asyncio.create_task(output("下载时发生未知错误"))
            print(f"[Download Error] {e}")
        finally:
            self.download_btn.setEnabled(True)


class LaunchPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.username_edit = QLineEdit()
        self.version_combo = QComboBox()
        self.version_combo.addItems(["1.20.2", "1.19.4", "1.18.2", "1.17.1"])  # 示例版本

        form_layout.addRow("用户名:", self.username_edit)
        form_layout.addRow("启动版本:", self.version_combo)

        self.progress = QProgressBar()
        self.label = QLabel("准备启动游戏")

        self.launch_btn = QPushButton("启动游戏")
        self.launch_btn.clicked.connect(self.start_launch)

        layout.addLayout(form_layout)
        layout.addWidget(self.progress)
        layout.addWidget(self.label)
        layout.addWidget(self.launch_btn)

        self._task = None

    def start_launch(self):
        if self._task is None or self._task.done():
            username = self.username_edit.text().strip()
            if not username:
                self.label.setText("用户名不能为空！")
                return
            self.launch_btn.setEnabled(False)
            self.progress.setValue(0)
            self._task = asyncio.create_task(self.launch())

    async def launch(self):
        self.label.setText("游戏启动中...")
        for i in range(1, 11):
            await asyncio.sleep(0.3)
            self.progress.setValue(i * 10)
        self.label.setText("游戏启动完成！")
        self.launch_btn.setEnabled(True)


class HelpPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setText("帮助页面：\n\n"
                          "1. 选择版本下载最新的Minecraft客户端。\n"
                          "2. 在启动页面输入用户名并选择版本启动游戏。\n"
                          "3. 遇到问题可以查看这里的FAQ或联系我们。")
        layout.addWidget(self.text)


class ToolboxPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.label = QLabel("工具箱：\n这里可以放置各种小工具，比如皮肤管理、配置备份等。")
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.label)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EasyCraftLauncher")
        self.resize(600, 400)

        self.home_btn = QPushButton("主页")
        self.download_btn = QPushButton("下载")
        self.launch_btn = QPushButton("启动")
        self.help_btn = QPushButton("帮助")
        self.toolbox_btn = QPushButton("工具箱")

        for btn in (self.home_btn, self.download_btn, self.launch_btn, self.help_btn, self.toolbox_btn):
            btn.setCheckable(True)
            btn.setMinimumHeight(40)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)
        nav_layout.addWidget(self.home_btn)
        nav_layout.addWidget(self.download_btn)
        nav_layout.addWidget(self.launch_btn)
        nav_layout.addWidget(self.help_btn)
        nav_layout.addWidget(self.toolbox_btn)
        nav_layout.addStretch()

        self.stack = QStackedWidget()
        self.home_page = HomePage()
        self.download_page = DownloadPage()
        self.launch_page = LaunchPage()
        self.help_page = HelpPage()
        self.toolbox_page = ToolboxPage()

        for page in (self.home_page, self.download_page, self.launch_page, self.help_page, self.toolbox_page):
            self.stack.addWidget(page)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.stack)

        self.buttons = [self.home_btn, self.download_btn, self.launch_btn, self.help_btn, self.toolbox_btn]
        self.home_btn.setChecked(True)

        self.home_btn.clicked.connect(lambda: self.switch_page(0))
        self.download_btn.clicked.connect(lambda: self.switch_page(1))
        self.launch_btn.clicked.connect(lambda: self.switch_page(2))
        self.help_btn.clicked.connect(lambda: self.switch_page(3))
        self.toolbox_btn.clicked.connect(lambda: self.switch_page(4))

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 读取样式表文件
    try:
        with open("style.qss", "r", encoding="utf-8") as qss_f:
            app.setStyleSheet(qss_f.read())
    except Exception:
        pass

    window = MainWindow()
    window.show()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_forever()
