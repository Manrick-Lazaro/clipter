from faster_whisper import WhisperModel
import subprocess
import os

video = "LUZES.mp4"
model_whisper = "large-v3-turbo"
language = "pt"
SRT = "legends.srt"

model = WhisperModel(
    model_whisper, 
    device="cuda", 
    compute_type="float16"
)

segments, info = model.transcribe(
    video,
    language=language
)

def time_formatter(seconds):
    seconds = int(seconds)

    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60

    return f"{h:02}:{m:02}:{s:02}"

with open(SRT, "w", encoding="utf-8") as arquive:
    counter = 1
    for segment in segments:
        start = time_formatter(segment.start)
        end = time_formatter(segment.end)
        text = segment.text.strip()
        arquive.write(f"{counter}\n")
        arquive.write(f"{start} --> {end} \n")
        arquive.write(f"{text}\n\n")
        counter += 1