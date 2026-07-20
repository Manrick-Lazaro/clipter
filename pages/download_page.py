from yt_dlp import YoutubeDL
from PySide6.QtWidgets import (
    QWidget, 
    QPushButton, 
    QVBoxLayout, 
    QLabel,
    QLineEdit,
)

class DownloadPage(QWidget):
    def __init__(self):
        super().__init__()

        # WIDGETS
        self.button_download = QPushButton("DOWNLOAD")
        self.input_url_video = QLineEdit()
        self.label = QLabel()

        # SET WIDGETS
        self.button_download.clicked.connect(self.download)

        # LAYOUT
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.input_url_video)
        layout.addWidget(self.button_download)

    def download(self):
        url = self.input_url_video.text()

        options = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": r"C:\Users\manri\Downloads\%(title)s.%(ext)s"
        }

        with YoutubeDL(options) as ydl:
            ydl.download(url)   
