import websockets.sync.client as websockets
import json
import tls_client
import time
from twocaptcha import TwoCaptcha


class Kick:
    def __init__(self, proxy: str = None):
        self.__session = tls_client.Session(
            client_identifier="okhttp4_android_9",
            random_tls_extension_order=True
        )
        if proxy:
            self.__session.proxies.update({
                "https": f"http://{proxy}",
                "http": f"http://{proxy}",
            })
        self.__session.headers.update({
            "User-Agent": "okhttp/4.9.2",
        })
        self.__token_provider = None
        self.token = None

    def __refresh_token_provider(self):
        r = self.__session.get("https://kick.com/kick-token-provider")
        self.__token_provider = r.json()
    
    def __get_auth(self, socket_id: str, channel: str):
        r = self.__session.post(
                "https://kick.com/broadcasting/auth",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data=f"socket_id={socket_id}&channel_name={channel}"
            )
        return r.json()["auth"]

    def signup(self, email: str, username: str, password: str):
        self.__refresh_token_provider()
        r = self.__session.post(
            "https://kick.com/api/v1/signup/send/email",
            json={
                "email": email
            }
        )
        if r.status_code != 204:
            raise Exception("Failed to send email")
        r = self.__session.post(
            "https://kick.com/api/v1/signup/verify/code",
            json={
                "email": email,
                "code": input("Enter verification code: ").strip()
            }
        )
        if r.status_code != 204:
            raise Exception("Failed to verify code")
        solver = TwoCaptcha("86127f8b73586582e7886fe0bc92a20b", pollingInterval=5)
        captcha_token = solver.turnstile("0x4AAAAAAAEJ7fHQIF0h3YUC", "https://kick.com")["code"]
        r = self.__session.post(
            "https://kick.com/register",
            json={
                "email": email,
                "username": username,
                "password": password,
                "password_confirmation": password,
                "birthdate": "2000-01-01T01:50:40.880Z",
                "cf_captcha_token": captcha_token,
                "agreed_to_terms": True,
                "isMobileRequest": True,
                self.__token_provider["nameFieldName"]: "",
                self.__token_provider["validFromFieldName"]: self.__token_provider["encryptedValidFrom"],
            }
        )
        if r.status_code != 200:
            raise Exception("Failed to register")
        self.token = f"Bearer {r.json()['token']}"

    def login(self, username: str = None, password: str = None, token: str = None):
        self.__refresh_token_provider()
        if username and password:
            r = self.__session.post(
                "https://kick.com/mobile/login",
                json={
                    "email": username,
                    "password": password,
                    "isMobileRequest": True,
                    self.__token_provider["nameFieldName"]: "",
                    self.__token_provider["validFromFieldName"]: self.__token_provider["encryptedValidFrom"],
                }
            )
            if r.status_code == 302:
                raise Exception("Invalid credentials")
            self.token = f"Bearer {r.json()['token']}"
            self.__session.headers["Authorization"] = self.token
        elif token:
            self.__session.headers["Authorization"] = token

    def get_channel(self, username: str):
        r = self.__session.get(f"https://kick.com/api/v2/channels/{username}")
        if r.status_code == 404:
            raise Exception("Channel not found")
        return r.json()

    def follow_channel(self, username: str):
        r = self.__session.post(f"https://kick.com/api/v2/channels/{username}/follow")
        if r.status_code == 404:
            raise Exception("Channel not found")
        elif r.status_code == 302:
            raise Exception("Channel already followed")
        elif not self.__session.get(f"https://kick.com/api/v2/channels/{username}/me").json()["is_following"]:
            raise Exception("Failed to follow channel")
        return r.json()

    def watch_channel(self, username: str, sleep: int = 10):
        with websockets.connect("wss://ws-us2.pusher.com/app/eb1d5f283081a78b932c?protocol=7&client=js&version=7.6.0&flash=false") as ws:
            channel = f"private-livestream.{self.get_channel(username)['livestream']['id']}"
            socket_id = json.loads(json.loads(ws.recv())["data"])["socket_id"]
            ws.send(json.dumps({"event": "pusher:subscribe", "data": {"auth": self.__get_auth(socket_id, channel), "channel": channel}}))
            for _ in range(sleep):
                time.sleep(1)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass