import os
import aiohttp
import time
import tempfile
from config import MAX_SINGLE_FILE_MB, SPLIT_SIZE_MB, BOT_TOKEN
from utils import format_size, format_time, get_progress_bar, get_status

MAX_SINGLE = MAX_SINGLE_FILE_MB * 1024 * 1024
SPLIT_SIZE = SPLIT_SIZE_MB * 1024 * 1024

async def update_progress(msg, phase, downloaded, total, start_time, extra=""):
    percent = (downloaded / total * 100) if total > 0 else 0
    elapsed = time.time() - start_time
    speed = downloaded / elapsed if elapsed > 0 else 0
    eta = (total - downloaded) / speed if speed > 0 else 0

    bar = get_progress_bar(percent)
    size_str = f"{format_size(downloaded)} / {format_size(total)}"
    speed_str = format_size(speed) + "/s"
    eta_str = format_time(eta) if eta > 0 else "calculating..."
    status = get_status(speed) if speed > 0 else "⏳ Starting..."

    icon = "📥" if phase == "download" else "📤"
    title = "Downloading..." if phase == "download" else "Uploading..."

    text = (
        f"╭──────────────╮\n"
        f"│ {icon} {title}\n"
        f"├───────────────\n"
        f"│ {bar} {percent:.1f}%\n"
        f"│ 📦 Size: {size_str}\n"
        f"│ ⚡ Speed: {speed_str}\n"
        f"│ ⏱️ ETA: {eta_str}\n"
        f"│ 🔗 Status: {status}\n"
        f"│ {extra}\n"
        f"╰──────────────╯"
    )
    await msg.edit_text(text)

async def download_file(url, progress_msg, total_size):
    fd, temp_path = tempfile.mkstemp(suffix=".download")
    os.close(fd)

    start_time = time.time()
    downloaded = 0

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get('content-length', total_size))
            with open(temp_path, 'wb') as f:
                async for chunk in resp.content.iter_chunked(8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded % max(1, total // 50) == 0 or downloaded == total:
                            await update_progress(progress_msg, "download", downloaded, total, start_time)
    return temp_path, total

async def upload_single_file(chat_id, file_path, filename, caption, thumbnail):
    with open(file_path, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field('chat_id', str(chat_id))
        data.add_field('document', f, filename=filename)
        if caption:
            data.add_field('caption', caption)
        if thumbnail:
            data.add_field('thumbnail', thumbnail)
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            async with session.post(url, data=data) as resp:
                resp.raise_for_status()
                result = await resp.json()
                if not result.get('ok'):
                    raise Exception(result.get('description'))

async def upload_parts(chat_id, file_path, filename, caption, thumbnail, total_size, progress_msg):
    part_num = 0
    part_size = SPLIT_SIZE
    uploaded_total = 0
    start_time = time.time()

    with open(file_path, 'rb') as f:
        while True:
            part_data = f.read(part_size)
            if not part_data:
                break
            part_num += 1
            part_filename = f"{filename}.part{part_num:03d}"
            part_caption = f"{caption}\n\n─── Part {part_num} ───"
            await upload_part(chat_id, part_data, part_filename, part_caption, thumbnail)
            uploaded_total += len(part_data)
            await update_progress(progress_msg, "upload", uploaded_total, total_size, start_time,
                                  extra=f"Part {part_num}")
            del part_data

    await progress_msg.edit_text(
        f"✅ All {part_num} parts sent successfully!\n\n"
        f"Merge using:\n"
        f"`cat {filename}.part* > {filename}` (Linux/Mac)\n"
        f"or `copy /b {filename}.part* {filename}` (Windows)"
    )

async def upload_part(chat_id, data, filename, caption, thumbnail):
    form = aiohttp.FormData()
    form.add_field('chat_id', str(chat_id))
    form.add_field('document', data, filename=filename)
    if caption:
        form.add_field('caption', caption)
    if thumbnail:
        form.add_field('thumbnail', thumbnail)

    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        async with session.post(url, data=form) as resp:
            resp.raise_for_status()
            result = await resp.json()
            if not result.get('ok'):
                raise Exception(result.get('description'))

async def download_and_upload_stream(
    chat_id, download_url, filename, caption, progress_msg,
    thumbnail, total_size
):
    temp_path, actual_size = await download_file(download_url, progress_msg, total_size)

    try:
        if actual_size <= MAX_SINGLE:
            await upload_single_file(chat_id, temp_path, filename, caption, thumbnail)
            await progress_msg.edit_text("✅ File sent successfully!")
        else:
            await upload_parts(chat_id, temp_path, filename, caption, thumbnail, actual_size, progress_msg)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    return True
