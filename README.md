Logitech G HUB (LGHUB) Profile Editor
---
A simple app that lets you edit profile names, profile icons and add/remove profiles in Logitech G HUB. Written in python. Inspired by [this](https://www.reddit.com/r/LogitechG/comments/jwiddw/g_hub_renaming_profiles/k8t1s6c/
) reddit comment.

You can run it directly (without having to bother with python) by simply downloading the `.exe` from the [releases](https://github.com/homelab-00/LGHUB-Profile-Editor/releases/tag/V3) page.
Make sure to exit LGHUB while editing the profiles with this app and to exit this app when you start LGHUB afterwards.

The app auto-detects the `.db` file where LGHUB stores all the profile data. It's hardcoded to look into `C:\Users\%username%\AppData\Local\LGHUB`. If your `.db` file is located elsewhere you can manually edit the script. The icons folder (`icon_cache`) is located in that same folder as well.

Tested in LGHUB `2024.9.649333` on Windows 10 22H2.

---

### Preview

![screenshot](https://github.com/homelab-00/LGHUB-Profile-Editor/blob/main/screenshots/screenshot_1.png?raw=true)
