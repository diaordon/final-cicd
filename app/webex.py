import os, requests
ROOM  = os.getenv("WEBEX_ROOM_ID")
TOKEN = os.getenv("WEBEX_TOKEN")

def notify(text: str):
    if not (ROOM and TOKEN):
        return
    r = requests.post(
        "https://webexapis.com/v1/messages",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"roomId": ROOM, "markdown": text},
        timeout=15
    )
    r.raise_for_status()

