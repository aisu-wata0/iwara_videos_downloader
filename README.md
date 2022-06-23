
# Iwara video downloader

## Setup

Install the python packages needed.

`pip install -r requirements.txt`

## Config

To get your liked videos, and download videos in general you need to set your session cookies.

In the file `iwa_cookies.py`, set on the cookies variable the empty keys (`_gid`, `_ga`, and the other one). To get these cookies it will depend on the browser you are using, in Chrome, in a logged in iwara tab, open the DevTools (F12), go on the `Application` tab (on the top of the window), and on the left the sidebar will have a `Storage` item with listed subitems, one of which is `Cookies`, click on it and select the `iwara.tv` subsubitem and the values will be there.

Copy and paste the 3 necessary items.

! **The `SSESS` item however needs both the key (the `Name` column on DevTools) and the value to be copied. The key starts something like `SSESS` and has lots of letters, you need to make that replace `"SSESS"` in the `iwa_cookies.py` file.**