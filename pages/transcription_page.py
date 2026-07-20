from faster_whisper import WhisperModel
from PySide6.QtWidgets import (
    QWidget, 
    QPushButton, 
    QVBoxLayout, 
    QLabel,
    QLineEdit,
)

class TranscriptionPage(QWidget):
    def __init__(self):
        super().__init__()

        # WIDGETS
        self.button_transcribe = QPushButton("TRANSCRIBE")
        self.input_path_video = QLineEdit()
        self.label = QLabel()

        # SET WIDGETS
        self.label.setText("PAGINA DE TRANSCRIÇÃO")
        self.button_transcribe.clicked.connect(self.transcribe)

        # LAYOUT
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.input_path_video)
        layout.addWidget(self.button_transcribe)

    
    def time_formatter(self, seconds):
        seconds = int(seconds)

        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60

        return f"{h:02}:{m:02}:{s:02}"
    
    def transcribe(self):
        video = self.input_path_video.text().strip()

        model_whisper = "large-v3-turbo"
        language = "pt"
        SRT = "transcription_file.srt"

        model = WhisperModel(
            model_whisper,
            device="cuda",
            compute_type="float16"
        )

        segments, info = model.transcribe(
            video,
            language=language
        )

        with open(SRT, "w", encoding="utf-8") as arquive:
            counter = 1
            for segment in segments:
                start = self.time_formatter(segment.start)
                end = self.time_formatter(segment.end)
                text = segment.text.strip()
                arquive.write(f"{start} --> {end} : {text} \n")
                counter += 1
