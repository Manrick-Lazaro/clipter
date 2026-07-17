from yt_dlp import YoutubeDL

url = "https://www.youtube.com/watch?v=h4NzUoUVi38"

options = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
    "outtmpl": r"C:\Users\manri\Downloads\%(title)s.%(ext)s"
}

with YoutubeDL(options) as ydl:
    ydl.download(url)