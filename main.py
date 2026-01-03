import os
import time
import subprocess
import whisper
import torch

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ---------- DIRECTORIES ----------
BASE_DIR = os.getcwd()
DOWNLOADS = os.path.join(BASE_DIR, "downloads")
CLIPS = os.path.join(BASE_DIR, "clips")
SUBS = os.path.join(BASE_DIR, "subtitles")
OUTPUT = os.path.join(BASE_DIR, "output")

for d in [DOWNLOADS, CLIPS, SUBS, OUTPUT]:
    os.makedirs(d, exist_ok=True)

VIDEO_PATH = None
CLIP_PATH = None
FINAL_PATH = None
SRT_PATH = None

# ---------- UTILS ----------
def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return str(int(time.time()))

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")

# ---------- DOWNLOAD (FORCE MP4) ----------
def download_video(url):
    print("⬇️ Downloading video (forced MP4)...")
    run(
        f'yt-dlp '
        f'-f "bv*[vcodec=h264]+ba[acodec=aac]/mp4" '
        f'--merge-output-format mp4 '
        f'-o "{VIDEO_PATH}" '
        f'--no-overwrites "{url}"'
    )

# ---------- CUT CLIP (4K VERTICAL) ----------
def cut_clip(start=60, duration=45):
    print("✂️ Cutting TRUE 4K vertical clip (bulletproof)...")
    run(
        f'ffmpeg -y -ss {start} -i "{VIDEO_PATH}" -t {duration} '
        f'-vf "scale=-1:3840,crop=2160:3840:(iw-2160)/2:0" '
        f'-c:v libx264 -preset slow -crf 16 '
        f'-pix_fmt yuv420p -profile:v high '
        f'-c:a copy "{CLIP_PATH}"'
    )



# ---------- SUBTITLES ----------
def generate_subtitles():
    print("📝 Generating subtitles...")
    model = whisper.load_model("base")
    result = model.transcribe(CLIP_PATH)

    with open(SRT_PATH, "w") as f:
        for i, seg in enumerate(result["segments"], start=1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(seg["text"].strip() + "\n\n")

# ---------- BURN SUBTITLES ----------
def burn_subtitles():
    print("🔥 Burning subtitles...")
    run(
        f'ffmpeg -y -i "{CLIP_PATH}" '
        f'-vf "subtitles={SRT_PATH}" '
        f'-c:v libx264 -preset slow -crf 16 '
        f'-pix_fmt yuv420p -profile:v high '
        f'-c:a copy "{FINAL_PATH}"'
    )

# ---------- METADATA (FRESH EVERY TIME) ----------
def generate_metadata():
    print("✍️ Generating fresh title & description...")

    text = ""
    with open(SRT_PATH, "r") as f:
        for line in f:
            if "-->" not in line and not line.strip().isdigit():
                text += line.strip() + " "

    hooks = [
        "Nobody tells you this about life",
        "Most people learn this too late",
        "This advice changed my mindset",
        "You need to hear this today",
        "This hit harder than expected"
    ]

    title = hooks[int(time.time()) % len(hooks)][:60]

    description = (
        f"{text[:140]}...\n"
        "Watch till the end.\n"
        "#Shorts #Mindset #LifeAdvice"
    )

    return title, description

# ---------- UPLOAD ----------
def upload_to_youtube(title, description):
    print("🚀 Uploading 4K YouTube Short...")

    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", scopes
    )
    creds = flow.run_local_server(port=0)

    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public"
            }
        },
        media_body=MediaFileUpload(
            FINAL_PATH,
            chunksize=-1,
            resumable=True
        )
    )

    request.execute()
    print("✅ 4K SHORT UPLOADED SUCCESSFULLY")

# ---------- MAIN ----------
def main():
    global VIDEO_PATH, CLIP_PATH, FINAL_PATH, SRT_PATH

    url = input("Paste YouTube video URL: ").strip()
    video_id = get_video_id(url)

    print(f"📌 Processing NEW video: {video_id}")

    VIDEO_PATH = os.path.join(DOWNLOADS, f"{video_id}.mp4")
    CLIP_PATH = os.path.join(CLIPS, f"{video_id}_4k_clip.mp4")
    FINAL_PATH = os.path.join(OUTPUT, f"{video_id}_4k_final.mp4")
    SRT_PATH = os.path.join(SUBS, f"{video_id}.srt")

    download_video(url)
    cut_clip()
    generate_subtitles()
    burn_subtitles()

    title, description = generate_metadata()
    print("\nTITLE:", title)
    print("DESCRIPTION:\n", description)

    upload_to_youtube(title, description)

if __name__ == "__main__":
    main()
