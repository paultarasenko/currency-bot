import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set! Add it to environment variables.")

# Каталог для файла с пользовательскими данными (избранное, история, выбранная пара).
# На хостингах с эфемерной файловой системой (Railway) примонтируйте сюда Volume.
DATA_DIR = os.getenv("DATA_DIR", "data")
