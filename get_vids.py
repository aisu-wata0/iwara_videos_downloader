#%%

import os
import time
import datetime
import logging
import shutil
import math
import re
import pickle
import json
import urllib.request
from urllib.error import HTTPError
import urllib.parse
from pathlib import Path
from threading import Thread
import traceback
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# %%

from iwa_cookies import cookies, headers
from get_vids_setting import *

# %%


def removeOldFiles(list_of_files, max_files):
    old_files = list(
        sorted(
            list_of_files,
            key=lambda x: os.stat(x).st_ctime,
            reverse=True,
        )
    )[max_files:]
    for f in old_files:
        os.remove(f)
    return old_files


save_funs = {
    "pickle": (pickle.dump, "wb"),
    "json": (lambda data, f: json.dump(data, f, indent=2), "w"),
}


def save_file(filepath, data, save_fun, backup_dir=backup_dir, max_backups=max_backups):
    """Save data to filepath. Creates backup in `backup_dir` and deletes old backups too keep them at `max_backups`."""
    if isinstance(save_fun, str):
        save_fun = save_funs[save_fun]
    filepath_bak = ""
    if backup_dir:
        backup_dir = Path(filepath).parent / backup_dir
        filepath_bak = (
            str(backup_dir / str(Path(filepath).name))
            + "-"
            + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        )
    try:
        try:
            if backup_dir:
                Path(filepath_bak).parent.mkdir(exist_ok=True)
                shutil.copyfile(filepath, filepath_bak)
                try:
                    removeOldFiles(
                        Path(backup_dir).glob(f"{Path(filepath).name}*"), max_backups
                    )
                except Exception as e:
                    logging.exception(e)
        except FileNotFoundError:
            pass
        if "b" in save_fun[1]:
            with open(filepath, save_fun[1]) as f:
                save_fun[0](data, f)
        else:
            with open(filepath, save_fun[1], encoding="utf8") as f:
                save_fun[0](data, f)
        print("Saved!", filepath)
    except Exception as e:
        if backup_dir:
            shutil.copyfile(filepath_bak, filepath_bak + ".err")
        logging.warning("Exception on saving file ", filepath)
        logging.exception(e)


def save_file_json(filepath, data):
    return save_file(filepath, data, save_fun="json")


def save_file_pickle(filepath, data):
    return save_file(filepath, data, save_fun="pickle")


# %%


def openUrl(url):
    response = requests.get(url, headers=headers, cookies=cookies)
    return response


def readUrl(address):
    response = openUrl(address)
    if response.status_code == 200:
        html = BeautifulSoup(response.content, "html.parser")
        error_string = "404: Page Not Found"
        if html.find(text=error_string) is not None:
            raise HTTPError(address, code=404, msg=error_string, hdrs=None, fp=None)
        return html
    else:
        raise Exception(
            f"Error while reading url, response.status_code={response.status_code}"
        )


# %%
def get_date_str(text):
    date_str = ""
    date_split_strs = ["作成日:", "on "]
    for ds in date_split_strs:
        if ds not in text:
            continue
        try:
            date_str = text.split(ds)[-1].strip()
            break
        except IndexError:
            pass
    return date_str


# %%

videos = {}
filepath = videos_filepath
try:
    with open(filepath, "rb") as f:
        videos = json.load(f)
except FileNotFoundError:
    logging.warning(
        f"Cache file {filepath} not found, hopefully this is your first time running this script."
    )
except Exception as e:
    logging.exception(e)
print(f"Found existing {len(videos.keys())} in {filepath} cache")


# %%

if get_liked_videos:
    page_num = 0
    videos_new = {}

    try:
        while True:
            video_download_url = (
                "https://ecchi.iwara.tv/user/liked?page="
                + urllib.parse.quote(str(page_num))
            )
            print("Getting... ", video_download_url)
            soup = readUrl(video_download_url)
            # class_str = "node-teaser"
            class_str = "node-video"
            items = soup.find_all("div", class_=class_str)
            if not items:
                print("No items found, breaking from loop")
                break
            print("Got ", len(items), " items")
            new_items = 0
            for item in items:
                item_link = item.find("a")
                if item_link is not None:
                    vid_id = item_link.get("href").split("/")[-1]
                    if vid_id not in videos:
                        new_items += 1
                    videos_new[vid_id] = {
                        "title": item.find("h3", class_="title").text,
                        "username": item.find("a", class_="username").text,
                        "views": item.find("div", class_="left-icon").text.strip(),
                        "likes": item.find("div", class_="right-icon").text.strip(),
                    }
                    node_img = item.find("img")
                    if node_img:
                        videos_new[vid_id]["thumbnail"] = node_img.get("src")

            print(new_items, " new items")

            page_num += 1
            if break_when_no_new_videos:
                if not new_items:
                    break

    except KeyboardInterrupt as e:
        print("Stopped by keyboard interrupt")
    except Exception as e:
        print("Caught exception")
        logging.exception(e)

    if videos_new:
        videos = {**videos_new, **videos}

        print(len(videos.keys()), " videos total,", len(videos_new.keys()), " new")

        def saveNoInterrupt0():
            save_file_json(videos_filepath, videos)

        a = Thread(target=saveNoInterrupt0)
        a.start()
        a.join()

# %%

searches = {}
filepath = searches_filepath
try:
    with open(filepath, "rb") as f:
        searches = json.load(f)
except FileNotFoundError:
    pass
except Exception as e:
    logging.exception(e)
print(f"Found existing {len(searches.keys())} in {filepath} cache")


# %%


def get_search_videos(search_query):
    page_num = 0
    searches_new = {}

    try:
        while True:
            video_download_url = f"https://www.iwara.tv/search?query={urllib.parse.quote(str(search_query))}&page={urllib.parse.quote(str(page_num))}"
            print("Getting... ", video_download_url)
            soup = readUrl(video_download_url)
            class_str = "views-column"
            items = soup.find_all("div", class_=class_str)
            if not items:
                print("No items found, breaking from loop")
                break
            print("Got ", len(items), " items")
            new_items = 0
            for item in items:
                node_username = item.find("a", class_="username")
                if node_username is not None:
                    node_title = None
                    title = None
                    for tt in ["h1", "h3"]:
                        node_title = item.find(tt, class_="title")
                        if node_title:
                            title = node_title.text.strip()
                            break
                    if node_title is None:
                        continue
                    vid_id = None
                    is_image = False
                    node_vid_id = node_title.find("a")
                    if node_vid_id:
                        vid_id = node_vid_id.get("href").split("/")[-1]
                    else:
                        is_image = True
                        node_share = item.find("div", class_="share-icons").find("a")
                        vid_id = node_share.get("href").split("/")[-1].split("%2F")[-1]
                    print(vid_id)
                    if vid_id not in searches.get(search_query, {}):
                        new_items += 1
                    searches_new[vid_id] = {
                        "username": node_username.text,
                    }
                    searches_new[vid_id]["title"] = title
                    searches_new[vid_id]["is_image"] = is_image
                    node_img = item.find("img")
                    if node_img:
                        searches_new[vid_id]["thumbnail"] = node_img.get("src")
                    node_views = item.find("div", class_="node-views")
                    if node_views:
                        searches_new[vid_id]["views"] = node_views.text.strip()

                    video_info = item.find("div", class_="video-info")
                    if video_info:
                        searches_new[vid_id]["views"] = video_info.text.strip().split()[
                            0
                        ]
                        searches_new[vid_id]["likes"] = video_info.text.strip().split()[
                            -1
                        ]

                    date_node = item.find("div", class_="submitted")
                    if date_node:
                        date_str = get_date_str(date_node.text)
                        if date_str:
                            searches_new[vid_id]["date"] = date_str
                    if "views" in searches_new[vid_id]:
                        print("views")
                        print(searches_new[vid_id]["views"])
                    if "likes" in searches_new[vid_id]:
                        print("likes")
                        print(searches_new[vid_id]["likes"])
            print(new_items, " new items")

            page_num += 1
            if break_when_no_new_videos and not update_metadata:
                if not new_items:
                    break

    except KeyboardInterrupt as e:
        print("Stopped by keyboard interrupt")
    except Exception as e:
        print("Caught exception")
        logging.exception(e)

    if searches_new:
        if search_query in searches:
            searches[search_query] = searches_new
        else:
            searches[search_query] = searches_new
        print(
            len(searches[search_query].keys()),
            " items total,",
            len(searches_new.keys()),
            " new",
        )

        def saveNoInterrupt0():
            save_file_json(searches_filepath, searches)

        a = Thread(target=saveNoInterrupt0)
        a.start()
        a.join()


def make_html(items, name):
    with open(f"{name}.html", "w") as outfile:
        keys = ["username", "title", "thumbnail", "views", "likes", "date" "url"]
        html_table_id = "iw"

        outfile.write(f'<table id="{html_table_id}" class="searchable  sortable">\n')
        outfile.write("<thead>\n")
        outfile.write("\t<tr>\n")
        for idx, key in enumerate(keys):
            outfile.write(f'\t<th onclick="sortTable({idx})">' + key + "</th>\n")
        outfile.write("\t<th>" + "url" + "</th>\n")
        outfile.write("\t</tr>\n")
        outfile.write("</thead>\n")

        outfile.write("<tbody>\n")
        for k, item in items.items():
            outfile.write("\t<tr>\n")
            for key in keys:
                v = " "
                if key in item:
                    v = item[key]
                if key == "thumbnail":
                    outfile.write(
                        f'\t\t<td><img src="https://{v[2:]}" style="max-height: 220px;">'
                        + "</img></td>\n"
                    )
                else:
                    outfile.write("\t\t<td>" + str(v) + "</td>\n")
            url = (
                f"https://www.iwara.tv/images/{k}"
                if item["is_image"]
                else f"https://www.iwara.tv/videos/{k}"
            )
            outfile.write(f'\t\t<td><a href="{url}">' + url + "</a></td>\n")
            outfile.write("\t</tr>\n")
        outfile.write("</tbody>\n")

        html_script = (
            """
        <script>
        function sortTable(n) {
        var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
        table = document.getElementById("""
            f'"{html_table_id}");'
            + """
        switching = true;
        // Set the sorting direction to ascending:
        dir = "asc";
        /* Make a loop that will continue until
        no switching has been done: */
        while (switching) {
            // Start by saying: no switching is done:
            switching = false;
            rows = table.rows;
            /* Loop through all table rows (except the
            first, which contains table headers): */
            for (i = 1; i < (rows.length - 1); i++) {
            // Start by saying there should be no switching:
            shouldSwitch = false;
            /* Get the two elements you want to compare,
            one from current row and one from the next: */
            x = rows[i].getElementsByTagName("TD")[n];
            y = rows[i + 1].getElementsByTagName("TD")[n];
            /* Check if the two rows should switch place,
            based on the direction, asc or desc: */
			if (dir == "asc") {
				var xt = x.innerHTML.toLowerCase().replace(/,/g, "");
				var yt = y.innerHTML.toLowerCase().replace(/,/g, "");
				if (isNaN(Number(xt)) || isNaN(Number(yt))) {
					if (xt > yt) {
					// If so, mark as a switch and break the loop:
					shouldSwitch = true;
					break;
					}
				} else {
					if (Number(xt) > Number(yt)) {
					// If so, mark as a switch and break the loop:
					shouldSwitch = true;
					break;
					}
				}
                
            } else if (dir == "desc") {
				var xt = x.innerHTML.toLowerCase().replace(/,/g, "");
				var yt = y.innerHTML.toLowerCase().replace(/,/g, "");
				if (isNaN(Number(xt)) || isNaN(Number(yt))) {
					if (xt < yt) {
					// If so, mark as a switch and break the loop:
					shouldSwitch = true;
					break;
					}
				} else {
					if (Number(xt) < Number(yt)) {
					// If so, mark as a switch and break the loop:
					shouldSwitch = true;
					break;
					}
				}
            }
            }
            if (shouldSwitch) {
            /* If a switch has been marked, make the switch
            and mark that a switch has been done: */
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
            // Each time a switch is done, increase this count by 1:
            switchcount ++;
            } else {
            /* If no switching has been done AND the direction is "asc",
            set the direction to "desc" and run the while loop again. */
            if (switchcount == 0 && dir == "asc") {
                dir = "desc";
                switching = true;
            }
            }
        }
        }
        </script>
        """
        )

        outfile.write(html_script)


for search_query in search_queries:
    get_search_videos(search_query)
    make_html(searches[search_query], f"search-{search_query}")

# %%

import ast


def open_data_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            file_str = ""
            for l in f:
                file_str += l + "\n"
            return ast.literal_eval(file_str)
    except FileNotFoundError:
        logging.warning(f"File {filepath} not found!")
    except Exception as e:
        logging.exception(e)
    return None


if videos_list:
    if isinstance(videos_list, str):
        if videos_list != videos_filepath:
            filepath = videos_list
            videos_list = open_data_file(filepath)

    if isinstance(videos_list, dict):
        videos = {**videos_list, **videos}
        print(f"video list has {len(videos_list.keys())} items")
    elif isinstance(videos_list, list):
        videos = {**{v.split("/")[-1]: {} for v in videos_list}, **videos}
        print(f"video list has {len(videos_list)} items")

print(f"{len(videos.keys())} videos total")

# %%

skipped = []
skipped_by_name = []
errors = []

existing_videos = {}


if not videos_base_dirs:
    logging.error(
        f"No video base directories specified, please set `{videos_base_dirs}` in the settings file."
    )
    exit(1)
if not videos_globs:
    logging.error(
        f"No videos_globs specified, please set `{videos_globs}` in the settings file."
    )
    exit(1)

video_id_inv_chars = re.compile(r"[.\s\?\\/:*?？\"<>\|]+")
if not isinstance(videos_globs, list):
    videos_globs = [videos_globs]
if not isinstance(videos_base_dirs, list):
    videos_base_dirs = [videos_base_dirs]

try:
    re_video_id_str = re.compile(re_video_id_valid, re.IGNORECASE)
    re_video_id_valid = re.compile(re_video_id_valid, re.IGNORECASE)

    if not isinstance(re_video_id_list, list):
        re_video_id_list = [re_video_id_list]
    re_video_id_list = [
        (
            re.compile(re_video_id[0], re.IGNORECASE),
            re_video_id[1],
        )
        for re_video_id in re_video_id_list
    ]
except ValueError:
    pass


def get_video_id_from_filename(fname):
    video_id = ""
    matched = None
    for re_video_id, group_idx in re_video_id_list:
        match = re_video_id.search(fname)
        if match:
            matched = match
            video_id = match.group(group_idx)
            break
    if not matched:
        video_id = fname.split()[-1].lower()
        video_id = video_id.split("_source")[0]
        video_id = video_id.split("_")[-1]
        video_id = video_id_inv_chars.sub("", video_id)
    try:
        if not video_id:
            return None
        is_valid = re_video_id_valid.match(video_id)
        if not is_valid:
            return None
        return video_id.lower()
    except:
        pass
        print(
            "Error while matching video id",
            "fname",
            fname,
            "video_id",
            video_id,
            "matched",
            matched,
        )
        if matched:
            print("matched.groups()", matched.groups())
    return None


for videos_base_dir in [*videos_base_dirs, download_dir]:
    print("Finding existing videos in ", videos_base_dir)
    for videos_glob in videos_globs:
        for f in Path(videos_base_dir).glob(videos_glob):
            # get video ids from filename
            video_id = get_video_id_from_filename(f.stem)
            if video_id not in existing_videos:
                if video_id:
                    existing_videos[video_id] = str(f)
                else:
                    existing_videos[str(f.stem)] = str(f)

# sort by key length
existing_videos = {
    k: v for k, v in sorted(existing_videos.items(), key=lambda item: len(item[0]))
}
print("Found ", len(existing_videos.keys()), " existing videos")
save_file_json("existing_videos.json", existing_videos)

# %%

removed_videos = []

for i in delete_videos:
    if i in videos:
        print(f"# removed {i}")
        del videos[i]
        removed_videos.append(i)
    if i in existing_videos:
        print(f'rm "{existing_videos[i]}"')
        try:
            Path(existing_videos[i]).unlink()
        except FileNotFoundError as e:
            pass
        except Exception as e:
            print(f"# Error while deleting file {existing_videos[i]}: ", str(e))

if removed_videos:
    save_file_json("videos_removed.json", removed_videos)

# %%


if rename_existing_videos:
    for video_id in existing_videos.keys():
        if video_id not in videos:
            continue
        if (
            rename_existing_videos
            and (
                type(rename_existing_videos) in (bool,)
                or (
                    isinstance(rename_existing_videos, (list, tuple))
                    and any(
                        (
                            str(Path(existing_videos[video_id])).startswith(p)
                            for p in rename_existing_videos
                        )
                    )
                )
            )
            and not any(
                re.search(r, existing_videos[video_id]) for r in rename_avoid_regex
            )
        ):
            filename = (
                filename_download.format(
                    username=videos[video_id]["username"],
                    title=videos[video_id]["title"],
                    date_str=videos[video_id]["date"],
                    video_id=video_id,
                )
                + Path(existing_videos[video_id]).suffix
            )
            filename = re_filename_invalid_chars.sub(" ", filename)
            filepath = Path(existing_videos[video_id]).parent / filename

            if not re.match(r"^[0-9T-]{16,16}$", videos[video_id]["date"]):
                print(
                    f'Error on renaming video_id {video_id}: date in metadata is wrong (fix its entry in videos.json)  "{Path(existing_videos[video_id])}"'
                )
                continue
            try:
                Path(existing_videos[video_id]).rename(filepath)
            except OSError:
                print(
                    f'Error on renaming video_id {video_id}: mv  "{Path(existing_videos[video_id])}"   "{filepath}"'
                )

# %%
def saveNoInterrupt2():
    save_file_json(videos_filepath, videos)


a = Thread(target=saveNoInterrupt2)
a.start()
a.join()
# %%

downloaded_videos = {}
redownloads = {}
liked_videos = []

from selenium.webdriver.remote.remote_connection import LOGGER

LOGGER.setLevel(logging.ERROR)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920x1920")

# download Chrome Webdriver
# https://sites.google.com/a/chromium.org/chromedriver/download
# put driver executable file in the script directory
chrome_driver = os.path.join(os.getcwd(), "chromedriver")

# driver = webdriver.Chrome(options=chrome_options, executable_path=chrome_driver)
driver = webdriver.Chrome(
    options=chrome_options, service=Service(ChromeDriverManager().install())
)

url_base = "https://ecchi.iwara.tv/"

load_timeout = 120
driver.set_page_load_timeout(load_timeout)
driver.get(url_base)
for cookie in cookies.items():
    driver.add_cookie({"name": cookie[0], "value": cookie[1]})
try:
    for video_id in list(videos.keys())[:]:
        filepath = None
        skip = False
        existing_file = None
        privated = False
        if video_id in existing_videos:
            skipped.append(video_id)
            existing_file = existing_videos[video_id]
            skip = True
        if not try_downloading_privated_videos and (
            "privated" in videos[video_id] and videos[video_id]["privated"]
        ):
            privated = True
            skip = True
        if not skip:
            for id_existing, filepath in existing_videos.items():
                if not re_video_id_valid.match(id_existing):
                    if (
                        "title" in videos[video_id]
                        and videos[video_id]["title"].lower() in id_existing.lower()
                    ):
                        skipped_by_name.append(
                            {
                                "video_id": video_id,
                                "title": videos[video_id]["title"],
                                "filepath_existing": str(filepath),
                            }
                        )
                        skip = True
                        if video_id not in existing_videos:
                            existing_videos[video_id] = str(filepath)
                        else:
                            logging.warning(
                                f"Skipped two videos suspected to having the same title:\n{str(filepath)}\n{existing_videos[video_id]}\nid={video_id}\n"
                            )
                        existing_file = str(filepath)
                        break

        if privated or (skip and not update_metadata):
            continue

        video_download_url = url_base + f"videos/{video_id}"
        try:
            for i in range(timeout_tries):
                try:
                    print("\n...Getting... ", video_id, video_download_url)
                    driver.get(video_download_url)
                    # # take a screenshot of the page
                    # driver.save_screenshot(f"{video_id}.png")
                    try:
                        video_is_processing = driver.find_elements(
                            by=By.ID, value="video-processing"
                        )[0]
                        if (
                            video_is_processing
                            and video_is_processing.value_of_css_property("visibility")
                            != "hidden"
                        ):
                            print(
                                "FAIL: Processing video, please check back in a while\n"
                            )
                            continue
                    except IndexError:
                        pass
                    try:
                        download_button = driver.find_elements(
                            by=By.ID, value="download-button"
                        )[0]
                    except IndexError:
                        print("-- No download button found, likely privated video")
                        videos[video_id]["privated"] = True
                        continue
                    if "privated" in videos[video_id]:
                        del videos[video_id]["privated"]
                    download_button.click()

                    videos[video_id]["title"] = driver.find_elements(
                        by=By.CLASS_NAME, value="title"
                    )[0].text.strip()
                    if update_metadata or "username" not in videos[video_id]:
                        videos[video_id]["username"] = driver.find_elements(
                            by=By.CLASS_NAME, value="username"
                        )[0].text.strip()
                    try:
                        if update_metadata or "likes" not in videos[video_id]:
                            node_text = driver.find_elements(
                                by=By.CLASS_NAME, value="node-views"
                            )[0].text.strip()
                            videos[video_id]["likes"] = node_text.split()[0]
                        if update_metadata or "views" not in videos[video_id]:
                            node_text = driver.find_elements(
                                by=By.CLASS_NAME, value="node-views"
                            )[0].text.strip()
                            videos[video_id]["views"] = node_text.split()[1]
                    except Exception as e:
                        logging.exception(e)

                    WebDriverWait(driver, 7).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "#download-options a")
                        )
                    )
                    download_options = driver.find_elements(
                        by=By.ID, value="download-options"
                    )[0]
                    download_links = download_options.find_elements(
                        by=By.TAG_NAME, value="a"
                    )
                    download_source = download_links[0]
                    video_download_url = download_source.get_attribute("href")
                    video_ext = ".mp4"
                    ext_split = video_download_url.split("&")
                    for i in range(len(ext_split) - 1, -1, -1):
                        if "file=" in ext_split[i]:
                            video_ext = "." + ext_split[i].split(".")[-1]
                    #

                    class_name = "submitted"
                    submitted_str = driver.find_elements(
                        by=By.CLASS_NAME, value=class_name
                    )[0]
                    date_str = get_date_str(submitted_str.text)
                    if not date_str:
                        raise Exception(f"No date string found for video {video_id}")
                    date_str = re.sub(" ", "T", date_str)
                    date_str = re.sub(":", "-", date_str)
                    videos[video_id]["date"] = date_str

                    if like_videos_downloaded:
                        try:
                            node_buttons = driver.find_elements(
                                by=By.CLASS_NAME, value="node-buttons"
                            )[0]
                            buttons = node_buttons.find_elements(
                                by=By.TAG_NAME, value="a"
                            )
                            like_button = None
                            for b in buttons:
                                if "Like".lower() in b.text.lower():
                                    like_button = b
                            if like_button:
                                not_liked = (
                                    "Like".lower() in like_button.text.lower()
                                    and "Unlike".lower() not in like_button.text.lower()
                                )
                                videos[video_id]["liked"] = not not_liked
                                if not_liked:
                                    like_button.click()
                                    WebDriverWait(driver, 3).until(
                                        EC.visibility_of_element_located(
                                            (By.ID, "_nonexistantID_")
                                        )
                                    )
                                    liked_videos.append(video_id)
                        except TimeoutException as e:
                            pass
                        except Exception as e:
                            logging.exception(e)

                    if skip and not overwrite_small_files:
                        break
                    # Download
                    Path(download_dir).mkdir(parents=True, exist_ok=True)
                    chunk_size = 1024 * 1024  # 1 MB
                    response = requests.get(
                        video_download_url,
                        headers=headers,
                        cookies=cookies,
                        stream=True,
                    )
                    content_length_str = response.headers.get("content-length")
                    filename = (
                        filename_download.format(
                            username=videos[video_id]["username"],
                            title=videos[video_id]["title"],
                            date_str=videos[video_id]["date"],
                            video_id=video_id,
                        )
                        + video_ext
                    )
                    # filename = f"{videos[video_id]['username']} - {videos[video_id]['title']} {date_str} {video_id}.mp4"
                    filename = re_filename_invalid_chars.sub(" ", filename)
                    filepath = str(Path(download_dir) / filename)
                    totalMB = None
                    if content_length_str:
                        totalMB = math.ceil(int(content_length_str) / chunk_size)
                    # check if enough disk space is available
                    _, _, diskFree = shutil.disk_usage(download_dir)
                    diskFreeMB = diskFree // (2**20)
                    if isinstance(totalMB, int) and diskFreeMB < totalMB:
                        raise OSError("[Errno 28] No space left on device")

                    existingMB = None
                    if existing_file:
                        existingMB = math.ceil(
                            os.path.getsize(existing_file) / (2**20)
                        )
                    existing_file_is_incomplete = (
                        existingMB and totalMB and (existingMB < totalMB)
                    )
                    if not existingMB or (
                        overwrite_small_files and existing_file_is_incomplete
                    ):
                        if existing_file_is_incomplete and existing_file:
                            print(f"Redownloading file {existing_file}")
                            print(f"It has only {existingMB}MB out of {totalMB}MB")
                            filepath = Path(existing_file).parent / Path(filepath).name
                            redownloads[video_id] = [str(existing_file), str(filepath)]
                        print(filepath)
                        print("")
                        try:
                            with open(filepath, "wb") as handle:
                                for data in tqdm(
                                    response.iter_content(chunk_size),
                                    total=totalMB,
                                    **tqdm_args,
                                ):
                                    handle.write(data)
                        except Exception as e:
                            if filepath and os.path.exists(filepath):
                                os.remove(filepath)
                            raise
                        if existing_file and existing_file != filepath:
                            os.remove(existing_file)
                        downloaded_videos[video_id] = videos[video_id]
                    break
                except TimeoutException as e:
                    print("Timeout")
                    if i == timeout_tries - 1:
                        print("------ Failed to download it, too many timeouts")
                        errors.append(
                            {
                                "error": "Timeout " + str(e),
                                "video_id": video_id,
                                "traceback": traceback.format_exc(),
                            }
                        )
                    else:
                        print("trying again...")
                        time.sleep(timeout_sleep)
                    continue
        except KeyboardInterrupt as e:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            raise
        except Exception as e:
            logging.exception(e)
            errors.append(
                {
                    "error": str(e),
                    "video_id": video_id,
                    "traceback": traceback.format_exc(),
                }
            )
            continue

except KeyboardInterrupt as e:
    print("Stopped by keyboard interrupt")
except Exception as e:
    print("Caught exception")
    logging.exception(e)


def saveNoInterrupt():
    save_file_json(videos_filepath, videos)
    save_file_json("redownloads.json", redownloads)
    save_file_json("liked_videos.json", liked_videos)
    save_file_json(
        "skipped.json", {"skipped_by_name": skipped_by_name, "skipped": skipped}
    )
    save_file_json("errors.json", errors)
    save_file_json("downloaded_videos.json", downloaded_videos)


a = Thread(target=saveNoInterrupt)
a.start()
a.join()
# %%

print("Done")
# %%

try:
    driver.quit()
except Exception as e:
    pass
