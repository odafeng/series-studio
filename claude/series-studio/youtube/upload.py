#!/usr/bin/env python3
"""Upload the tutorial video to YouTube via the YouTube Data API v3.

One-time setup (see README.md): create an OAuth client (Desktop app) in a GCP project
with the YouTube Data API enabled, download it as youtube/client_secret.json. The first
run opens a browser to authorise; the token is cached in youtube/token.json so later runs
are non-interactive.

  python3 youtube/upload.py                         # upload master, privacy from --privacy
  python3 youtube/upload.py --file ../path.mp4 --privacy unlisted
  python3 youtube/upload.py --auth-only             # just do the OAuth handshake, no upload

Metadata (title/description/tags/category/language) is read from youtube/metadata.json.
"""
import argparse
import json
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

HERE = Path(__file__).resolve().parent
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
CLIENT_SECRET = HERE / "client_secret.json"
TOKEN = HERE / "token.json"
METADATA = HERE / "metadata.json"
DEFAULT_FILE = HERE.parent / "remotion" / "out" / "world_master.mp4"


def get_credentials():
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                sys.exit(f"missing {CLIENT_SECRET} — see youtube/README.md to create the OAuth client")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.write_text(creds.to_json())
    return creds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_FILE))
    ap.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    ap.add_argument("--auth-only", action="store_true")
    ap.add_argument("--update", metavar="VIDEO_ID", help="update an existing video's title/description/tags from metadata.json")
    ap.add_argument("--thumb", metavar="VIDEO_ID", help="set a custom thumbnail on an existing video")
    ap.add_argument("--thumb-file", default=str(HERE.parent / "remotion" / "out" / "thumb_1.png"))
    ap.add_argument("--metadata", default=str(METADATA), help="path to metadata json (title/description/tags)")
    ap.add_argument("--playlist", metavar="VIDEO_ID", help="add a video to the playlist given by --playlist-id")
    ap.add_argument("--playlist-id", help="target playlist id for --playlist")
    ap.add_argument("--comment", metavar="VIDEO_ID", help="post a top-level comment on a video (text from --comment-text / --comment-file). Note: YouTube API cannot PIN — pin manually in Studio/app.")
    ap.add_argument("--comment-text", help="comment body (inline)")
    ap.add_argument("--comment-file", help="path to a file containing the comment body")
    args = ap.parse_args()
    meta_path = Path(args.metadata)

    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    ch = youtube.channels().list(part="snippet", mine=True).execute()
    channel = ch["items"][0]["snippet"]["title"] if ch.get("items") else "(no channel on this account)"
    print(f"authorised channel: 「{channel}」")

    if args.auth_only:
        print("OAuth OK — token saved to", TOKEN.name)
        return

    if args.thumb:
        try:
            youtube.thumbnails().set(videoId=args.thumb, media_body=MediaFileUpload(args.thumb_file)).execute()
        except HttpError as e:
            sys.exit(f"YouTube API error {e.resp.status}: {e.content.decode()[:400]}")
        print(f"✅ thumbnail set ({Path(args.thumb_file).name}) → https://youtu.be/{args.thumb}")
        return

    if args.playlist:
        if not args.playlist_id:
            sys.exit("provide --playlist-id")
        body = {"snippet": {"playlistId": args.playlist_id, "resourceId": {"kind": "youtube#video", "videoId": args.playlist}}}
        try:
            youtube.playlistItems().insert(part="snippet", body=body).execute()
        except HttpError as e:
            sys.exit(f"YouTube API error {e.resp.status}: {e.content.decode()[:400]}")
        print(f"✅ added https://youtu.be/{args.playlist} to playlist {args.playlist_id}")
        return

    if args.comment:
        text = args.comment_text
        if args.comment_file:
            text = Path(args.comment_file).read_text()
        if not text:
            sys.exit("provide --comment-text or --comment-file")
        body = {"snippet": {"videoId": args.comment, "topLevelComment": {"snippet": {"textOriginal": text}}}}
        try:
            r = youtube.commentThreads().insert(part="snippet", body=body).execute()
        except HttpError as e:
            sys.exit(f"YouTube API error {e.resp.status}: {e.content.decode()[:400]}")
        print(f"✅ comment posted (id {r['id']}) → https://youtu.be/{args.comment}")
        print("   ⚠️ API 無法置頂；到 Studio/App 點該留言 ⋮ →「置頂」")
        return

    if args.update:
        meta = json.loads(meta_path.read_text())
        body = {"id": args.update, "snippet": {
            "title": meta["title"], "description": meta["description"],
            "tags": meta.get("tags", []), "categoryId": meta.get("categoryId", "27"),
            "defaultLanguage": meta.get("defaultLanguage", "zh-Hant")}}
        try:
            youtube.videos().update(part="snippet", body=body).execute()
        except HttpError as e:
            sys.exit(f"YouTube API error {e.resp.status}: {e.content.decode()[:400]}")
        print(f"✅ metadata updated → https://youtu.be/{args.update}")
        return

    video = Path(args.file)
    if not video.exists():
        sys.exit(f"video not found: {video}")
    meta = json.loads(meta_path.read_text())

    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("categoryId", "27"),
            "defaultLanguage": meta.get("defaultLanguage", "zh-Hant"),
            "defaultAudioLanguage": meta.get("defaultAudioLanguage", "zh-Hant"),
        },
        "status": {"privacyStatus": args.privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    print(f"uploading {video.name} ({video.stat().st_size/1e6:.1f} MB) as {args.privacy}…")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    resp = None
    try:
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                print(f"  {int(status.progress()*100)}%")
    except HttpError as e:
        sys.exit(f"YouTube API error {e.resp.status}: {e.content.decode()[:400]}")

    vid = resp["id"]
    print("\n✅ done →", f"https://youtu.be/{vid}")
    print("   Studio:", f"https://studio.youtube.com/video/{vid}/edit")
    if args.privacy == "public":
        print("   (若 app 未驗證被鎖成私人，到上面 Studio 連結手動改公開)")


if __name__ == "__main__":
    main()
