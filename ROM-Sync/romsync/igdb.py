"""A small IGDB client: Twitch OAuth, throttled queries, image download.

Credentials (Twitch Client ID and Secret) live in the app config; the first run
copies them across from ROM Curator 1 if they are not set yet.
"""
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import db

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API = "https://api.igdb.com/v4"
IMG = "https://images.igdb.com/igdb/image/upload"
RATE = 4.0
OLD_DB = r"D:\Games\RomCurator\romcurator\data\library.db"


class IgdbError(Exception):
    pass


def credentials():
    cfg = db.get_config()
    if cfg.get("client_id") and cfg.get("client_secret"):
        return cfg["client_id"], cfg["client_secret"]
    if os.path.isfile(OLD_DB):
        c = sqlite3.connect(OLD_DB)
        row = c.execute("SELECT value FROM meta WHERE key='config'").fetchone()
        c.close()
        if row:
            old = json.loads(row[0])
            if old.get("client_id") and old.get("client_secret"):
                db.save_config({"client_id": old["client_id"], "client_secret": old["client_secret"]})
                return old["client_id"], old["client_secret"]
    raise IgdbError("No IGDB credentials in the config (client_id / client_secret).")


class Client:
    def __init__(self, client_id=None, client_secret=None):
        if not client_id:
            client_id, client_secret = credentials()
        self.client_id, self.client_secret = client_id, client_secret
        self._token, self._expiry = None, 0
        self._lock = threading.Lock()
        self._last = 0.0

    def _throttle(self):
        with self._lock:
            wait = self._last + 1.0 / RATE - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def token(self):
        if self._token and time.time() < self._expiry - 120:
            return self._token
        body = urllib.parse.urlencode({"client_id": self.client_id, "client_secret": self.client_secret,
                                       "grant_type": "client_credentials"}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body, method="POST"), timeout=30) as r:
                payload = json.load(r)
        except urllib.error.HTTPError as e:
            raise IgdbError(f"Twitch rejected the credentials (HTTP {e.code}).") from e
        except urllib.error.URLError as e:
            raise IgdbError(f"Could not reach Twitch: {e.reason}") from e
        self._token = payload["access_token"]
        self._expiry = time.time() + int(payload.get("expires_in", 3600))
        return self._token

    def query(self, endpoint, body):
        self._throttle()
        req = urllib.request.Request(f"{API}/{endpoint}", data=body.encode("utf-8"), method="POST",
                                     headers={"Client-ID": self.client_id, "Authorization": f"Bearer {self.token()}",
                                              "Accept": "application/json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=45) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if e.code in (401, 403) and attempt == 0:
                    self._token = None
                    continue
                raise IgdbError(f"IGDB returned HTTP {e.code} for {endpoint}: {e.read()[:300]!r}") from e
            except urllib.error.URLError as e:
                if attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise IgdbError(f"Could not reach IGDB: {e.reason}") from e
        raise IgdbError("IGDB kept rate limiting the request")


def image_url(image_id, size):
    return f"{IMG}/{size}/{image_id}.jpg"


def fetch_image(image_id, size, dest):
    """Download one IGDB image to dest (atomic). Returns dest or None."""
    if os.path.isfile(dest):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(image_url(image_id, size), timeout=30) as r, open(tmp, "wb") as f:
            f.write(r.read())
        os.replace(tmp, dest)
        return dest
    except (urllib.error.URLError, OSError):
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None
