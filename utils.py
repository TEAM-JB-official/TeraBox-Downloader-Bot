import time
import aiohttp
from config import API_URL

def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"

def format_time(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds//60)}m {int(seconds%60)}s"
    else:
        return f"{int(seconds//3600)}h {int((seconds%3600)//60)}m"

def get_progress_bar(percent, width=20):
    filled = int(width * percent / 100)
    return '█' * filled + '░' * (width - filled)

def get_status(speed):
    if speed > 5 * 1024 * 1024:
        return "👍 Excellent"
    elif speed > 1 * 1024 * 1024:
        return "👍 Good"
    elif speed > 200 * 1024:
        return "🙂 Average"
    else:
        return "🐢 Slow"

def apply_rename_and_replace(filename, rename_tag, replace_rules):
    if rename_tag:
        filename = rename_tag.replace("{filename}", filename)
    for old, new in replace_rules.items():
        filename = filename.replace(old, new)
    return filename

def get_file_type(filename):
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    video = ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', '3gp']
    audio = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']
    image = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
    if ext in video:
        return "video"
    elif ext in audio:
        return "audio"
    elif ext in image:
        return "image"
    else:
        return "document"

async def fetch_terabox_data(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}{url}", timeout=30) as resp:
                data = await resp.json()
                return data if data.get("success") else None
    except Exception:
        return None
