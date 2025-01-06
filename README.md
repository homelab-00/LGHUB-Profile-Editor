# Logitech G HUB (LGHUB) Profile Editor

A simple app that lets you edit profile names, profile icons and add/remove profiles in Logitech G HUB. Written in python. Inspired by [this](https://www.reddit.com/r/LogitechG/comments/jwiddw/g_hub_renaming_profiles/k8t1s6c/
) reddit comment.

You can run it directly (without having to bother with python) by simply downloading the `.exe` from the [releases](https://github.com/homelab-00/LGHUB-Profile-Editor/releases/tag/V3) page.

You can change a profile's name and its associated profile path by editing the fields directly. Clearing the icon is self explanatory. When you change icon, the app will ask you to select an image from your computer. Image types `.bmp`, `.ico`, `.png`, `.jpg` and `.jpeg` are supported. Since LGHUB prefers `.bmp` files, we auto convert images to that format. The selected icon is then copied to the icon folder (named `icon_cache` and located in the same folder as `settings.db`) either ovewritting the one already there or creating a new one.

Don't forget to save your changes when you're done.

Note that the app doesn't check file size or dimensions, so make sure the image you use is sized appropriately beforehand.

Also make sure to exit LGHUB while editing profiles with this app and to exit this app when you start LGHUB afterwards.

> The app auto-detects the `settings.db` file where LGHUB stores all the profile data. It's hardcoded to look into `C:\Users\%username%\AppData\Local\LGHUB`. If your `settings.db` file is located elsewhere you can manually edit the script.

> Tested with LGHUB `2024.9.649333` on Windows 10 22H2.

---

### Preview

![screenshot](https://github.com/homelab-00/LGHUB-Profile-Editor/blob/main/screenshots/screenshot_1.png?raw=true)
