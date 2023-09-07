import tkinter as tk
from tkinter import ttk, PhotoImage
from PIL import Image, ImageTk, ImageFilter
import subprocess
import threading
import eyed3
import time  # used for simulating download progress
import os
import sys
import io
import re
import shutil
import json
from itertools import cycle

global thumbnail_label
global song_path
global global_song_path
global global_song_title
global_song_title = None
thumbnail_label = None
global_song_path = None

def on_focus_out(event):
    widget = event.widget
    widget.xview_moveto(0)  # Scroll to the start

def get_file_size(file_path):
    try:
        file_size_bytes = os.path.getsize(file_path)
        file_size_megabytes = file_size_bytes / (1024 * 1024)  # Convert bytes to megabytes
        return f"{file_size_megabytes:.2f}"
    except Exception as e:
        print(f"Error fetching file size: {str(e)}\nFile Path: ", file_path)
        return "- Mb"

def get_file_bitrate(file_path):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=bit_rate', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(f"Error fetching bitrate: {stderr}\nBit Rate File Path: ",file_path)
        return "0k"

    # Convert the bitrate to kbps and round to the nearest whole number
    bitrate_in_kbps = int(float(stdout.strip()) / 1000)
    # print("Bit Rate:", bitrate_in_kbps)
    return f"{bitrate_in_kbps}"


def seconds_to_time_format(duration):
    """Converts seconds to a format of minutes:seconds"""
    try:
        duration = int(duration)
        minutes = duration // 60
        seconds = duration % 60
        return f"{minutes}:{seconds:02}"
    except ValueError:
        return "-:-"



def safe_filename(title):
    # Replace spaces with underscores
    s = title.replace(" ", "_")
    
    # Convert non-alphanumeric characters (except '_', '-', '.', and '+') to '_'
    s = ''.join(c if c.isalnum() or c in ('_', '-', '.', '+') else '_' for c in s)
    
    # Replace multiple underscores in a row with a single underscore
    s = re.sub('_+', '_', s)
    
    # Remove leading and trailing underscores
    s = s.strip('_')
    
    return s

class CustomStdOut(io.StringIO):
    def __init__(self, result_text, *args, **kwargs):
        self.result_text = result_text
        super().__init__(*args, **kwargs)

    def write(self, s):
        self.append_to_gui(s)
        return super().write(s)

    def append_to_gui(self, s):
        self.result_text.config(state=tk.NORMAL)  # Temporarily make it editable
        self.result_text.insert(tk.END, s)  # Append the new text
        self.result_text.see(tk.END)  # Scroll to the end, if you want this behavior
        self.result_text.config(state=tk.DISABLED)  # Make it read-only again

    def flush(self):
        # Explicitly add the content to the Text widget
        content = self.getvalue()
        self.append_to_gui(content)
        # Clear the internal buffer
        self.truncate(0)
        self.seek(0)


draggers = []
is_dragging = False
start_x = 0

class ImageDragger:
    def __init__(self, canvas, item):
        self.canvas = canvas
        self.drag_data = {"x": 0, "y": 0, "item": item}

        # Directly bind to the item now, not the tag
        self.canvas.tag_bind(item, "<ButtonPress-1>", self.on_drag_start)
        self.canvas.tag_bind(item, "<ButtonRelease-1>", self.on_drag_stop)
        self.canvas.tag_bind(item, "<B1-Motion>", self.on_drag_motion)

    def on_drag_start(self, event):
        # Store initial position data
        self.drag_data["item"] = self.canvas.find_closest(event.x, event.y)[0]
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag_stop(self, event):
        # Reset the drag information
        self.drag_data["item"] = None
        self.drag_data["x"] = 0
        self.drag_data["y"] = 0

    def on_drag_motion(self, event):
        # Compute how much the mouse has moved
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]

        # Move the object
        self.canvas.move(self.drag_data["item"], dx, 0)  # Only move in X direction

        # Now, we want to ensure that the image doesn't go out of canvas boundaries
        coords = self.canvas.bbox(self.drag_data["item"])
        if coords[0] > 0:  # Left boundary
            self.canvas.move(self.drag_data["item"], -coords[0], 0)
        if coords[2] < 250:  # Right boundary
            self.canvas.move(self.drag_data["item"], 250 - coords[2], 0)

        # Update initial position data
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y


def display_image(thumbnail_path):
    try:
        # Load the new image thumbnail
        image = Image.open(thumbnail_path)

        # Make it 1:1
        image = resize_and_crop(image, 250)
        photo = ImageTk.PhotoImage(image)

        img_id = album_art_canvas.create_image(125, 125, image=photo, tags="img")  # Note the tags argument
        album_art_canvas.image = photo  # Keep a reference to avoid garbage collection
        
        # Initialize the image dragging
        dragger = ImageDragger(album_art_canvas, img_id)
        draggers.append(dragger)

    except Exception as e:
        print(f"Error loading image: {str(e)}")



def resize_and_crop(image, size):
    """
    Resize and then crop the center part of the image to get a square output.
    
    Args:
    - image (Image object): The PIL Image object.
    - size (int): The desired size for the output image.
    
    Returns:
    - Image object: The cropped and resized image.
    """
    
    # Calculate the aspect ratio
    aspect_ratio = image.width / image.height

    # If the image is wider than tall
    if aspect_ratio > 1:
        new_height = size
        new_width = int(size * aspect_ratio)
        left_crop = (new_width - size) // 2
        right_crop = left_crop + size
        image = image.resize((new_width, new_height), Image.BICUBIC)
        image = image.crop((left_crop, 0, right_crop, size))
    # If the image is taller than wide
    elif aspect_ratio < 1:
        new_width = size
        new_height = int(size / aspect_ratio)
        top_crop = (new_height - size) // 2
        bottom_crop = top_crop + size
        image = image.resize((new_width, new_height), Image.BICUBIC)
        image = image.crop((0, top_crop, size, bottom_crop))
    # If the image is square
    else:
        image = image.resize((size, size), Image.BICUBIC)
    
    return image

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

def get_video_details(url,song_path):
    try:
        command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', '--skip-download', '--print-json', url]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            update_result_text(f"Error fetching video details:\n{stderr}")
            return "", "", "", "", ""

        video_data = json.loads(stdout)

        title = video_data.get("title", "")
        duration = str(video_data.get("duration", ""))
        publication_date = video_data.get("upload_date", "")

        # Format the date properly if it exists
        if publication_date:
            publication_date = f"{publication_date[4:6]}/{publication_date[6:]}/{publication_date[:4]}"

        # Extracting bitrate and file size from 'formats'. We'll go for the 'best' format
        formats = video_data.get("formats", [])
        file_size, bit_rate = "", ""


        return title, duration, publication_date, file_size, bit_rate
    except Exception as e:
        update_result_text(f"Error: {str(e)}")
        return "", "", "", "", ""    

def on_update_metadata():
    global global_song_path
   

    # global_song_path = safe_filename(global_song_title)
    if not global_song_path:
        print("Error: Song path not set. Please download a video first.\n",global_song_path)

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
        print("Metadata updated successfully!")
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
    

def get_video_title(url):
    command = ['yt-dlp', '--print', '%(title)s', url]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print(f"Error fetching video title: {stderr}")
        return None

    return stdout.strip()


# This allows the application to download the video while also displaying the GUI. Preventing the applicaiton from 'Not Responding'
def download_video_threaded():

    update_result_text("")

    url = url_entry.get()
    
    # Hide the download button before starting the download
    # download_button.place_forget()
    
    # Show the progress bar before starting the download
    # progress_bar.place(x=150, y=5)  # Adjusted position to be relative to the container frame
    
    if not url:
        update_result_text.config(text="Please enter a valid URL.")
        return

    
    download_thread = threading.Thread(target=download_video)
    download_thread.start()

def download_video():
    url = url_entry.get()

    if not url:
        update_result_text("Please enter a valid URL.")
        return


    # Fetch the video title
    video_title = get_video_title(url)
    if not video_title:
        print("Failed to fetch video title.")
        return

    # Convert video title to a safe filename
    global_song_title = video_title
    safe_video_title = safe_filename(video_title)
    folder_path = os.path.join(r"C:\Users\brand\Music", safe_video_title)
    print("\nFolder Path:",folder_path,"\n")
    

    # Delete the folder and its contents if it exists
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
            print(f"Deleted folder: {folder_path}")
        except PermissionError:
            print(f"Permission denied when trying to delete folder: {folder_path}")
            return
        except Exception as e:
            print(f"Error deleting folder {folder_path}: {e}")
            return

    # Download Thumbnail
    command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', '--skip-download', '--write-thumbnail', url]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    # Check for errors
    if process.returncode != 0:
        update_result_text(f"Error during thumbnail download:\n{stderr}")
        return
    
    thumbnail_path = None
    for line in stdout.splitlines():
        if "Writing video thumbnail" in line:
            thumbnail_path = line.split("to:")[1].strip()

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


    # Download the song 
    command = [r'C:\Program Files\yt-dlp\yt-dlp.exe', url]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()




    # Check for errors
    if process.returncode != 0:
        update_result_text(f"Error during song download:\n{stderr}")
        return



    global global_song_path
    song_path = None
    for line in stdout.splitlines():
        if "Destination:" in line:
            file_path = line.split("Destination:")[1].strip()
            if not file_path.endswith('.webp'):
                song_path = file_path
                global_song_path = os.path.join(r"C:\Users\brand\Music", song_path)



    # Update Song Information
    title, duration, publication_date, file_size, bit_rate = get_video_details(url,song_path)
    bit_rate = get_file_bitrate(song_path)
    file_size = get_file_size(song_path)

    formatted_duration = seconds_to_time_format(duration)

    video_title_label['text'] = title or '-'
    video_length_value_label['text'] = formatted_duration or '-:-'
    publication_value_label['text'] = publication_date or 'M/D/Y'
    file_size_value_label['text'] = file_size + " Mb" if file_size else '- Mb'
    bit_rate_value_label['text'] = bit_rate + " kbps" if bit_rate else '- kbps'
    display_image(thumbnail_path)



    # Embed the cover art



# GUI code
app = tk.Tk()
app.title("Brandon's YouTube Downloader")
app.geometry("900x480")
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

# Frame Setup
frame = ttk.Frame(app)
frame.columnconfigure(1, weight=1)
frame.pack(pady=0, padx=10, fill=tk.BOTH, expand=True)  # Adjusted padding for top-left positioning

# Create a style object
style = ttk.Style()

# Configure the custom style for Button
style.configure('custom.TButton', padding=(0, 5))  # Adjust padding as needed

# Enter YouTube URL
url_label = ttk.Label(frame, text="YouTube URL: ")
url_label.grid(row=0, column=0, sticky=tk.E, pady=0)

url_entry = ttk.Entry(frame, width=65)
url_entry.grid(row=0, column=1, sticky=tk.W, pady=0)
url_entry.bind('<Return>', lambda event=None: download_video_threaded())

# Download Button with custom style
download_button = ttk.Button(frame, text="- Download -", command=download_video_threaded, width=20, style='custom.TButton')
download_button.grid(row=0, column=1, sticky=tk.E, pady=2, padx=(5, 10))  # Adjusted padx

# Adjusting padding for column 1
frame.columnconfigure(1, pad=10)  # Add some padding after column 1

# Song Title
song_title_label = ttk.Label(frame, text="Song Title:")
song_title_label.grid(row=1, column=0, sticky=tk.W, pady=0)
video_title_label = ttk.Label(frame, text="-", anchor=tk.CENTER)
video_title_label.grid(row=1, column=1, sticky=tk.EW, pady=0)

# Video Length
video_length_label = ttk.Label(frame, text="Length:")
video_length_label.grid(row=2, column=0, sticky=tk.W, pady=0)
video_length_value_label = ttk.Label(frame, text="-:-", anchor=tk.CENTER)
video_length_value_label.grid(row=2, column=1, sticky=tk.EW, pady=0)

# File Size
file_size_label = ttk.Label(frame, text="File Size:")
file_size_label.grid(row=3, column=0, sticky=tk.W, pady=0)
file_size_value_label = ttk.Label(frame, text="- Mb", anchor=tk.CENTER)
file_size_value_label.grid(row=3, column=1, sticky=tk.EW, pady=0)

# Bit Rate
bit_rate_label = ttk.Label(frame, text="Bit Rate:")
bit_rate_label.grid(row=4, column=0, sticky=tk.W, pady=0)
bit_rate_value_label = ttk.Label(frame, text="- kbps", anchor=tk.CENTER)
bit_rate_value_label.grid(row=4, column=1, sticky=tk.EW, pady=0)

# Published
publication_label = ttk.Label(frame, text="Published:")
publication_label.grid(row=5, column=0, sticky=tk.W, pady=0)
publication_value_label = ttk.Label(frame, text="M/D/Y", anchor=tk.CENTER)
publication_value_label.grid(row=5, column=1, sticky=tk.EW, pady=0)


# video_title_label.configure(font=bold_font)
# video_length_value_label.configure(font=bold_font)
# file_size_value_label.configure(font=bold_font)
# bit_rate_value_label.configure(font=bold_font)
# publication_value_label.configure(font=bold_font)

# Container Frame for the Download Button
# container_frame = ttk.Frame(frame) 
# container_frame.grid(row=4, column=0, columnspan=2, pady=5, sticky=tk.EW)  # Fills the space, but won't display anything
# Add a progress bar
# progress_var = tk.IntVar()
# progress_bar = ttk.Progressbar(container_frame, orient="horizontal", length=420, mode="determinate", variable=progress_var)

# Assuming an approximate width for the "YouTube URL:" label
padding_for_label = 90  # This is a guess; you might need to adjust it

# Canvas for album art
album_art_canvas = tk.Canvas(frame, width=250, height=250, bg=dark_color, bd=0, highlightthickness=1, highlightbackground=light_color)
album_art_canvas.grid(row=0, column=2, rowspan=6, padx=(0, 5), pady=(10, 0), sticky=tk.N)  # Added padx and pady
# Create text in the center of the canvas
album_art_canvas.create_text(125, 125, text="Album Art", font=("TkDefaultFont", 12), fill=light_color)
# Font for side note
side_note_font = ("TkDefaultFont", 8)
# Side Note
side_note_label = ttk.Label(app,text="(Adjust the Album Art as needed by Dragging)",font=side_note_font,style='TLabel',)
side_note_label.place(x=645, y=270)


# Metadata fields below the canvas
metadata_frame = ttk.Frame(frame)
metadata_frame.grid(row=11, column=2, sticky=tk.N, pady=40)

artist_label = ttk.Label(metadata_frame, text="Artist:")
artist_label.grid(row=0, column=0, sticky=tk.W, pady=5)  
artist_entry = ttk.Entry(metadata_frame, width=32)
artist_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
artist_entry.bind("<FocusOut>", on_focus_out)

title_label = ttk.Label(metadata_frame, text="Title:")
title_label.grid(row=1, column=0, sticky=tk.W, pady=5)   
title_entry = ttk.Entry(metadata_frame, width=32)
title_entry.grid(row=1, column=1, sticky=tk.W, pady=5)   
title_entry.bind("<FocusOut>", on_focus_out)

album_label = ttk.Label(metadata_frame, text="Album:")
album_label.grid(row=2, column=0, sticky=tk.W, pady=5)   
album_entry = ttk.Entry(metadata_frame, width=32)
album_entry.grid(row=2, column=1, sticky=tk.W, pady=5)   
album_entry.bind("<FocusOut>", on_focus_out)

date_label = ttk.Label(metadata_frame, text="Year:")
date_label.grid(row=3, column=0, sticky=tk.W, pady=5)    
date_entry = ttk.Entry(metadata_frame, width=32)
date_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
date_entry.bind("<FocusOut>", on_focus_out)



# Update Metadata button
update_metadata_button = ttk.Button(metadata_frame, text="- Update Image Position & Metadata -", command=on_update_metadata)
update_metadata_button.grid(row=4, column=0, columnspan=2, pady=(10, 0))

# # Download Label
# progress_bar_label = ttk.Label(frame, text="Download")
# progress_bar_label.place(x=0, y=275, width=580)  # Set width as per your requirement



# Creating a Text widget to replace the Label
result_text = tk.Text(frame, height=10, width=75, bg='black', fg='white', wrap=tk.WORD, borderwidth=2, relief="solid")
result_text.grid(row=11, column=0, columnspan=3, sticky=tk.W, padx=0, pady=10)
result_text.config(highlightbackground="white", highlightcolor="white", highlightthickness=1, bd=0)

# Disabling editing but allowing copying
result_text.config(state=tk.DISABLED)

sys.stdout = CustomStdOut(result_text)
print("Welcome user! Please paste a YouTube URL above and download away (*^ω^)\n\n\n\n\n\n")
print("Version: Alpha")
print("Copyright ©: Brandon Schuster, 2023")



app.mainloop()