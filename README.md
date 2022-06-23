
# Iwara video downloader

## Run it

`python get_vids.py`

Do the setup and config first, of course.

## Setup

Install the python packages needed.

`pip install -r requirements.txt`

## Config

Define the directory you keep your video files in `get_vids_setting.py` on the variable `videos_base_dirs`. There's an example right above it. This is so you don't download duplicates.

The download directory is defined in `download_dir`. By default it will download videos in the repository folder `"downloads/"`, which might be not what you want.

Decide if you want to check your liked videos and download them (if they can't be found in your listed directories). `True` by default, if you don't want that, disable `get_liked_videos` (set it to False).

If you want to download a list of links or video ids, list them in the variable `videos_list`, there's and example commented there already, but here's another one anyway:

```python
videos_list: Union[list, str] = [
	"wm0jefm1mbi2ldojn",
]
```

### Cookies

To get your liked videos, and download videos in general you need to set your session cookies.

In the file `iwa_cookies.py`, set on the cookies variable the empty keys (`_gid`, `_ga`, and the other one). To get these cookies it will depend on the browser you are using, in Chrome, in a logged in iwara tab, open the DevTools (F12), go on the `Application` tab (on the top of the window), and on the left the sidebar will have a `Storage` item with listed subitems, one of which is `Cookies`, click on it and select the `iwara.tv` subsubitem and the values will be there.

Copy and paste the 3 necessary items.

! **The `SSESS` item however needs both the key (the `Name` column on DevTools) and the value to be copied. The key starts something like `SSESS` and has lots of letters, you need to make that replace `"SSESS"` in the `iwa_cookies.py` file.**