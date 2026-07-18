from yt_dlp import YoutubeDL
from PySide6.QtWidgets import (
    QWidget, 
    QPushButton, 
    QVBoxLayout, 
    QLabel,
    QLineEdit,
)

class DownloadPage(QWidget):
    def __init__(self, main_window):
        super().__init__()

        self.main = main_window

        # WIDGETS
        self.button_transcribe = QPushButton("Ir para página de transcrição")
        self.button_download = QPushButton("DOWNLOAD")
        self.input_url_video = QLineEdit()
        self.label = QLabel()

        # SET WIDGETS
        self.label.setText("PAGINA DE DOWNLOAD")
        self.button_transcribe.clicked.connect(self.main.show_transcription_page)
        self.button_download.clicked.connect(self.download)

        # LAYOUT
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.input_url_video)
        layout.addWidget(self.button_download)
        layout.addWidget(self.button_transcribe)

    def download(self):
        url = self.input_url_video.text()

        options = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": r"C:\Users\manri\Downloads\%(title)s.%(ext)s"
        }

        with YoutubeDL(options) as ydl:
            ydl.download(url)   
