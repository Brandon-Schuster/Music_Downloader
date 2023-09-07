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

# To set or update the content, use this method:
def update_result_text(new_text):
    result_text.config(state=tk.NORMAL)  # Temporarily make it editable
    result_text.delete(1.0, tk.END)  # Clear existing content
    result_text.insert(tk.END, new_text)  # Insert the new text
    result_text.config(state=tk.DISABLED)  # Make it read-only again

def center_window(root):
    # Get window width and height
    window_width = root.winfo_reqwidth()
    window_height = root.winfo_reqheight()

    # Get screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate position x, y coordinates
    x = (screen_width - window_width) / 3.25
    y = (screen_height - window_height) / 4

    root.geometry('+%d+%d' % (x, y))

def get_video_details(url):
    try:
        command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', '--skip-download', '--get-title', '--get-duration', url]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            update_result_text(f"Error fetching video details:\n{stderr}")
            return "", ""
        # Assuming the output has the title first, then duration
        title, duration = stdout.strip().split('\n')
        return title, duration
    except Exception as e:
        update_result_text(f"Error: {str(e)}")
        return "", ""
    
    

def on_update_metadata():
    global global_song_path
    if not global_song_path:
        update_result_text.config(text="Error: Song path not set. Please download a video first.")
        return
    
    artist = artist_entry.get()
    title = title_entry.get()
    album = album_entry.get()
    date = date_entry.get()

    # Check if date is an integer
    try:
        int(date)
    except ValueError:
        update_result_text.config(text="Error: Date must be an integer.")
        return

    try:
        update_metadata(global_song_path, artist, title, album, date)
        update_result_text.config(text="Metadata updated successfully!")
    except Exception as e:
        update_result_text(f"Error updating metadata: {str(e)}")
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
    progress_bar.place(x=85, y=5)  # Adjusted position to be relative to the container frame
    
    threading.Thread(target=download_video).start()

    if not url:
        update_result_text.config(text="Please enter a valid URL.")
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
    download_button.place(x=85, y=5)  # Adjusted position to be relative to the container frame

    if not url:
        update_result_text.config(text="Please enter a valid URL.")
        return

    # Part 1: Download the song and thumbnail
    command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', '--write-thumbnail', url]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    # Check for errors
    if process.returncode != 0:
        update_result_text(f"Error during song or thumbnail download:\n{stderr}")
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
        update_result_text.config(text="Failed to determine song or thumbnail path.")
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
        update_result_text.config(text="Download completed with cover art!")
    except Exception as e:
        update_result_text(f"Error during embedding cover art: {str(e)}")
        print(f"Embed cover art error: {str(e)}")



# GUI code
app = tk.Tk()
app.title("Brandon's YouTube Downloader")
app.geometry("900x500")
app.resizable(False, False)
center_window(app)

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

# Frame Setup
frame = ttk.Frame(app)
frame.columnconfigure(1, weight=1)
frame.pack(pady=0, padx=10, fill=tk.BOTH, expand=True)  # Adjusted padding for top-left positioning

# Enter YouTube URL
url_label = ttk.Label(frame, text="YouTube URL:")
url_label.grid(row=0, column=0, sticky=tk.E, pady=0)
url_entry = ttk.Entry(frame, width=80)
url_entry.grid(row=0, column=1, pady=0)
url_entry.bind('<Return>', lambda event=None: download_video_threaded())

# Song Title
song_title_label = ttk.Label(frame, text="Song Title:")
song_title_label.grid(row=1, column=0, sticky=tk.W, pady=0)
video_title_label = ttk.Label(frame, text="-", font=bold_font, anchor=tk.CENTER)
video_title_label.grid(row=1, column=1, sticky=tk.EW, pady=0)

# Video Length
video_length_label = ttk.Label(frame, text="Length:")
video_length_label.grid(row=2, column=0, sticky=tk.W, pady=0)
video_length_value_label = ttk.Label(frame, text="-:-", font=bold_font, anchor=tk.CENTER)
video_length_value_label.grid(row=2, column=1, sticky=tk.EW, pady=0)

# Bit Rate
bit_rate_label = ttk.Label(frame, text="Bit Rate:")
bit_rate_label.grid(row=3, column=0, sticky=tk.W, pady=0)
bit_rate_value_label = ttk.Label(frame, text="- bit/s", anchor=tk.CENTER)
bit_rate_value_label.grid(row=3, column=1, sticky=tk.EW, pady=0)

# Container Frame for the Download Button
container_frame = ttk.Frame(frame) 
container_frame.grid(row=4, column=0, columnspan=2, pady=5, sticky=tk.EW)  # Fills the space, but won't display anything

# Add a progress bar
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(container_frame, orient="horizontal", length=420, mode="determinate", variable=progress_var)

# Assuming an approximate width for the "YouTube URL:" label
padding_for_label = 90  # This is a guess; you might need to adjust it

# Download Button
download_button = ttk.Button(container_frame, text="Download", command=download_video_threaded, width=80)
download_button.pack(pady=5, padx=(80, 0))  # Adding 10 pixels of left padding

# Canvas for album art
album_art_canvas = tk.Canvas(frame, width=250, height=250, bg=dark_color, bd=0, highlightthickness=1, highlightbackground=light_color)
album_art_canvas.grid(row=0, column=2, rowspan=6, padx=(0, 5), pady=(10, 0), sticky=tk.N)  # Added padx and pady
# Create text in the center of the canvas
album_art_canvas.create_text(125, 125, text="Album Art", font=("Helvetica Neue", 14), fill=light_color)



# Metadata fields below the canvas
metadata_frame = ttk.Frame(frame)
metadata_frame.grid(row=11, column=2, sticky=tk.N, pady=40)  # Added some padding here

artist_label = ttk.Label(metadata_frame, text="Artist:")
artist_label.grid(row=0, column=0, sticky=tk.W, pady=5)  # Updated pady
artist_entry = ttk.Entry(metadata_frame, width=30)
artist_entry.grid(row=0, column=1, sticky=tk.W, pady=5)  # Updated pady

title_label = ttk.Label(metadata_frame, text="Title:")
title_label.grid(row=1, column=0, sticky=tk.W, pady=5)   # Updated pady
title_entry = ttk.Entry(metadata_frame, width=30)
title_entry.grid(row=1, column=1, sticky=tk.W, pady=5)   # Updated pady

album_label = ttk.Label(metadata_frame, text="Album:")
album_label.grid(row=2, column=0, sticky=tk.W, pady=5)   # Updated pady
album_entry = ttk.Entry(metadata_frame, width=30)
album_entry.grid(row=2, column=1, sticky=tk.W, pady=5)   # Updated pady

date_label = ttk.Label(metadata_frame, text="Year:")
date_label.grid(row=3, column=0, sticky=tk.W, pady=5)    # Updated pady
date_entry = ttk.Entry(metadata_frame, width=30)
date_entry.grid(row=3, column=1, sticky=tk.W, pady=5)    # Updated pady


# Update Metadata button
update_metadata_button = ttk.Button(metadata_frame, text="Update Metadata", command=on_update_metadata)
update_metadata_button.grid(row=4, column=0, columnspan=2, pady=(0, 0))

# Creating a Text widget to replace the Label
result_text = tk.Text(frame, height=10, width=75, bg='black', fg='white', wrap=tk.WORD, borderwidth=2, relief="solid")
result_text.grid(row=11, column=0, columnspan=3, sticky=tk.W, padx=0, pady=10)
result_text.config(highlightbackground="white", highlightcolor="white", highlightthickness=1, bd=0)

# Disabling editing but allowing copying
result_text.config(state=tk.DISABLED)

app.mainloop()