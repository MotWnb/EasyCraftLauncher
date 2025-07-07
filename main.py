import sys
import asyncio
from typing import Dict, List, TypedDict

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QProgressBar, QTextEdit, QComboBox, QLineEdit, QFormLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

import aiohttp
import qasync


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
        # 用 QTimer 单次触发启动异步任务，利用 qasync 事件循环
        QTimer.singleShot(0, lambda: asyncio.create_task(self.get_versions()))

    async def initialize_session(self):
        self.session = aiohttp.ClientSession()

    async def get_versions(self):
        if self.session is None:
            await self.initialize_session()
        try:
            async with self.session.get(self.version_manifest_v2_url) as resp:
                version_manifest: Dict = await resp.json()
                self.versions: List = version_manifest.get("versions")

                class VersionInfo(TypedDict):
                    id: str
                    type: str
                    url: str
                    time: str
                    releaseTime: str
                    sha1: str
                    complianceLevel: int

                versions_list: List[str] = []
                for version in self.versions:
                    version_info: VersionInfo = version
                    versions_list.append(version_info["id"])
                self.version_combo.addItems(versions_list)
        except Exception as e:
            self.label.setText(f"获取版本列表失败: {e}")

    def start_download(self):
        if self._task is None or self._task.done():
            self.download_btn.setEnabled(False)
            self.progress.setValue(0)
            self._task = asyncio.create_task(self.download())

    async def download(self):
        version = self.version_combo.currentText()
        self.label.setText(f"正在下载版本 {version}...")
        for i in range(1, 11):
            await asyncio.sleep(0.3)  # 模拟下载进度
            self.progress.setValue(i * 10)
        self.label.setText(f"版本 {version} 下载完成！")
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
        self.text.setText(
            "帮助页面：\n\n"
            "1. 选择版本下载最新的Minecraft客户端。\n"
            "2. 在启动页面输入用户名并选择版本启动游戏。\n"
            "3. 遇到问题可以查看这里的FAQ或联系我们。"
        )
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
        with open("style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass

    window = MainWindow()
    window.show()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_forever()
