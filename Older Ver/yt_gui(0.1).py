import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import eyed3
from eyed3.id3.frames import ImageFrame
from PIL import Image
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC



def add_cover_with_mutagen(mp3_path, cover_path):
    audio = MP3(mp3_path, ID3=ID3)

    # Add ID3 tag if it doesn't exist
    try:
        audio.add_tags()
    except Exception:
        pass

    with open(cover_path, 'rb') as albumart:
        audio.tags.add(
            APIC(
                encoding=3,         # 3 is for utf-8
                mime='image/jpeg',  # image/jpeg or image/png
                type=3,             # 3 is for the cover image
                desc=u'Cover',
                data=albumart.read()
            )
        )
    audio.save()


def set_metadata_and_cover_art(file_path, thumbnail_path):
    try:
        audio_file = eyed3.load(file_path)
        if audio_file.tag is None:
            audio_file.tag = eyed3.id3.Tag()
            audio_file.tag.file_info = eyed3.id3.FileInfo(file_path)

        # remove all existing images in the tag
        for img in audio_file.tag.frame_set.get('APIC', []):
            audio_file.tag.frame_set['APIC'].remove(img)

        # Add the cover art
        with open(thumbnail_path, 'rb') as img_data:
            audio_file.tag.images.set(type_=eyed3.id3.frames.ImageFrame.FRONT_COVER, 
                                      img_data=img_data.read(), 
                                      mime_type='image/jpeg',
                                      description=u'Front cover')
        
        audio_file.tag.save()
    except Exception as e:
        print(f"Error in set_metadata_and_cover_art: {e}")

def convert_webp_to_jpg(webp_path):
    with Image.open(webp_path) as im:
        jpg_path = webp_path.rsplit('.', 1)[0] + '.jpg'
        im.save(jpg_path, "JPEG")
    return jpg_path

def download_video_threaded():
    # Use a separate thread for the downloading process
    download_thread = threading.Thread(target=download_video)
    download_thread.start()

def download_video():
    url = url_entry.get()

    if not url:
        result_label.config(text="Please enter a valid URL.")
        return

    # Part 1: Download the song
    command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', url]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    stdout, stderr = process.communicate()

    # Check for errors in song download
    if process.returncode != 0:
        result_label.config(text="Error during song download: " + stderr)
        return  # We exit here if the song download had an error

    song_path = None
    for line in stdout.splitlines():
        if "Destination:" in line:
            song_path = line.split("Destination:")[1].strip()

    # Part 2: Download the thumbnail
    thumbnail_command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', '--skip-download', '--write-thumbnail', url]
    thumbnail_process = subprocess.Popen(thumbnail_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    thumb_stdout, thumb_stderr = thumbnail_process.communicate()

    # Print full output for thumbnail command for debugging
    print("Thumbnail command stdout:", thumb_stdout)
    print("Thumbnail command stderr:", thumb_stderr)

    if thumbnail_process.returncode != 0:
        result_label.config(text="Error during thumbnail download.")
        return  # We exit here if the thumbnail download had an error

    thumbnail_path = None
    for line in thumb_stdout.splitlines():
        if "Writing video thumbnail" in line:
            thumbnail_path = line.split(" to: ")[1].strip()

    if thumbnail_path.endswith('.webp'):
        thumbnail_path = convert_webp_to_jpg(thumbnail_path)

    if song_path and thumbnail_path:
        # Part 3: Set the thumbnail as cover art
        print("Song path:", song_path)
        print("Thumbnail path:", thumbnail_path)
        add_cover_with_mutagen(song_path, thumbnail_path)
        result_label.config(text="Download completed with cover art!")
    else:
        result_label.config(text="Download completed, but unable to set cover art.")



# GUI code remains mostly the same with layout adjustments

app = tk.Tk()
app.title("Brandon's YouTube Downloader")
app.geometry("900x700")  # Making the window size bigger
app.resizable(False, False)

dark_color = "#000000"
light_color = "#FFFFFF"

app.configure(bg=dark_color)

style = ttk.Style()
style.theme_use('clam')
style.configure('TFrame', background=dark_color)
style.configure('TLabel', background=dark_color, foreground=light_color)
style.configure('TButton', background=dark_color, foreground=light_color, bordercolor=dark_color)
style.configure('TEntry', fieldbackground=dark_color, background=dark_color, foreground=light_color, insertcolor=light_color)

style.map('TButton',
          background=[('pressed', dark_color), ('active', '#1a1a1a')],
          foreground=[('pressed', light_color), ('active', light_color)])

frame = ttk.Frame(app)
frame.pack(pady=50, padx=50, fill=tk.BOTH, expand=True)  # Adjusting the padding for better centering

url_label = ttk.Label(frame, text="Enter YouTube URL:")
url_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

url_entry = ttk.Entry(frame, width=40)
url_entry.grid(row=1, column=0, columnspan=2, pady=(0, 20))

download_button = ttk.Button(frame, text="Download", command=download_video_threaded)
download_button.grid(row=2, column=0, columnspan=2)

result_label = ttk.Label(frame, text="")
result_label.grid(row=3, column=0, columnspan=2, pady=20)

app.mainloop()
