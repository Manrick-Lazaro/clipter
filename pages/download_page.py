from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel

class DownloadPage(QWidget):
    def __init__(self, main_window):
        super().__init__()

        self.main = main_window

        # WIDGETS
        self.button = QPushButton("go to Transcription Page")
        self.button.clicked.connect(self.main.show_transcription_page)

        self.label = QLabel()
        self.label.setText("ESSA É A PAGINA DE DOWNLOAD")

        # LAYOUT
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        
