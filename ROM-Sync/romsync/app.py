"""The desktop window: a WebView2 window over the local server.

    python -m romsync.app            open the app
    python -m romsync.app --browser  serve only and print the address (for a normal browser)
"""
import os
import sys
import time

from . import db, server


def main(argv):
    httpd, port = server.serve(8765 if "--browser" in argv else 0)
    url = f"http://127.0.0.1:{port}/"
    if "--browser" in argv:
        print(f"ROM-Sync at {url}")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return
    import webview
    # WebView2 keeps a browser profile (page cache, cookies) on disk. Point it at the app's own
    # data folder so nothing lands under the user profile on C: and deleting the app removes it.
    storage = os.path.join(db.data_dir(), "webview")
    os.makedirs(storage, exist_ok=True)
    webview.create_window("ROM-Sync", url, width=1440, height=900, min_size=(1000, 640))
    webview.start(private_mode=False, storage_path=storage)
    httpd.shutdown()


if __name__ == "__main__":
    main(sys.argv)
