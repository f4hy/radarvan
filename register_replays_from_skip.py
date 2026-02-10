import pathlib
import httpx

url = "http://localhost:8000/api/register_replay_url"
url = "https://www.radarvan.com/api/register_replay_url"
base = "https://generals-public.s3.us-east-2.amazonaws.com/reps/replays_from_skip/"

list_file = pathlib.Path("./replays_from_skip.txt")

parsed = 0

with list_file.open() as f:
    for line in f:
        if parsed > 5000:
            break
        print(line)
        if line.count("HardAI") > 1:
            continue
        if "2v2" in line or "3v3" in line or "4v4" in line:
            path = f"{base}{line}"
            resp = httpx.post(url, params={"url_of_replay": path}, timeout=300)
            if resp.json():
                print(resp.json()["id"])
            parsed += 1
