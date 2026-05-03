[app]
title = PC Controller
package.name = pccremote
package.domain = com.user

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = .git,__pycache__,venv,.venv,build,bin

version = 0.1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

android.permissions = INTERNET

android.allow_backup = True
android.accept_sdk_license = True

presplash.filename =
icon.filename =

log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
