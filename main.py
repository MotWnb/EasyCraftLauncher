import asyncio
import hashlib
import json
import os.path
import platform
import sys
import time
import zipfile
from asyncio import to_thread
from typing import List, Dict, Literal, Optional

import aiofiles
import aiohttp
import qasync
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QStackedWidget,
                               QProgressBar, QTextEdit, QComboBox, QLineEdit, QFormLayout)
from aiohttp import ClientError, ClientPayloadError

import typed_dict


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
        sha1 = hashlib.sha1()
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(64 * 1024)
                if not chunk:
                    break
                sha1.update(chunk)
        return sha1.hexdigest()

    async def download(
        self,
        url: str,
        target_path: str,
        retry: int = 3,
        timeout_per_chunk: float = 10.0,
        expected_sha1: Optional[str] = None
    ) -> bool:
        """
        返回 True 表示下载成功（且 SHA1 校验通过，如果提供 expected_sha1）。
        否则会在重试耗尽后抛出异常。
        """
        # 如果文件已存在且 SHA1 匹配，直接返回
        if expected_sha1 and os.path.exists(target_path):
            actual = await self.calculate_sha1(target_path)
            if actual == expected_sha1:
                return True
            else:
                print(f"文件存在但 SHA1 不匹配 ({actual} != {expected_sha1})，将重新下载")
                os.remove(target_path)
        # 每次 retry 都重新获取已下载的大小和 Range 头
        existing_size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
        headers = {}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"
        try:
            async with self.session.get(url, headers=headers, allow_redirects=True) as resp:
                resp.raise_for_status()  # 捕获 4xx/5xx 错误

                os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
                mode: Literal["ab", "wb"] = "ab" if existing_size > 0 else "wb"

                async with aiofiles.open(target_path, mode=mode) as f:
                    total_downloaded = 0
                    last_check = time.time()
                    last_bytes = 0
                    check_interval = 5.0
                    while True:
                        # 超时控制
                        chunk = await asyncio.wait_for(
                            resp.content.read(1024),
                            timeout=timeout_per_chunk
                        )
                        if not chunk:
                            break
                        await f.write(chunk)
                        total_downloaded += len(chunk)
                        # 滑动窗口测速
                        now = time.time()
                        if now - last_check >= check_interval:
                            speed = (total_downloaded - last_bytes) / (now - last_check)
                            if speed < 1024:  # <1KB/s
                                raise Exception("下载速度过慢，强制中断重试")
                            last_check, last_bytes = now, total_downloaded
            # 下载完成后做 SHA1 校验
            if expected_sha1:
                actual = await self.calculate_sha1(target_path)
                if actual != expected_sha1:
                    print(f"SHA1 校验失败 (期望 {expected_sha1}，实际 {actual})，将重试")
                    os.remove(target_path)
                    if retry > 0:
                        return await self.download(
                            url, target_path,
                            retry - 1, timeout_per_chunk,
                            expected_sha1
                        )
                    else:
                        raise Exception("SHA1 校验失败且重试次数耗尽")
            return True
        except (ClientPayloadError, ClientError, asyncio.TimeoutError, Exception) as e:
            # 打印完整堆栈，便于调试
            import traceback; traceback.print_exc()

            # 清理可能损坏的文件
            if os.path.exists(target_path):
                try: os.remove(target_path)
                except: pass
            if retry > 0:
                print(f"下载出错: {e}，准备重试（剩余 {retry} 次）")
                await asyncio.sleep(1)
                # 递归调用并且 **return**，确保调用链返回新的协程结果
                return await self.download(
                    url, target_path,
                    retry - 1, timeout_per_chunk,
                    expected_sha1
                )
            else:
                raise Exception(f"下载失败: {e}")


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

        self.get_tasks_remaining_bun = QPushButton("获取剩余任务")
        self.get_tasks_remaining_bun.clicked.connect(self.get_tasks_remaining)

        layout.addLayout(form_layout)
        layout.addWidget(self.progress)
        layout.addWidget(self.label)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.get_tasks_remaining_bun)

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
    @staticmethod
    def get_tasks_remaining():
        current_tasks = asyncio.all_tasks()
        print(f"当前未完成任务数: {len(current_tasks)}")

    async def download_assets_index(self, index_url: str, sha1: str,
                                    assets_folder_path: str, assets_index_path: str):
        await self.downloader.download(index_url, assets_index_path, expected_sha1=sha1)

        async with aiofiles.open(assets_index_path, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())

        tasks = []
        for name, meta in data['objects'].items():
            hash_ = meta['hash']
            subdir = hash_[:2]
            path = os.path.join(assets_folder_path, subdir, hash_)
            url = f"https://resources.download.minecraft.net/{subdir}/{hash_}"
            tasks.append(self.downloader.download(url, path, expected_sha1=hash_))

        await asyncio.gather(*tasks)

    @staticmethod
    def is_allowed(lib: TypedDict.Library, os_name: str, arch: str) -> bool:
        rules = lib.get("rules")
        if not rules:
            return True  # 没有规则时默认允许

        result = None
        for rule in rules:
            os_rule = rule.get("os", {})
            # 判断是否匹配当前系统
            if os_rule:
                if "name" in os_rule and os_rule["name"] != os_name:
                    continue
                if "arch" in os_rule and os_rule["arch"] != arch:
                    continue

            # 匹配到规则，就根据 action 修改结果
            result = rule["action"] == "allow"

        return result if result is not None else False

    @staticmethod
    async def extract_natives_if_needed(jar_path: str, dest_path: str,
                                        extract_cfg: Optional[TypedDict.LibraryExtract]):
        def _extract():
            excludes = extract_cfg.get("exclude", []) if extract_cfg else []
            with zipfile.ZipFile(jar_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if any(member.startswith(exclude) for exclude in excludes):
                        continue
                    zip_ref.extract(member, dest_path)

        await to_thread(_extract)

    async def download_libraries(self, libraries: List[TypedDict.Library],
                                 libraries_folder_path: str, selected_version_natives_folder_path: str):
        os_name = platform.system().lower()
        arch = platform.machine().lower()
        tasks = []

        for lib in libraries:
            if not self.is_allowed(lib, os_name, arch):
                continue

            downloads = lib.get("downloads", {})
            name = lib.get("name", "")
            artifact = downloads.get("artifact")

            # 普通库或 natives（新格式）
            if artifact:
                path = os.path.join(libraries_folder_path, artifact["path"])
                url = artifact["url"]
                sha1 = artifact["sha1"]
                tasks.append(self.downloader.download(url, path, expected_sha1=sha1))

                # 判断是否是新格式 natives：name 包含 natives-xxx
                '''
                if "natives-" in name:
                    native_dest = os.path.join("natives", name.replace(":", "_"))
                    tasks.append(self.extract_natives_if_needed(path, native_dest, lib.get("extract")))
                '''

            # 老格式 natives（classifiers + natives）
            classifiers = downloads.get("classifiers")
            natives = lib.get("natives")
            if classifiers and natives:
                key = natives.get(os_name)
                if key and key in classifiers:
                    classifier = classifiers[key]
                    jar_path = os.path.join("libraries", classifier["path"])
                    url = classifier["url"]
                    sha1 = classifier["sha1"]
                    tasks.append(self.downloader.download(url, jar_path, expected_sha1=sha1))
                    native_dest = os.path.join("natives", name.replace(":", "_"))
                    '''
                    tasks.append(self.extract_natives_if_needed(jar_path, native_dest, lib.get("extract")))
                    '''

        await asyncio.gather(*tasks)

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

            minecraft_folder_path = os.path.join(os.getcwd(), ".minecraft")
            versions_folder_path = os.path.join(minecraft_folder_path, "versions")
            selected_version_folder_path = os.path.join(versions_folder_path, version)
            selected_version_json_path = os.path.join(selected_version_folder_path, f"{version}.json")
            selected_version_jar_path = os.path.join(selected_version_folder_path, f"{version}.jar")
            assets_folder_path = os.path.join(minecraft_folder_path, "assets")
            assets_index_path = os.path.join(assets_folder_path, "indexes")
            libraries_folder_path = os.path.join(minecraft_folder_path, "libraries")
            selected_version_natives_folder_path = os.path.join(selected_version_folder_path, f"{version}-natives")
            selected_version_json_url = selected_version_info["url"]
            selected_version_json_sha1 = selected_version_info["sha1"]
            asyncio.create_task(output(f"已找到版本 {version}，准备从 {selected_version_json_url} 下载..."))

            await self.downloader.download(selected_version_json_url, selected_version_json_path, expected_sha1=selected_version_json_sha1)

            async with aiofiles.open(selected_version_json_path, "r", encoding="utf-8") as f:
                selected_version_dict: TypedDict.VersionJsonInfo = json.loads(await f.read())
                await asyncio.gather(
                    self.downloader.download(
                        selected_version_dict["downloads"]["client"]["url"],
                        selected_version_jar_path,
                        expected_sha1=selected_version_dict["downloads"]["client"]["sha1"]
                    ),
                    self.download_assets_index(
                        selected_version_dict["assetIndex"]["url"],
                        selected_version_dict["assetIndex"]["sha1"],
                        assets_folder_path,
                        assets_index_path
                    )

                )
                '''
                ,

                self.download_libraries(
                    selected_version_dict["libraries"],
                    libraries_folder_path,
                    selected_version_natives_folder_path
                )
                '''
                asyncio.create_task(output(f"版本 {version} 下载完成！"))

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
