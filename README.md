# yt-whisper-srt

把 YouTube 影片（或本機影片檔）用 OpenAI Whisper 語音辨識，自動產生 **繁體中文 `.srt` 字幕檔**。

- 貼網址即可，支援單支影片與整個播放清單
- 只下載音訊，辨識完自動刪除，不佔空間
- 簡體自動轉繁體（台灣用語）
- 有 NVIDIA 顯卡自動用 GPU 與最準的 `large-v3` 模型，沒有就用 CPU
- 不需要另外安裝 ffmpeg
- 也可辨識英文、日文等其他語言，或直接翻譯成英文字幕

## 安裝

需要 Python 3.10 以上。

```bash
pip install -r requirements.txt
```

或

```bash
pip install faster-whisper yt-dlp opencc-python-reimplemented
```

第一次執行時會自動下載辨識模型（medium 約 1.5 GB、large-v3 約 3 GB），之後不需重新下載。

## 使用方式

```bash
python yt_whisper_srt.py "https://youtu.be/影片ID"
```

字幕會存到目前資料夾下的 `subtitles\影片標題 [影片ID].srt`。

### 更多範例

```bash
# 多支影片一次處理
python yt_whisper_srt.py 網址1 網址2 網址3

# 整個播放清單
python yt_whisper_srt.py "https://www.youtube.com/playlist?list=xxxx"

# 本機影片或音訊檔
python yt_whisper_srt.py 影片.mp4

# 英文影片
python yt_whisper_srt.py 網址 --lang en

# 自動偵測語言
python yt_whisper_srt.py 網址 --lang auto

# 外語影片直接產生英文字幕
python yt_whisper_srt.py 網址 --translate

# CPU 太慢時改用較小的模型
python yt_whisper_srt.py 網址 --model small

# 指定輸出資料夾、另存純文字稿、保留下載的音訊
python yt_whisper_srt.py 網址 --out D:\字幕 --txt --keep-audio
```

### 參數

| 參數 | 說明 | 預設 |
|---|---|---|
| `--model` | `tiny` / `base` / `small` / `medium` / `large-v3`，越大越準也越慢 | 有 GPU：`large-v3`；無：`medium` |
| `--lang` | 語言代碼，如 `zh`、`en`、`ja`；`auto` 為自動偵測 | `zh` |
| `--out` | 輸出資料夾 | `subtitles` |
| `--translate` | 翻譯成英文字幕 | 關閉 |
| `--txt` | 另外輸出純文字 `.txt` | 關閉 |
| `--keep-audio` | 保留下載的音訊檔 | 關閉 |

### 速度參考

CPU 執行 `medium` 模型，大約需要接近影片長度的時間；`small` 約快 2–3 倍但準確度較低。使用 NVIDIA 顯卡（需安裝 CUDA 12 與 cuDNN 9）可快 10 倍以上。

## 把字幕加回 YouTube

自己的影片：YouTube Studio → 字幕 → 選擇影片 → 新增語言 → 上傳檔案 → 選「含時間碼」→ 選擇產生的 `.srt`。

## 常見問題

**出現 `huggingface_hub ... symlinks` 警告**
Windows 預設不支援符號連結，只是快取多佔一點空間，可忽略（新版腳本已隱藏此警告）。

**出現 `No supported JavaScript runtime` 警告，或部分影片下載失敗**
安裝 deno 即可：

```bash
winget install DenoLand.Deno
```

並更新 yt-dlp：`pip install -U yt-dlp`

**`open() got an unexpected keyword argument 'metadata_errors'`**
PyAV 15 版與舊版 faster-whisper 不相容，腳本已內建修正；若仍發生請更新到最新版腳本。

**字幕有錯字**
可改用較大的模型（`--model large-v3`），或用任何文字編輯器直接修改 `.srt`。

## 授權

MIT License
