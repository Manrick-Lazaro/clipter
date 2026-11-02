from pathlib import Path
import zipfile, py_compile, textwrap

base = Path("/mnt/data/omnivideo_studio")
base.mkdir(parents=True, exist_ok=True)

# app_code = r'''from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Qt, Slot
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QSpinBox
)

APP_DIR = Path(__file__).resolve().parent
ACCENT = "#6366F1"
PURPLE = "#8B5CF6"
GREEN = "#10B981"
BG = "#090A0F"
PANEL = "#171820"
PANEL_ALT = "#1D1E28"
TEXT = "#E7E7EF"
MUTED = "#999AAA"
BORDER = "#292A36"


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def ffprobe_path() -> str | None:
    return shutil.which("ffprobe")


class Worker(QObject):
    log = Signal(str)
    progress = Signal(int)
    done = Signal(bool, str)
    transcript_segment = Signal(str, float, float)

    def __init__(self, task: str, **kwargs: Any):
        super().__init__()
        self.task = task
        self.kwargs = kwargs
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            if self.task == "download":
                self._download()
            elif self.task == "transcribe":
                self._transcribe()
            elif self.task == "cut":
                self._cut()
            else:
                raise ValueError(f"Tarefa desconhecida: {self.task}")
            if not self._stop:
                self.done.emit(True, "Operação concluída.")
            else:
                self.done.emit(False, "Operação interrompida.")
        except Exception as exc:
            self.done.emit(False, str(exc))

    def _download(self) -> None:
        try:
            import yt_dlp
        except ImportError as exc:
            raise RuntimeError("yt-dlp não instalado. Execute: pip install -r requirements.txt") from exc

        url = self.kwargs["url"]
        folder = Path(self.kwargs["folder"])
        folder.mkdir(parents=True, exist_ok=True)
        quality = self.kwargs["quality"]
        extract_subs = self.kwargs["subtitles"]

        def hook(data: dict[str, Any]) -> None:
            if self._stop:
                raise RuntimeError("Download interrompido pelo usuário.")
            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                if total:
                    pct = int(downloaded * 100 / total)
                    self.progress.emit(max(0, min(99, pct)))
                speed = data.get("_speed_str", "")
                eta = data.get("_eta_str", "")
                self.log.emit(f"Baixando... {data.get('_percent_str', '').strip()} | {speed} | ETA {eta}")
            elif status == "finished":
                self.progress.emit(100)
                self.log.emit("Download do arquivo concluído. Finalizando processamento...")

        formats = {
            "Melhor qualidade": "bv*+ba/b",
            "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
            "720p": "bv*[height<=720]+ba/b[height<=720]",
            "480p": "bv*[height<=480]+ba/b[height<=480]",
            "Somente áudio (MP3)": "bestaudio/best",
        }
        opts: dict[str, Any] = {
            "format": formats.get(quality, "bv*+ba/b"),
            "outtmpl": str(folder / "%(title).180B [%(id)s].%(ext)s"),
            "noplaylist": True,
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": False,
            "merge_output_format": "mp4",
        }
        if quality == "Somente áudio (MP3)":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
        if extract_subs:
            opts.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["pt", "pt-BR", "en"],
                "subtitlesformat": "srt/best",
            })
        if not ffmpeg_path():
            self.log.emit("Aviso: FFmpeg não encontrado no PATH; algumas combinações de áudio/vídeo podem falhar.")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    def _transcribe(self) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper não instalado. Execute: pip install -r requirements.txt") from exc

        source = Path(self.kwargs["source"])
        output = Path(self.kwargs["folder"])
        output.mkdir(parents=True, exist_ok=True)
        model_name = self.kwargs["model"]
        language = self.kwargs["language"]
        device = self.kwargs["device"]
        compute_type = self.kwargs["compute_type"]
        beam_size = self.kwargs["beam_size"]
        self.log.emit(f"Carregando {model_name} ({device}/{compute_type})...")
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        self.log.emit("Modelo carregado. Iniciando transcrição...")
        segments_iter, info = model.transcribe(
            str(source),
            language=language,
            task="transcribe",
            beam_size=beam_size,
            patience=2.0,
            temperature=0.0,
            condition_on_previous_text=True,
            word_timestamps=True,
            vad_filter=False,
        )
        duration = info.duration or 0
        self.log.emit(f"Duração aproximada: {duration:.1f}s | Idioma: {info.language}")
        segments: list[dict[str, Any]] = []
        for seg in segments_iter:
            if self._stop:
                raise RuntimeError("Transcrição interrompida pelo usuário.")
            words = None
            if seg.words is not None:
                words = [
                    {"start": w.start, "end": w.end, "word": w.word, "probability": w.probability}
                    for w in seg.words
                ]
            item = {
                "id": seg.id, "start": seg.start, "end": seg.end, "text": seg.text,
                "avg_logprob": seg.avg_logprob,
                "compression_ratio": seg.compression_ratio,
                "no_speech_prob": seg.no_speech_prob,
                "words": words,
            }
            segments.append(item)
            self.transcript_segment.emit(seg.text.strip(), float(seg.start), float(seg.end))
            if duration:
                self.progress.emit(min(99, int(seg.end * 100 / duration)))
            self.log.emit(f"[{self._ts(seg.start)}] {seg.text.strip()}")
        stem = source.stem
        txt = " ".join(s["text"].strip() for s in segments).strip()
        (output / f"{stem}.txt").write_text(txt + "\n", encoding="utf-8")
        srt_lines: list[str] = []
        vtt_lines = ["WEBVTT", ""]
        for i, seg in enumerate(segments, 1):
            srt_lines.extend([str(i), f'{self._ts(seg["start"])} --> {self._ts(seg["end"])}', seg["text"].strip(), ""])
            vtt_lines.extend([f'{self._ts(seg["start"], True)} --> {self._ts(seg["end"], True)}', seg["text"].strip(), ""])
        (output / f"{stem}.srt").write_text("\n".join(srt_lines), encoding="utf-8")
        (output / f"{stem}.vtt").write_text("\n".join(vtt_lines), encoding="utf-8")
        data = {
            "source": str(source.resolve()), "model": model_name, "language": language,
            "duration": duration, "language_probability": info.language_probability,
            "settings": {"beam_size": beam_size, "patience": 2, "temperature": 0,
                         "condition_on_previous_text": True, "word_timestamps": True,
                         "vad_filter": False, "device": device, "compute_type": compute_type},
            "segments": segments,
        }
        (output / f"{stem}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.progress.emit(100)
        self.log.emit(f"Arquivos gerados: {stem}.txt, .srt, .vtt e .json")

    @staticmethod
    def _ts(seconds: float, vtt: bool = False) -> str:
        ms = max(0, round(seconds * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02}{'.' if vtt else ','}{ms:03}"

    def _cut(self) -> None:
        ffmpeg = ffmpeg_path()
        if not ffmpeg:
            raise RuntimeError("FFmpeg não encontrado. Instale o FFmpeg e adicione a pasta bin ao PATH.")
        source = Path(self.kwargs["source"])
        output = Path(self.kwargs["folder"])
        output.mkdir(parents=True, exist_ok=True)
        cuts = self.kwargs["cuts"]
        mode = self.kwargs["mode"]
        if not cuts:
            raise ValueError("Adicione pelo menos um trecho.")
        for index, cut in enumerate(cuts, 1):
            if self._stop:
                raise RuntimeError("Cortes interrompidos pelo usuário.")
            start, end = float(cut["start"]), float(cut["end"])
            if start < 0 or end <= start:
                raise ValueError(f"Intervalo inválido no item {index}: início/fim.")
            title = re.sub(r'[<>:"/\\\\|?*]+', "_", cut["title"]).strip(" .") or f"corte_{index:03}"
            target = output / f"{index:03}_{title}.mp4"
            command = [ffmpeg, "-hide_banner", "-y", "-ss", str(start), "-i", str(source), "-t", str(end-start)]
            if mode == "Rápido (Stream Copy)":
                command += ["-map", "0", "-c", "copy"]
            else:
                command += ["-map", "0:v:0?", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k"]
            command += ["-movflags", "+faststart", str(target)]
            self.log.emit(f"Cortando {index}/{len(cuts)}: {title}")
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            while proc.poll() is None:
                if self._stop:
                    proc.terminate()
                    raise RuntimeError("Corte interrompido pelo usuário.")
                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    self.log.emit(line.rstrip())
            if proc.returncode != 0:
                raise RuntimeError(f"FFmpeg falhou ao gerar: {target.name}")
            self.progress.emit(int(index * 100 / len(cuts)))
        self.log.emit(f"{len(cuts)} corte(s) exportado(s) para {output}")


class ClipterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clipter")
        self.resize(1440, 900)
        self.setMinimumSize(1120, 720)
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self.cut_rows: list[dict[str, QWidget]] = []
        self._build()
        self._refresh_engine_status()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(285)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 22, 18, 18)
        side.setSpacing(10)
        logo = QLabel("CLIPTER")
        logo.setStyleSheet("font-size:21px;font-weight:800;color:#F1F0FF;")
        side.addWidget(logo)
        side.addSpacing(22)
        side.addWidget(self._muted("FERRAMENTAS PRINCIPAIS"))
        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        for label, icon in [
            ("Download de Vídeo", "⇩"),
            ("Transcrição de Áudio/Vídeo", "◉"),
            ("Corte de Trechos", "✂"),
        ]:
            item = QListWidgetItem(f"{icon}   {label}")
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self._switch_page)
        side.addWidget(self.nav, 1)
        side.addStretch()
        status = QFrame()
        status.setObjectName("statusCard")
        sl = QVBoxLayout(status)
        sl.addWidget(self._muted("STATUS DO MOTOR"))
        self.engine_label = QLabel("●  Verificando dependências...")
        self.engine_label.setStyleSheet(f"color:{GREEN};font-weight:600;")
        sl.addWidget(self.engine_label)
        sl.addWidget(self._muted("FFmpeg • Whisper • yt-dlp"))
        side.addWidget(status)
        side.addWidget(self._muted("⚙  Ajustes                                  v1.0.0"))
        root.addWidget(sidebar)

        main = QWidget()
        main.setObjectName("mainArea")
        ml = QVBoxLayout(main)
        ml.setContentsMargins(26, 18, 26, 20)
        ml.setSpacing(14)
        top = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText("⌕  Pesquisar mídias, tarefas ou comandos...")
        search.setReadOnly(True)
        top.addWidget(search, 1)
        clock = QLabel("LOCAL PROCESSING")
        clock.setObjectName("topBadge")
        top.addWidget(clock)
        ml.addLayout(top)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._download_page())
        self.pages.addWidget(self._transcription_page())
        self.pages.addWidget(self._cut_page())
        ml.addWidget(self.pages, 1)
        root.addWidget(main, 1)

    def _muted(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color:{MUTED};font-size:11px;")
        return label

    def _panel(self, title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setStyleSheet("font-size:18px;font-weight:700;")
        layout.addWidget(heading)
        if subtitle:
            layout.addWidget(self._muted(subtitle))
        return frame, layout

    def _field(self, parent: QVBoxLayout, label: str, placeholder: str = "") -> QLineEdit:
        parent.addWidget(self._muted(label.upper()))
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        parent.addWidget(field)
        return field

    def _browse_row(self, parent: QVBoxLayout, label: str, placeholder: str, folder: bool) -> QLineEdit:
        row = QHBoxLayout()
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        button = QPushButton("Procurar pasta..." if folder else "Selecionar arquivo...")
        button.clicked.connect(lambda: self._browse(field, folder))
        row.addWidget(field, 1)
        row.addWidget(button)
        parent.addWidget(self._muted(label.upper()))
        parent.addLayout(row)
        return field

    def _browse(self, field: QLineEdit, folder: bool):
        path = QFileDialog.getExistingDirectory(self, "Selecionar pasta") if folder else QFileDialog.getOpenFileName(
            self, "Selecionar arquivo", "", "Vídeo/Áudio (*.mp4 *.mkv *.mov *.avi *.mp3 *.wav *.m4a *.flac);;Todos (*.*)"
        )[0]
        if path:
            field.setText(path)

    def _progress_panel(self, layout: QVBoxLayout, label: str):
        layout.addWidget(self._muted(label.upper()))
        bar = QProgressBar()
        bar.setValue(0)
        bar.setTextVisible(True)
        layout.addWidget(bar)
        status = QLabel("Aguardando início...")
        status.setStyleSheet(f"color:{MUTED};")
        layout.addWidget(status)
        return bar, status

    def _download_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 8, 0, 0)
        title = QLabel("Download de Vídeo")
        title.setStyleSheet("font-size:28px;font-weight:800;")
        v.addWidget(title)
        v.addWidget(self._muted("Baixe vídeos compatíveis da web diretamente para o computador usando yt-dlp e FFmpeg."))
        grid = QGridLayout()
        left, ll = self._panel("Fonte do Vídeo", "Insira a URL do vídeo ou conteúdo compatível.")
        self.url_edit = self._field(ll, "URL do vídeo", "https://...")
        ll.addWidget(self._muted("RESOLUÇÃO / PERFIL"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Melhor qualidade", "1080p", "720p", "480p", "Somente áudio (MP3)"])
        ll.addWidget(self.quality_combo)
        self.subs_check = QCheckBox("Tentar baixar legendas disponíveis (SRT)")
        self.subs_check.setChecked(True)
        ll.addWidget(self.subs_check)
        right, rl = self._panel("Destino Local", "Escolha onde os arquivos serão armazenados.")
        self.download_folder = self._browse_row(rl, "Pasta de destino", "Selecione a pasta", True)
        rl.addStretch()
        grid.addWidget(left, 0, 0)
        grid.addWidget(right, 0, 1)
        v.addLayout(grid)
        progress_panel, pl = self._panel("Progresso do Download")
        self.download_bar, self.download_status = self._progress_panel(pl, "Progresso global")
        self.download_button = QPushButton("⇩   Iniciar Download Agora")
        self.download_button.setObjectName("primaryButton")
        self.download_button.clicked.connect(self._start_download)
        pl.addWidget(self.download_button)
        v.addWidget(progress_panel)
        self.download_log = self._log_box(v, "Registro de download")
        return page

    def _transcription_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 8, 0, 0)
        title = QLabel("Transcrição de Áudio e Vídeo")
        title.setStyleSheet("font-size:28px;font-weight:800;")
        v.addWidget(title)
        v.addWidget(self._muted("Converta gravações em texto com timestamps usando Whisper local."))
        grid = QGridLayout()
        left, ll = self._panel("Arquivo de Origem")
        self.trans_source = self._browse_row(ll, "Caminho do vídeo/áudio", "Selecione um arquivo", False)
        self.trans_output = self._browse_row(ll, "Diretório de exportação", "Selecione uma pasta", True)
        ll.addWidget(self._muted("MODELO WHISPER"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["large-v3-turbo", "large-v3", "medium", "small"])
        self.model_combo.setCurrentText("large-v3-turbo")
        ll.addWidget(self.model_combo)
        ll.addWidget(self._muted("IDIOMA"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Português (pt)", "pt")
        self.language_combo.addItem("Inglês (en)", "en")
        ll.addWidget(self.language_combo)
        ll.addWidget(self._muted("DISPOSITIVO"))
        self.device_combo = QComboBox()
        self.device_combo.addItem("Automático", "auto")
        self.device_combo.addItem("GPU NVIDIA (CUDA)", "cuda")
        self.device_combo.addItem("CPU", "cpu")
        ll.addWidget(self.device_combo)
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["auto", "float16", "int8_float16", "int8"])
        ll.addWidget(self.compute_combo)
        ll.addWidget(self._muted("BEAM SIZE"))
        self.beam_spin = QSpinBox()
        self.beam_spin.setRange(1, 20)
        self.beam_spin.setValue(5)
        ll.addWidget(self.beam_spin)
        right, rl = self._panel("Processamento da Transcrição")
        self.trans_bar, self.trans_status = self._progress_panel(rl, "Progresso estimado")
        self.transcript_view = QTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setPlaceholderText("A transcrição aparecerá aqui conforme os segmentos forem reconhecidos...")
        rl.addWidget(self.transcript_view, 1)
        self.trans_button = QPushButton("✧   Iniciar Transcrição IA")
        self.trans_button.setObjectName("primaryButton")
        self.trans_button.clicked.connect(self._start_transcription)
        ll.addWidget(self.trans_button)
        grid.addWidget(left, 0, 0)
        grid.addWidget(right, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        v.addLayout(grid, 1)
        self.trans_log = self._log_box(v, "Registro da transcrição", compact=True)
        return page

    def _cut_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 8, 0, 0)
        title = QLabel("Corte de Trechos em Lote")
        title.setStyleSheet("font-size:28px;font-weight:800;")
        outer.addWidget(title)
        outer.addWidget(self._muted("Defina intervalos de tempo e exporte vários clipes com FFmpeg."))
        source_panel, sl = self._panel("Vídeo de Origem e Destino")
        self.cut_source = self._browse_row(sl, "Vídeo de origem", "Selecione o vídeo", False)
        self.cut_output = self._browse_row(sl, "Pasta onde salvar os cortes", "Selecione uma pasta", True)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self._muted("ESTRATÉGIA DE RENDERIZAÇÃO"))
        self.cut_mode = QComboBox()
        self.cut_mode.addItems(["Rápido (Stream Copy)", "Reencodar (Frame Exato)"])
        mode_row.addWidget(self.cut_mode)
        sl.addLayout(mode_row)
        outer.addWidget(source_panel)
        heading = QHBoxLayout()
        heading.setContentsMargins(0, 5, 0, 0)
        heading.addWidget(QLabel("Trechos Marcados para Corte"))
        heading.addStretch()
        add_btn = QPushButton("+ Adicionar Novo Trecho")
        add_btn.clicked.connect(self._add_cut_row)
        heading.addWidget(add_btn)
        outer.addLayout(heading)
        self.cut_list_frame = QFrame()
        self.cut_list_layout = QVBoxLayout(self.cut_list_frame)
        self.cut_list_layout.setContentsMargins(0, 0, 0, 0)
        self.cut_list_layout.setSpacing(7)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.cut_list_frame)
        outer.addWidget(scroll, 1)
        self._add_cut_row()
        self._add_cut_row()
        bottom, bl = self._panel("Exportação em Lote")
        self.cut_bar, self.cut_status = self._progress_panel(bl, "Progresso do lote")
        self.cut_button = QPushButton("✂   Cortar Todos os Trechos de Uma Vez")
        self.cut_button.setObjectName("primaryButton")
        self.cut_button.clicked.connect(self._start_cut)
        bl.addWidget(self.cut_button)
        outer.addWidget(bottom)
        self.cut_log = self._log_box(outer, "Registro de cortes", compact=True)
        return page

    def _add_cut_row(self):
        row = QFrame()
        row.setObjectName("cutRow")
        layout = QGridLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        title = QLineEdit()
        title.setPlaceholderText("Título do arquivo de saída")
        start = QLineEdit("00:00:00")
        end = QLineEdit("00:00:10")
        start.setMaximumWidth(130)
        end.setMaximumWidth(130)
        layout.addWidget(QLabel(f"{len(self.cut_rows)+1:02d}"), 0, 0)
        layout.addWidget(title, 0, 1)
        layout.addWidget(QLabel("INÍCIO"), 0, 2)
        layout.addWidget(start, 0, 3)
        layout.addWidget(QLabel("FIM"), 0, 4)
        layout.addWidget(end, 0, 5)
        delete = QPushButton("Remover")
        delete.clicked.connect(lambda: self._remove_cut_row(row))
        layout.addWidget(delete, 0, 6)
        self.cut_list_layout.addWidget(row)
        self.cut_rows.append({"widget": row, "title": title, "start": start, "end": end})

    def _remove_cut_row(self, widget: QWidget):
        if len(self.cut_rows) <= 1:
            QMessageBox.information(self, "Trechos", "Mantenha pelo menos um trecho.")
            return
        for item in list(self.cut_rows):
            if item["widget"] is widget:
                self.cut_rows.remove(item)
                widget.deleteLater()
                break
        for index, item in enumerate(self.cut_rows, 1):
            item["widget"].layout().itemAt(0).widget().setText(f"{index:02d}")

    def _log_box(self, parent: QVBoxLayout, title: str, compact: bool = False):
        panel, layout = self._panel(title)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setMaximumHeight(105 if compact else 135)
        layout.addWidget(text)
        parent.addWidget(panel)
        return text

    def _switch_page(self, index: int):
        self.pages.setCurrentIndex(index)

    def _refresh_engine_status(self):
        parts = []
        parts.append("FFmpeg OK" if ffmpeg_path() else "FFmpeg ausente")
        try:
            import yt_dlp  # noqa
            parts.append("yt-dlp OK")
        except ImportError:
            parts.append("yt-dlp pendente")
        try:
            import faster_whisper  # noqa
            parts.append("Whisper OK")
        except ImportError:
            parts.append("Whisper pendente")
        self.engine_label.setText("●  " + "  |  ".join(parts))

    def _start_download(self):
        url = self.url_edit.text().strip()
        folder = self.download_folder.text().strip()
        if not url or not folder:
            QMessageBox.warning(self, "Dados incompletos", "Informe a URL e a pasta de destino.")
            return
        self.download_log.clear()
        self.download_bar.setValue(0)
        self._launch("download", self.download_button, self.download_bar, self.download_status,
                     self.download_log, url=url, folder=folder,
                     quality=self.quality_combo.currentText(), subtitles=self.subs_check.isChecked())

    def _start_transcription(self):
        source, folder = self.trans_source.text().strip(), self.trans_output.text().strip()
        if not Path(source).is_file() or not folder:
            QMessageBox.warning(self, "Dados incompletos", "Selecione um arquivo válido e a pasta de exportação.")
            return
        self.transcript_view.clear()
        self.trans_log.clear()
        self.trans_bar.setValue(0)
        self._launch("transcribe", self.trans_button, self.trans_bar, self.trans_status,
                     self.trans_log, source=source, folder=folder,
                     model=self.model_combo.currentText(), language=self.language_combo.currentData(),
                     device=self.device_combo.currentData(), compute_type=self.compute_combo.currentText(),
                     beam_size=self.beam_spin.value())

    @staticmethod
    def _parse_time(value: str) -> float:
        value = value.strip().replace(",", ".")
        parts = value.split(":")
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        raise ValueError(f"Tempo inválido: {value}")

    def _start_cut(self):
        source, folder = self.cut_source.text().strip(), self.cut_output.text().strip()
        if not Path(source).is_file() or not folder:
            QMessageBox.warning(self, "Dados incompletos", "Selecione o vídeo e a pasta de destino.")
            return
        cuts = []
        try:
            for i, row in enumerate(self.cut_rows, 1):
                title = row["title"].text().strip() or f"corte_{i:03}"
                start = self._parse_time(row["start"].text())
                end = self._parse_time(row["end"].text())
                if start < 0 or end <= start:
                    raise ValueError(f"Confira início e fim do trecho {i}.")
                cuts.append({"title": title, "start": start, "end": end})
        except ValueError as exc:
            QMessageBox.warning(self, "Tempo inválido", str(exc))
            return
        self.cut_log.clear()
        self.cut_bar.setValue(0)
        self._launch("cut", self.cut_button, self.cut_bar, self.cut_status,
                     self.cut_log, source=source, folder=folder, cuts=cuts,
                     mode=self.cut_mode.currentText())

    def _launch(self, task, button, bar, status, log, **kwargs):
        if self.thread and self.thread.isRunning():
            QMessageBox.information(self, "Processamento", "Já existe uma tarefa em execução.")
            return

        # Os widgets são guardados na janela. Os sinais do Worker chegam
        # aos slots da janela por QueuedConnection, portanto a atualização
        # da interface sempre acontece na thread principal do Qt.
        self._active_button = button
        self._active_bar = bar
        self._active_status = status
        self._active_log = log

        button.setEnabled(False)
        bar.setValue(0)

        self.thread = QThread(self)
        self.worker = Worker(task, **kwargs)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        queued = Qt.ConnectionType.QueuedConnection
        self.worker.log.connect(self._on_worker_log, queued)
        self.worker.progress.connect(self._on_worker_progress, queued)

        if task == "transcribe":
            self.worker.transcript_segment.connect(self._on_worker_segment, queued)

        self.worker.done.connect(self._on_worker_done, queued)
        self.worker.done.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    @Slot(str)
    def _on_worker_log(self, message):
        if getattr(self, "_active_log", None) is not None:
            self._active_log.append(message)

    @Slot(int)
    def _on_worker_progress(self, value):
        if getattr(self, "_active_bar", None) is not None:
            self._active_bar.setValue(value)
        if getattr(self, "_active_status", None) is not None:
            self._active_status.setText(f"Processando... {value}%")

    @Slot(str, float, float)
    def _on_worker_segment(self, text, start, end):
        self.transcript_view.append(
            f'<span style="color:{GREEN}">[{Worker._ts(start)}]</span> {text}'
        )

    @Slot(bool, str)
    def _on_worker_done(self, ok, message):
        self._task_done(
            self._active_button,
            self._active_status,
            self._active_log,
            ok,
            message,
        )

    def _task_done(self, button, status, log, ok, message):
        button.setEnabled(True)
        status.setText(message)
        log.append(("\n✓ " if ok else "\n✕ ") + message)
        if ok:
            QMessageBox.information(self, "Concluído", message)
        else:
            QMessageBox.critical(self, "Falha no processamento", message)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            answer = QMessageBox.question(
                self, "Sair", "Há um processamento em andamento. Deseja fechar mesmo assim?"
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()


def apply_theme(app: QApplication):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(f"""
        QWidget {{ background:{BG}; color:{TEXT}; }}
        QMainWindow {{ background:{BG}; }}
        #sidebar {{ background:#0D0E14; border-right:1px solid {BORDER}; }}
        #mainArea {{ background:{BG}; }}
        #panel, #statusCard, #cutRow {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:10px; }}
        #navigation {{ background:transparent; border:0; outline:0; }}
        #navigation::item {{ padding:14px 10px; border-radius:7px; color:#C9C9D5; }}
        #navigation::item:selected {{ background:#292A35; color:#FFFFFF; border-left:3px solid {ACCENT}; }}
        QLineEdit, QTextEdit, QComboBox, QSpinBox {{ background:#0F1017; border:1px solid {BORDER}; border-radius:6px; padding:9px; selection-background-color:{ACCENT}; }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border:1px solid {ACCENT}; }}
        QPushButton {{ background:#292A35; border:1px solid #353644; border-radius:7px; padding:9px 13px; }}
        QPushButton:hover {{ border-color:{ACCENT}; background:#333448; }}
        QPushButton:disabled {{ color:#6B6C79; background:#20212A; }}
        #primaryButton {{ background:{ACCENT}; border:0; color:white; font-size:15px; font-weight:700; padding:13px; }}
        #primaryButton:hover {{ background:{PURPLE}; }}
        QProgressBar {{ background:#0D0E14; border:0; border-radius:5px; height:12px; text-align:center; color:white; }}
        QProgressBar::chunk {{ background:{GREEN}; border-radius:5px; }}
        QCheckBox {{ spacing:8px; }}
        QCheckBox::indicator {{ width:17px; height:17px; }}
        QCheckBox::indicator:checked {{ background:{ACCENT}; border:1px solid {ACCENT}; }}
        QScrollArea {{ border:0; }}
        QLabel {{ background:transparent; }}
    """)


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    window = ClipterWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()



