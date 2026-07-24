from pathlib import Path
import sys
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QProgressBar,
    QWidget, 
    QPushButton, 
    QVBoxLayout, 
    QLabel,
    QLineEdit,
    QFileDialog,
)

# ------------------------
# Card
# ------------------------

class Card(QFrame):
    def __init__(self):
        super().__init__()

        self.setObjectName("card")
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20,20,20,20)
        self.layout.setSpacing(15)

# ------------------------
# Progress Item
# ------------------------

class DownloadItem(QFrame):

    def __init__(self, file, status, progress=0):
        super().__init__()

        self.setObjectName("downloadItem")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15,15,15,15)

        icon = QLabel("🎞")
        icon.setFixedWidth(35)

        center = QVBoxLayout()

        self.title = QLabel(file)
        self.title.setObjectName("fileTitle")

        self.bar = QProgressBar()
        self.bar.setValue(progress)
        self.bar.setTextVisible(False)

        self.info = QLabel(status)
        self.info.setObjectName("status")

        center.addWidget(self.title)
        center.addWidget(self.bar)
        center.addWidget(self.info)

        layout.addWidget(icon)
        layout.addLayout(center)

            # lbl = QLabel("✔")
        self.rightStatus = QLabel(f"{progress}%")
        self.rightStatus.setObjectName("rightStatus")
        layout.addWidget(self.rightStatus)

    def updateProgress(self, name, downloaded, total, speed):
        self.title.setText(Path(name).name)

        self.info.setText(
            f"{self.format_size(downloaded)} / "
            f"{self.format_size(total)} — "
            f"{self.format_size(speed)}/s"
        )

        percent = int(downloaded / total * 100)

        self.bar.setValue(percent)

        self.rightStatus.setText(f"{percent}%")

    @staticmethod
    def format_size(size):

        if not size:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]

        for unit in units:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024

        return f"{size:.1f} PB"


class DownloadPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Media Downloader")
        self.resize(1350,900)

        self.setObjectName("downloadPage")
        self.setAutoFillBackground(True)
        self.setMinimumSize(1000, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        # root.setSpacing(20)

        title = QLabel("Download de Vídeo/Áudio")
        title.setObjectName("title")

        subtitle = QLabel(
            "Cole o link abaixo para iniciar o processamento de alta fidelidade."
        )
        subtitle.setObjectName("subtitle")

        root.addWidget(title)
        root.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(20)

        root.addLayout(body)

        # -----------------------------
        # Left Card 
        # -----------------------------

        left = Card()
        body.addWidget(left,3)

        # -------- Url --------
         
        lbl = QLabel("URL DO CONTEÚDO")
        lbl.setObjectName("label")

        self.url = QLineEdit()
        self.url.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url.setMinimumHeight(42)

        left.layout.addWidget(lbl)
        left.layout.addWidget(self.url)

        # -------- MODO DE DOWNLOAD --------

        modeBox = QGroupBox("MODO DE DOWNLOAD")
        modeBox.setObjectName("mode_download_box")

        modeLayout = QHBoxLayout(modeBox)
        modeLayout.setContentsMargins(5, 25, 5, 5)

        video = QPushButton("Vídeo")
        audio = QPushButton("Apenas Áudio")

        video.setCheckable(True)
        audio.setCheckable(True)
        video.setChecked(True)

        modeLayout.addWidget(video)
        modeLayout.addWidget(audio)

        # -------- CAMINHO PARA SALVAR --------

        saveBox = QGroupBox("SALVAR EM")
        saveLayout = QHBoxLayout(saveBox)

        self.path = QLineEdit("/Users/admin/Downloads")
        downloads_path = str(Path.home() / "Downloads")
        self.path.setText(downloads_path)

        browse = QPushButton("Procurar...")
        browse.clicked.connect(self.select_folder)

        saveLayout.addWidget(self.path)
        saveLayout.addWidget(browse)

        # -------- -------- -------- -------- 

        row = QHBoxLayout()
        row.addWidget(modeBox,2)
        row.addWidget(saveBox,3)

        left.layout.addLayout(row)

        # -------- BOTÃO DE DOWNLOAD --------

        download = QPushButton("⬇  Baixar Agora")
        download.setObjectName("downloadButton")
        download.setMinimumHeight(55)

        download.clicked.connect(self.download)

        left.layout.addWidget(download)

        # -------- ESPAÇADOR (TALVEZ REMOVER) --------

        spacer = QLabel()
        spacer.setMinimumHeight(250)
        spacer.setAlignment(Qt.AlignCenter)
        spacer.setText("✥")

        left.layout.addWidget(spacer)

        # -----------------------------
        # Right Column
        # -----------------------------

        right = QVBoxLayout()
        body.addLayout(right,1)

        preview = Card()

        img = QLabel()
        img.setFixedHeight(140)
        img.setAlignment(Qt.AlignCenter)
        img.setText("MEDIA DOWNLOAD")

        img.setObjectName("preview")

        state = QLabel("ESTADO ATUAL")
        state.setObjectName("label")

        waiting = QLabel("Aguardando Link...")
        waiting.setObjectName("state")

        info = QLabel(
            "Insira uma URL válida para visualizar os metadados antes de iniciar."
        )
        info.setWordWrap(True)

        preview.layout.addWidget(img)
        preview.layout.addWidget(state)
        preview.layout.addWidget(waiting)
        preview.layout.addWidget(info)

        right.addWidget(preview)

        tips = Card()

        tips.layout.addWidget(QLabel("DICAS DE PERFORMANCE"))

        tips.layout.addWidget(QLabel("⚡ Transcodificação em Nuvem"))
        tips.layout.addWidget(QLabel("Arquivos acima de 4GB são processados em nossos clusters."))

        tips.layout.addSpacing(10)

        tips.layout.addWidget(QLabel("🎬 Max Bitrate H.265"))
        tips.layout.addWidget(QLabel("Padrão 4K HDR habilitado para downloads de vídeo."))

        right.addWidget(tips)

        # -----------------------------
        # Queue
        # -----------------------------

        # -------- TITULO --------

        queueTitle = QLabel("Fila de Processamento")
        queueTitle.setObjectName("queue")

        root.addWidget(queueTitle)

        # --------

        downloads = QVBoxLayout()

        self.downloadItem = DownloadItem(
            "Aguardando...",
            "",
            0
        )

        downloads.addWidget(self.downloadItem)

        root.addLayout(downloads)  

        self.loadStyle()

    def loadStyle(self):
        qss = Path(__file__).parent / "style.qss"

        with open(qss, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

    def download(self):
        url = self.url.text()

        options = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": fr"C:\Users\manri\Downloads\%(title)s.%(ext)s",
            "progress_hooks": [self.progress_hook],
            "noplaylist": True,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                )
            },
        }

        try:
            with YoutubeDL(options) as ydl:
                ydl.download([url])
        except DownloadError as e:
            print(e)

    def progress_hook(self, d):
        if d["status"] != "downloading":
            return

        self.downloadItem.updateProgress(
            name=d.get("filename", ""),
            downloaded=d.get("downloaded_bytes", 0),
            total=d.get("total_bytes") or d.get("total_bytes_estimate", 0),
            speed=d.get("speed", 0),
        )

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecione uma pasta de destino",
            self.path.text()
        )
        if folder:
            self.path.setText(folder)