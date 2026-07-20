from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Qt


class SideMenu(QWidget):
    def __init__(self):
        super().__init__()

        self.setMinimumWidth(240)
        
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Estilo do menu
        self.setStyleSheet("""
            QWidget {
                background-color: #171F33;
                border-right: 2px solid #414554;
                padding-right: 20px
            }
                           
            QLabel{
                color: #dce4fe;
                font-size: 32px;
                font-weight: bold;
                border: none;
                padding: 20px 0;
                left: 0
            }
        """)

        # Título
        self.title = QLabel("Clipter")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Botões
        self.bt_download = QPushButton("  Download")
        self.bt_transcription = QPushButton("  Transcrição")

        self.setup_button(
            self.bt_download,
            "assets/icons/download.svg"
        )

        self.setup_button(
            self.bt_transcription,
            "assets/icons/mic.svg"
        )

        self.buttons = [
            self.bt_download,
            self.bt_transcription
        ]

        self.set_active_button(
            self.bt_download
        )

        # Layout
        layout = QVBoxLayout(self)

        layout.addWidget(self.title)
        layout.addSpacing(15)

        layout.addWidget(self.bt_download)
        layout.addWidget(self.bt_transcription)

        layout.addStretch()

        layout.setContentsMargins(15, 0, 15, 20)
        layout.setSpacing(8)

    def set_active_button(self, button):
        for btn in self.buttons:
            btn.setProperty("active", False)

        button.setProperty("active", True)

        # força o Qt a atualizar o estilo
        for btn in self.buttons:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def setup_button(self, button, icon_path):
        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(24, 24))

        button.setFixedHeight(50)

        button.setCursor(Qt.CursorShape.PointingHandCursor)

        button.setStyleSheet("""
        QPushButton {
            background: transparent;

            color: #c4c7d8;
            font-size: 16px;
            font-weight: bold;

            border: none;
            
            border-radius: 8px;

            text-align: left;
        }
                             
        QPushButton[active="true"] {
            color: #B2C3F9;
            border-right: 2px solid #B2C3F9;
        }

        QPushButton:hover {
            background-color: #232A45;
        }

        QPushButton:pressed {
            background-color: #161C33;
        }
        """)
