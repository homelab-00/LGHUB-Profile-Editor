A simple app that lets you edit profile names and profile icons in Logitech G HUB. Written in python. Inspired by [this](https://www.reddit.com/r/LogitechG/comments/jwiddw/g_hub_renaming_profiles/k8t1s6c/
) reddit comment.

You can run it directly (without having to bother with python) by simply downloading the `.exe` from releases.
Make sure to exit LGHUB while editing the profiles with this app and to exit this app when you start LGHUB afterwards.

The app auto-detects the `.db` file where LGHUB stores all the profile data. It's hardcoded to look into `C:\Users\%username%\AppData\Local\LGHUB`. If your `.db` file is located elsewhere you can manually edit the script. The icons folder (`icon_cache`) is located in that same folder as well.

Tested in LGHUB `2024.9.649333`

![screenshot](https://github.com/homelab-00/LGHUB-Profile-Editor/blob/main/screenshots/screenshot_1.png?raw=true)