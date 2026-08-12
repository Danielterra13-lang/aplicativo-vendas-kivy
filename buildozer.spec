[app]

# (str) Title of your application
title = Aplicativo de Vendas

# (str) Package name
package.name = aplicativovendas

# (str) Package domain (needed for android/ios packaging)
package.domain = com.danielterra

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (leave empty to include all the files)
source.include_exts = py,png,kv

# (list) List of directory to exclude (leave empty to not exclude anything)
source.exclude_dirs = venv, venv_novo, .git, .idea, __pycache__, .kivy

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,requests,certifi,urllib3,idna,chardet

# (str) Presplash of the application
presplash.filename = %(source.dir)s/icones/bg_gradiente.png

# (str) Icon of the application
icon.filename = %(source.dir)s/icones/meu_avatar.png

# (list) Supported orientations
# Valid options are: landscape, portrait, portrait-reverse, landscape-reverse, or all
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
# INTERNET é necessária -- o app fala com o Firebase (login e banco) via HTTPS.
android.permissions = android.permission.INTERNET

# (bool) Aceita automaticamente a licença do Android SDK. Sem isso o build
# trava/falha no CI (GitHub Actions), porque não tem ninguém pra clicar
# "aceito" na hora que o buildozer baixa o SDK pela primeira vez.
android.accept_sdk_license = True

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# Só arm64-v8a por enquanto -- reduz o tempo de build. Dá pra adicionar
# armeabi-v7a (aparelhos mais antigos, 32-bit) depois que o build básico
# estiver passando.
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
