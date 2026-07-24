from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, 
    QStackedWidget,
    QWidget,
    QHBoxLayout,
)

from pages.download_page.download_page import DownloadPage
from pages.transcription_page import TranscriptionPage
from widgets.side_menu import SideMenu

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Clipter")
        self.resize(1324, 868)

        # WIDGETS
        self.menu = SideMenu()
        self.stack = QStackedWidget()
        self.stack.setObjectName("stack")
        self.download_page = DownloadPage()
        self.transcription_page = TranscriptionPage()

        # STACKS PAGES
        self.stack.addWidget(self.download_page)
        self.stack.addWidget(self.transcription_page)

        # LAYOUT
        central = QWidget()
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.menu)
        layout.addWidget(self.stack)
        
        self.setCentralWidget(central)

        self.menu.bt_download.clicked.connect(
            self.show_download_page
        )

        self.menu.bt_transcription.clicked.connect(
            self.show_transcription_page
        )

        self.loadStyle()
    
    def loadStyle(self):
        qss = Path(__file__).parent / "style.qss"

        with open(qss, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

    def show_download_page(self):
        self.stack.setCurrentWidget(self.download_page)
        self.menu.set_active_button(
            self.menu.bt_download
        )

    def show_transcription_page(self):
        self.stack.setCurrentWidget(self.transcription_page)
        self.menu.set_active_button(
            self.menu.bt_transcription
        )