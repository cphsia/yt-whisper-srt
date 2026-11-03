# -*- coding: utf-8 -*-
"""
YouTube / 本機影片 → Whisper 語音辨識 → 繁體中文 .srt 字幕檔

安裝（只需一次）：
    pip install faster-whisper yt-dlp opencc-python-reimplemented

用法：
    python yt_whisper_srt.py "https://www.youtube.com/watch?v=xxxx"
    python yt_whisper_srt.py 網址1 網址2 本機影片.mp4
    python yt_whisper_srt.py 播放清單網址 --model large-v3
    python yt_whisper_srt.py 影片.mp4 --lang en          # 英文影片
    python yt_whisper_srt.py 網址 --translate            # 外語直接翻成英文字幕
選項：
    --model   tiny / base / small / medium / large-v3（預設：有 NVIDIA 顯卡用 large-v3，否則 medium）
    --lang    語言代碼，預設 zh；填 auto 自動偵測
    --out     輸出資料夾，預設目前資料夾下的 subtitles
    --keep-audio  保留下載的音訊檔
    --txt     另外輸出純文字 .txt
"""
import argparse
import os
import re

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
import sys
from pathlib import Path

ZH_PROMPT = "以下是繁體中文的句子，包含標點符號。"


def is_url(s: str) -> bool:
    return s.lower().startswith(("http://", "https://", "www.", "youtu"))


def download_audio(url: str, outdir: Path) -> list[Path]:
    """只下載音訊（不需 ffmpeg 轉檔），支援單支影片與播放清單。"""
    import yt_dlp

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(outdir / "%(title)s [%(id)s].%(ext)s"),
        "windowsfilenames": True,
        "ignoreerrors": True,
    }
    files = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            return files
        for entry in info.get("entries") or [info]:
            if entry:
                p = Path(ydl.prepare_filename(entry))
                if p.exists():
                    files.append(p)
    return files


def patch_av():
    """PyAV 15+ 移除了 metadata_errors 參數，faster-whisper 舊版仍會傳入，這裡把它濾掉。"""
    try:
        import av
    except ImportError:
        return
    if getattr(av.open, "_patched", False):
        return
    orig_open = av.open

    def safe_open(*args, **kwargs):
        try:
            return orig_open(*args, **kwargs)
        except TypeError as e:
            if "metadata_errors" in str(e):
                kwargs.pop("metadata_errors", None)
                return orig_open(*args, **kwargs)
            raise

    safe_open._patched = True
    av.open = safe_open


def pick_device(model_arg: str | None):
    try:
        import ctranslate2
        has_cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        has_cuda = False
    if has_cuda:
        return "cuda", "float16", model_arg or "large-v3"
    return "cpu", "int8", model_arg or "medium"


def fmt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe(model, media: Path, out_srt: Path, lang, translate, converter, want_txt):
    kwargs = dict(vad_filter=True, beam_size=5)
    if lang:
        kwargs["language"] = lang
        if lang == "zh":
            kwargs["initial_prompt"] = ZH_PROMPT
    if translate:
        kwargs["task"] = "translate"

    segments, info = model.transcribe(str(media), **kwargs)
    total = info.duration or 0
    print(f"  偵測語言：{info.language}（{info.language_probability:.0%}），長度 {fmt_time(total)}")

    lines, texts = [], []
    for i, seg in enumerate(segments, 1):
        text = seg.text.strip()
        if converter:
            text = converter.convert(text)
        lines.append(f"{i}\n{fmt_time(seg.start)} --> {fmt_time(seg.end)}\n{text}\n")
        texts.append(text)
        if total:
            print(f"\r  進度 {seg.end / total:6.1%}", end="", flush=True)
    print()

    out_srt.write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"  ✔ 字幕：{out_srt}")
    if want_txt:
        out_txt = out_srt.with_suffix(".txt")
        out_txt.write_text("\n".join(texts), encoding="utf-8-sig")
        print(f"  ✔ 文字：{out_txt}")


def main():
    ap = argparse.ArgumentParser(description="影片 → Whisper → .srt 字幕")
    ap.add_argument("inputs", nargs="+", help="YouTube 網址或本機影片/音訊檔")
    ap.add_argument("--model", default=None)
    ap.add_argument("--lang", default="zh", help="zh / en / ja ... 或 auto")
    ap.add_argument("--out", default="subtitles")
    ap.add_argument("--translate", action="store_true", help="翻譯成英文字幕")
    ap.add_argument("--keep-audio", action="store_true")
    ap.add_argument("--txt", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    lang = None if args.lang.lower() == "auto" else args.lang.lower()

    converter = None
    if lang in (None, "zh") and not args.translate:
        try:
            import opencc
            converter = opencc.OpenCC("s2twp")  # 簡→繁（台灣用語）
        except ImportError:
            print("提示：未安裝 opencc-python-reimplemented，將不做簡轉繁。")

    from faster_whisper import WhisperModel
    patch_av()
    device, ctype, model_name = pick_device(args.model)
    print(f"載入模型 {model_name}（{device}）… 第一次使用會自動下載模型，請稍候")
    model = WhisperModel(model_name, device=device, compute_type=ctype)

    for item in args.inputs:
        downloaded = []
        if is_url(item):
            print(f"\n下載音訊：{item}")
            downloaded = download_audio(item, outdir)
            medias = downloaded
            if not medias:
                print("  ✘ 下載失敗，略過")
                continue
        else:
            p = Path(item)
            if not p.exists():
                print(f"\n✘ 找不到檔案：{item}")
                continue
            medias = [p]

        for media in medias:
            print(f"\n辨識中：{media.name}")
            stem = re.sub(r'[<>:"/\\|?*]', "_", media.stem)
            out_srt = outdir / f"{stem}.srt"
            try:
                transcribe(model, media, out_srt, lang, args.translate, converter, args.txt)
            except Exception as e:
                print(f"  ✘ 失敗：{e}")
            finally:
                if media in downloaded and not args.keep_audio:
                    media.unlink(missing_ok=True)

    print("\n全部完成。")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
