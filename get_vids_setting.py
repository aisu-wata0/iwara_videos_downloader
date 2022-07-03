# %%

from typing import Union

# download filename format
filename_download = "{username} - {title} {date_str} {video_id}"

# Directory(s) where videos will be checked for existence
# e.g. r"E:/lewd/iwara"
videos_base_dirs: Union[list, str] = r""
# Directory where the videos will be downloaded to
download_dir = "downloads/"
# glob pattern to recognize video files, its a pathlib Path glob, so it accepts recursive glob.
# default = "**/*.mp4"
videos_globs: Union[list, str] = ["**/*.mp4", "**/*.webm", "**/*.mkv"]
# File in which scraped videos are stored, with metadata.
# videos in here will be downloaded.
videos_filepath: str = "videos.json"

# Either a list of urls or video_ids or a file with a list of ids/urls (list in python format) or a .json file generated while scraping liked videos
videos_list: Union[list, str] = [
    #     "wm0jefm1mbi2ldojn",
]
# regex replacement to make urls into ids, ignore if you don't know what regex is.
# https://ecchi\.iwara\.tv/videos/(.*)$
# "$1",

# delete videos from the list
delete_videos = [
    # "y8enesm6qoh5evz36",
]

# Whether your liked videos list should be obtained and then downloaded
get_liked_videos = False  # False
try_downloading_privated_videos = False  # False
overwrite_small_files = True  # False
like_videos_downloaded = True  # False

# Whether existing videos should be renamed following the formatting variable `filename_download` above
# Can be a list of directories of which only the files withing will be renamed
rename_existing_videos: Union[bool, list] = False
rename_avoid_regex = [] # if these regexes are found on the filename, they wont be renamed
# rename_existing_videos: Union[bool,list] = ["E:/lewd/iwara/wrong_filenames"]

# %%

# Stop getting videos when page gets only videos you already know about
# # (i.e. you reached the pages you already got when you last executed)
break_when_no_new_videos = True

# Even when no download is needed, get video metadata from the website
# (Update views, likes, title, etc. in the metadata file)
# ! ALL VIDEOS
update_metadata = False

# how many tries to get the download link from its page
# sometimes Iwara does fail for no reason
# rerunning the script works perfectly fine as well I guess
timeout_tries = 3
timeout_sleep = 3
# Timedout failures will be logged to a file

# %%

# How the iwara video id's are recognized in your filesystem
# The video ID is in the url, as in: https://www.iwara.tv/videos/{iwara-video-id}
# also, when you download videos the normal way in the website, its the default filename (unless the video is very old)
# If iwara changes how they ID the videos, this needs to be updated

# the id itself
re_video_id_str: str = r"([A-Za-z0-9]{12,})"
# regex to validate a string that should contain only the video id
re_video_id_valid: str = rf"^{re_video_id_str}$"
# regexes to capture the id in the filename, in order of priority
re_video_id_list: Union[list, str] = [
    (
        rf"\b(?<!(twi-)|(san-)){re_video_id_str}[\s_\-]*(source|language)+",
        3,  # capture group where video id is, 0 is entire match
    ),
    (
        rf"\b(?<!(twi-)|(san-)){re_video_id_str}$",
        3,
    ),
]

# %%
DEBUG = True
# %%
# temporary files & backups
max_backups = 2
cache_dir = "cache/"
backup_dir = "bak/"

# aesthetic customization of the progressbar
tqdm_args = {
    "smoothing": 0.0,
    "position": 0,
    "leave": True,
    "bar_format": "{r_bar} {l_bar}{bar}",
    "dynamic_ncols": True,
    "mininterval": 1 / 60,
    "maxinterval": 1 / 24,
}
# %%
