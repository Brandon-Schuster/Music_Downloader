
# Music Downloader

This program aims to make downloading music from websites a breeze. Mainly to add to your Spotify library for easy accessibility, but feel free to do whatever you want!

- Author: **Brandon Schuster**
- Started: **8/17/2023**

## Required Plugins

1. **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
2. **[ffmpeg](https://ffmpeg.org/download.html)**
3. **[Python](https://www.python.org/downloads/)**

## Steps

1. Install [Python](https://www.python.org/downloads/)
2. Install yt-dlp 
   - a. Open Command Prompt
   - b. Run: `python -m pip install yt-dlp`
3. Install ffmpeg 
   - a. Download [ffmpeg](https://ffmpeg.org/download.html) 
   - b. Extract the files
   - c. Move the extracted folder to a secure folder like `C:\Program Files\`
   - d. In the windows search bar, search for the `Edit the System Environment Variables` page.
   - e. Click on `Environment Variables`
   - f. Under `System variables`, click on the `Path` variable and then click `edit`
   - g. In the `Edit Environment variable` page, click new
   - h. Add the path to `ffmpeg\bin`. **Make sure it is to the bin folder!**
   - i. Test functionality with this command in cmd prmpt: `ffmpeg -version`
4. Install required Python libraries
	- a. Install Pillow and eyed3: `pip install Pillow and eyed3`

Note: I will implement an installer with all of these in the future, or I will just include them with the program.
