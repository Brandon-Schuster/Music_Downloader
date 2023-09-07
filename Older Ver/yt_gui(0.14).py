import tkinter as tk
from tkinter import ttk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import subprocess
import threading
import eyed3
import time  # used for simulating download progress

global thumbnail_label
global global_song_path
thumbnail_label = None
global_song_path = None



def get_video_details(url):
    try:
        command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', '--skip-download', '--get-title', '--get-duration', url]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            result_label.config(text=f"Error fetching video details:\n{stderr}")
            return "", ""
        # Assuming the output has the title first, then duration
        title, duration = stdout.strip().split('\n')
        return title, duration
    except Exception as e:
        result_label.config(text=f"Error: {str(e)}")
        return "", ""
    
    

def on_update_metadata():
    global global_song_path
    if not global_song_path:
        result_label.config(text="Error: Song path not set. Please download a video first.")
        return
    
    artist = artist_entry.get()
    title = title_entry.get()
    album = album_entry.get()
    date = date_entry.get()

    # Check if date is an integer
    try:
        int(date)
    except ValueError:
        result_label.config(text="Error: Date must be an integer.")
        return

    try:
        update_metadata(global_song_path, artist, title, album, date)
        result_label.config(text="Metadata updated successfully!")
    except Exception as e:
        result_label.config(text=f"Error updating metadata: {str(e)}")
        print(f"Error updating metadata: {str(e)}")


def update_metadata(song_path, artist=None, title=None, album=None, date=None):
    audiofile = eyed3.load(song_path)
    if not audiofile.tag:
        audiofile.tag = eyed3.id3.Tag()
        audiofile.tag.file_info = eyed3.id3.FileInfo(song_path)

    if artist:
        audiofile.tag.artist = artist
    if title:
        audiofile.tag.title = title
    if album:
        audiofile.tag.album = album
    if date:
        audiofile.tag.recording_date = date

    audiofile.tag.save()


def embed_cover_art(song_path, cover_art_path, output_path):
    cmd = [
        'ffmpeg', 
        '-i', song_path, 
        '-i', cover_art_path, 
        '-c:a', 'copy',
        '-c:v', 'copy', 
        '-map', '0:a', 
        '-map', '1',
        '-id3v2_version', '3',
        '-metadata:s:v', 'title="Album cover"',
        '-metadata:s:v', 'comment="Cover (Front)"',
        output_path
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise Exception(stderr)
    
# This allows the application to download the video while also displaying the GUI. Preventing the applicaiton from 'Not Responding'
def download_video_threaded():
    url = url_entry.get()
    global global_song_path
    
    # Hide the download button before starting the download
    download_button.place_forget()
    
    # Show the progress bar before starting the download
    progress_bar.place(x=85, y=170, width=420)
    threading.Thread(target=download_video).start()


    if not url:
        result_label.config(text="Please enter a valid URL.")
        return

    title, duration = get_video_details(url)
    if title and duration:
        video_title_label.config(text=f"{title}")  # Changed to value label for title
        video_length_value_label.config(text=f"{duration}")  # Changed to value label for duration

    download_thread = threading.Thread(target=download_video)
    download_thread.start()

def download_video():
    url = url_entry.get()

    for i in range(101):  # Simulate download
            time.sleep(0.05)
            progress_var.set(i)
        
    # Hide the progress bar after download completes
    progress_bar.place_forget()
    # Show the download button again
    download_button.place(x=85, y=165, width=420)

    if not url:
        result_label.config(text="Please enter a valid URL.")
        return

    # Part 1: Download the song and thumbnail
    command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', '--write-thumbnail', url]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    # Check for errors
    if process.returncode != 0:
        result_label.config(text=f"Error during song or thumbnail download:\n{stderr}")
        print(f"Download process error: {stderr}")
        return

    song_path = None
    thumbnail_path = None
    print(stdout)

    for line in stdout.splitlines():
        if "Destination:" in line:
            file_path = line.split("Destination:")[1].strip()
            if file_path.endswith('.webp'):
                thumbnail_path = file_path
            else:
                song_path = file_path
        elif "Writing video thumbnail" in line:
            thumbnail_path = line.split("to:")[1].strip()

    print(f"Parsed song path: {song_path}")
    print(f"Parsed thumbnail path: {thumbnail_path}")

    # Ensure both paths were determined before proceeding
    if not song_path or not thumbnail_path:
        result_label.config(text="Failed to determine song or thumbnail path.")
        return
    
    global global_song_path
    global_song_path = song_path


    if thumbnail_path and thumbnail_path.endswith('.webp'):
        # Convert webp to jpg
        jpg_path = thumbnail_path.replace('.webp', '.jpg')
        conversion_cmd = [
            'ffmpeg', 
            '-i', thumbnail_path,  # The original path
            '-frames:v', '1',  # Only process one frame (since it's an image)
            '-update', '1',    # To ensure it's recognized as a single image output
            jpg_path           # The new jpg path
        ]
        subprocess.run(conversion_cmd)
        thumbnail_path = jpg_path  # Update the thumbnail_path to the new jpg path

        global thumbnail_label

    # Destroy the previous thumbnail label if it exists
    if thumbnail_label:
        thumbnail_label.destroy()

    try:
        # Load the new image thumbnail
        photo = PhotoImage(file=thumbnail_path)

        # Optional: Resize the image if necessary
        photo_width = photo.width() // 4  # These are example values, adjust as needed
        photo_height = photo.height() // 4
        photo = photo.subsample(photo_width, photo_height)

        thumbnail_label = ttk.Label(app, image=photo)
        thumbnail_label.photo = photo  # Keep a reference to avoid garbage collection
        thumbnail_label.place(relx=1, rely=0, anchor="ne")
    except Exception as e:
        print(f"Error loading image: {str(e)}")

    # Part 2: Embed the cover art
    try:
        embed_cover_art(song_path, thumbnail_path, song_path)
        result_label.config(text="Download completed with cover art!")
    except Exception as e:
        result_label.config(text=f"Error during embedding cover art: {str(e)}")
        print(f"Embed cover art error: {str(e)}")



# GUI code
app = tk.Tk()
app.title("Brandon's YouTube Downloader")
app.geometry("900x650")
app.resizable(False, False)

dark_color = "#000000"
light_color = "#FFFFFF"

app.configure(bg=dark_color)

# Style configurations
style = ttk.Style()
style.theme_use('clam')

# Background and foreground configurations for various widgets
style.configure('TFrame', background=dark_color)
style.configure('TLabel', background=dark_color, foreground=light_color)
style.configure('TButton', background=dark_color, foreground=light_color, bordercolor=dark_color)
style.configure('TEntry', fieldbackground=dark_color, background=dark_color, foreground=light_color, insertcolor=light_color)

# Button color changes when pressed or active
style.map('TButton',
          background=[('pressed', light_color), ('active', '#1a1a1a')],
          foreground=[('pressed', dark_color), ('active', light_color)])

# Font for bold text
bold_font = ("TkDefaultFont", 10, "bold")

# Font for bold text
bold_font = ("TkDefaultFont", 10, "bold")

# First Frame Setup
frame = ttk.Frame(app)
frame.columnconfigure(1, weight=1)
frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)  # Adjusted padding for top-left positioning

# Enter YouTube URL
url_label = ttk.Label(frame, text="YouTube URL: ")
url_label.grid(row=0, column=0, sticky=tk.E, pady=(0, 5))
url_entry = ttk.Entry(frame, width=80)
url_entry.grid(row=0, column=1, pady=(0, 5))
url_entry.bind('<Return>', lambda event=None: download_video_threaded())


# Song Title
song_title_label = ttk.Label(frame, text="Song Title:")
song_title_label.grid(row=1, column=0, sticky=tk.W, pady=0)
video_title_label = ttk.Label(frame, text="", font=bold_font, anchor=tk.CENTER)
video_title_label.grid(row=1, column=1, sticky=tk.EW, pady=0)  # Widget stretched but text centered

# Video Length
video_length_label = ttk.Label(frame, text="Length:")
video_length_label.grid(row=2, column=0, sticky=tk.W, pady=0)
video_length_value_label = ttk.Label(frame, text="-:-", font=bold_font, anchor=tk.CENTER)
video_length_value_label.grid(row=2, column=1, sticky=tk.EW, pady=(0, 0))  # Widget stretched but text centered

# Bit Rate
bit_rate_label = ttk.Label(frame, text="Bit Rate:")
bit_rate_label.grid(row=3, column=0, sticky=tk.W, pady=0)
bit_rate_value_label = ttk.Label(frame, text="- bit/s", anchor=tk.CENTER)
bit_rate_value_label.grid(row=3, column=1, sticky=tk.EW, pady=(0, 0))  # Widget stretched but text centered

# Add a progress bar but don't display it initially
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(frame, orient="horizontal", length=200, mode="determinate", variable=progress_var)

download_button = ttk.Button(frame, text="Download", command=download_video_threaded)
download_button.place(x=85, y=165, width=420)  # Initial placement of the download button

# Canvas for album art
album_art_canvas = tk.Canvas(frame, width=250, height=250, bg=dark_color, bd=0, highlightthickness=1, highlightbackground=light_color)
album_art_canvas.grid(row=0, column=2, rowspan=9, padx=60, sticky=tk.E)


# Second Frame Setup
frame = ttk.Frame(app)
frame.pack(pady=15, padx=15, fill=tk.BOTH, expand=True)  # Adjusted padding for top-left positioning


# Metadata fields
artist_label = ttk.Label(frame, text="Artist:")
artist_label.grid(row=5, column=0, sticky=tk.W, pady=5)
artist_entry = ttk.Entry(frame, width=30)
artist_entry.grid(row=5, column=1, sticky=tk.W, pady=5)

title_label = ttk.Label(frame, text="Title:")
title_label.grid(row=6, column=0, sticky=tk.W, pady=5)
title_entry = ttk.Entry(frame, width=30)
title_entry.grid(row=6, column=1, sticky=tk.W, pady=5)

album_label = ttk.Label(frame, text="Album:")
album_label.grid(row=7, column=0, sticky=tk.W, pady=5)
album_entry = ttk.Entry(frame, width=30)
album_entry.grid(row=7, column=1, sticky=tk.W, pady=5)

date_label = ttk.Label(frame, text="Year:")
date_label.grid(row=8, column=0, sticky=tk.W, pady=5)
date_entry = ttk.Entry(frame, width=30)
date_entry.grid(row=8, column=1, sticky=tk.W, pady=5)

# Update Metadata button
update_metadata_button = ttk.Button(frame, text="Update Metadata", command=on_update_metadata)
update_metadata_button.grid(row=9, column=0, columnspan=2, pady=(10, 10))  # Adjusted spacing

# Third Frame Setup
frame = ttk.Frame(app)
frame.pack(pady=0, padx=0, fill=tk.BOTH, expand=True)  # Adjusted padding for top-left positioning

# Result label
result_label = ttk.Label(frame, text="")
result_label.grid(row=1, column=2, rowspan=9, padx=60, sticky=tk.E)


app.mainloop()