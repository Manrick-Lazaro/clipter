from PySide6.QtWidgets import QMainWindow, QStackedWidget

from pages.download_page import DownloadPage
from pages.transcription_page import TranscriptionPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # WIDGETS
        self.stack = QStackedWidget()
        
        self.download_page = DownloadPage(self)
        self.transcription_page = TranscriptionPage(self)

        # STACKS PAGES
        self.stack.addWidget(self.download_page)
        self.stack.addWidget(self.transcription_page)

        self.setCentralWidget(self.stack)

        # INICIAL PAGE
        self.show_download_page()

    def show_download_page(self):
        self.stack.setCurrentWidget(self.download_page)
    
    def show_transcription_page(self):
        self.stack.setCurrentWidget(self.transcription_page)