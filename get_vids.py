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
# Bypassing Error 403
# User-Agent


def bypassOpen(url):
    response = requests.get(url, headers=headers, cookies=cookies)
    return response


def bypassRead(address):
    response = bypassOpen(address)
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

page_num = 0
videos_new = {}

try:
    while True:
        video_download_url = (
            "https://ecchi.iwara.tv/user/liked?page="
            + urllib.parse.quote(str(page_num))
        )
        print("Getting... ", video_download_url)
        soup = bypassRead(video_download_url)
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
                        "thumbnail": item.find("img").get("src"),
                        "likes": item.find("div", class_="right-icon").text.strip(),
                        "views": item.find("div", class_="left-icon").text.strip(),
                    }

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


# videos = open_data_file(videos_filepath) or {}

print(f"Found existing {len(videos.keys())} in {filepath} {videos_filepath}")

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
        video_id = fname.split(" ")[-1].lower()
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

downloaded_videos = {}

filename_invalid_chars = re.compile(r"[\s\?\\/:*?？\"<>\|]+")

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
        if video_id in existing_videos:
            skipped.append(video_id)
            skip = True
        if "privated" in videos[video_id] and videos[video_id]["privated"]:
            skip = True
        if not skip:
            for id_existing, filename in existing_videos.items():
                if not re_video_id_valid.match(id_existing):
                    if (
                        "title" in videos[video_id]
                        and videos[video_id]["title"].lower() in id_existing.lower()
                    ):
                        skipped_by_name.append(
                            {
                                "video_id": video_id,
                                "title": videos[video_id]["title"],
                                "filename_existing": filename,
                            }
                        )
                        skip = True
                        break
        if skip:
            if not update_metadata:
                continue

        video_download_url = url_base + f"videos/{video_id}"
        try:
            for i in range(timeout_tries):
                try:
                    print("Getting... ", video_id, video_download_url)
                    driver.get(video_download_url)
                    # # take a screenshot of the page
                    # driver.save_screenshot(f"{video_id}.png")
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
                            videos[video_id]["likes"] = node_text.split(" ")[0]
                        if update_metadata or "views" not in videos[video_id]:
                            node_text = driver.find_elements(
                                by=By.CLASS_NAME, value="node-views"
                            )[0].text.strip()
                            videos[video_id]["views"] = node_text.split(" ")[1]
                    except Exception as e:
                        logging.exception(e)

                    print(videos[video_id])

                    WebDriverWait(driver, 2).until(
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
                    date_str = submitted_str.text.split("on ")[1].strip()
                    date_str = re.sub(" ", "T", date_str)
                    date_str = re.sub(":", "-", date_str)
                    videos[video_id]["date"] = date_str

                    if skip:
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
                            date_str=date_str,
                            video_id=video_id,
                        )
                        + video_ext
                    )
                    # filename = f"{videos[video_id]['username']} - {videos[video_id]['title']} {date_str} {video_id}.mp4"
                    filename = filename_invalid_chars.sub(" ", filename)
                    filepath = str(Path(download_dir) / filename)
                    print(filepath)
                    print("")
                    with open(filepath, "wb") as handle:
                        total = None
                        if content_length_str:
                            total = math.ceil(int(content_length_str) / chunk_size)
                        for data in tqdm(
                            response.iter_content(chunk_size), total=total, **tqdm_args
                        ):
                            handle.write(data)
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
            if filepath:
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
driver.close()


def saveNoInterrupt():
    save_file_json(videos_filepath, videos)
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
