import os
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import sv_ttk
import yt_dlp

DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads")

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _video_codec(path: str) -> str | None:
    if not shutil.which("ffprobe"):
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_name", "-of", "csv=p=0", path,
            ],
            capture_output=True, text=True, timeout=30, creationflags=_NO_WINDOW,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def _reencode_to_h264(path: str) -> bool:
    """Re-encode in place to H.264/AAC. Returns True on success."""
    tmp_path = path + ".reencoded.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        tmp_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=1800, creationflags=_NO_WINDOW)
    except Exception:
        result = None
    if result is not None and result.returncode == 0 and os.path.exists(tmp_path):
        os.replace(tmp_path, path)
        return True
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    return False


class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Clipster")
        self.root.geometry("600x460")
        self.root.minsize(600, 460)

        self.video_info = None
        self.height_options: dict[str, int | None] = {}
        self.output_dir = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.mode = tk.StringVar(value="video")

        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Label(outer, text="Clipster", font=("Segoe UI", 18, "bold"))
        header.pack(anchor="w")
        ttk.Label(
            outer, text="Baixe vídeos e áudios a partir de uma URL", foreground="#888"
        ).pack(anchor="w", pady=(0, 12))

        url_frame = ttk.LabelFrame(outer, text="URL", padding=12)
        url_frame.pack(fill="x", pady=(0, 12))
        entry_row = ttk.Frame(url_frame)
        entry_row.pack(fill="x")
        self.url_entry = ttk.Entry(entry_row)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.fetch_btn = ttk.Button(entry_row, text="Buscar", command=self.on_fetch)
        self.fetch_btn.pack(side="left", padx=(8, 0))

        self.title_label = ttk.Label(url_frame, text="", wraplength=540, foreground="#888")
        self.title_label.pack(fill="x", pady=(8, 0))

        format_frame = ttk.LabelFrame(outer, text="Formato e qualidade", padding=12)
        format_frame.pack(fill="x", pady=(0, 12))
        mode_row = ttk.Frame(format_frame)
        mode_row.pack(fill="x")
        ttk.Radiobutton(
            mode_row, text="Vídeo (MP4)", variable=self.mode, value="video",
            command=self.on_mode_change,
        ).pack(side="left")
        ttk.Radiobutton(
            mode_row, text="Áudio (MP3)", variable=self.mode, value="audio",
            command=self.on_mode_change,
        ).pack(side="left", padx=(16, 0))

        quality_row = ttk.Frame(format_frame)
        quality_row.pack(fill="x", pady=(10, 0))
        ttk.Label(quality_row, text="Qualidade:").pack(side="left")
        self.quality_combo = ttk.Combobox(quality_row, state="disabled", width=30)
        self.quality_combo.pack(side="left", padx=(8, 0))

        out_frame = ttk.LabelFrame(outer, text="Destino", padding=12)
        out_frame.pack(fill="x", pady=(0, 12))
        out_row = ttk.Frame(out_frame)
        out_row.pack(fill="x")
        self.out_entry = ttk.Entry(out_row, textvariable=self.output_dir, state="readonly")
        self.out_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(out_row, text="Escolher pasta", command=self.on_choose_folder).pack(
            side="left", padx=(8, 0)
        )

        self.download_btn = ttk.Button(
            outer, text="Baixar", style="Accent.TButton", command=self.on_download,
            state="disabled",
        )
        self.download_btn.pack(fill="x", pady=(4, 10))

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.pack(fill="x")

        self.status_label = ttk.Label(
            outer, text="Cole uma URL e clique em Buscar.", foreground="#888"
        )
        self.status_label.pack(fill="x", pady=(8, 0))

    def on_mode_change(self):
        if self.video_info is not None:
            self._populate_quality_options()

    def on_choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir.get())
        if chosen:
            self.output_dir.set(chosen)

    def on_fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Atenção", "Cole uma URL antes de buscar.")
            return

        self.fetch_btn.config(state="disabled")
        self.status_label.config(text="Buscando informações do vídeo...")
        self.title_label.config(text="")
        self.download_btn.config(state="disabled")
        self.quality_combo.config(state="disabled")

        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url: str):
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            self.root.after(0, self._on_fetch_error, str(exc))
            return
        self.root.after(0, self._on_fetch_success, info)

    def _on_fetch_error(self, message: str):
        self.fetch_btn.config(state="normal")
        self.status_label.config(text="Erro ao buscar o vídeo.")
        messagebox.showerror("Erro", f"Não foi possível obter informações do vídeo:\n{message}")

    def _on_fetch_success(self, info: dict):
        self.video_info = info
        self.fetch_btn.config(state="normal")
        self.title_label.config(text=info.get("title", "(sem título)"))
        self.status_label.config(text="Vídeo encontrado. Escolha o formato e a qualidade.")
        self._populate_quality_options()
        self.download_btn.config(state="normal")

    def _populate_quality_options(self):
        self.quality_combo.config(state="readonly")
        if self.mode.get() == "audio":
            values = ["Alta (320kbps)", "Média (192kbps)", "Baixa (128kbps)"]
            self.height_options = {values[0]: 320, values[1]: 192, values[2]: 128}
            self.quality_combo["values"] = values
            self.quality_combo.current(1)
            return

        formats = self.video_info.get("formats", []) if self.video_info else []
        heights = sorted(
            {f.get("height") for f in formats if f.get("vcodec") not in (None, "none") and f.get("height")},
            reverse=True,
        )
        values = ["Melhor disponível"] + [f"{h}p" for h in heights]
        self.height_options = {"Melhor disponível": None}
        self.height_options.update({f"{h}p": h for h in heights})
        self.quality_combo["values"] = values
        self.quality_combo.current(0)

    def on_download(self):
        if self.video_info is None:
            return
        url = self.url_entry.get().strip()
        mode = self.mode.get()
        choice = self.quality_combo.get()

        if mode == "video" and not ffmpeg_available():
            proceed = messagebox.askyesno(
                "ffmpeg não encontrado",
                "O ffmpeg não foi encontrado no sistema. Sem ele, vídeo e áudio podem não ser "
                "combinados corretamente em algumas qualidades.\n\nDeseja tentar baixar mesmo assim?",
            )
            if not proceed:
                return
        if mode == "audio" and not ffmpeg_available():
            messagebox.showerror(
                "ffmpeg necessário",
                "Baixar em MP3 exige o ffmpeg instalado e disponível no PATH do sistema.",
            )
            return

        self.download_btn.config(state="disabled")
        self.fetch_btn.config(state="disabled")
        self.progress["value"] = 0
        self.status_label.config(text="Iniciando download...")

        threading.Thread(
            target=self._download_worker, args=(url, mode, choice), daemon=True
        ).start()

    def _progress_hook(self, d: dict):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total else 0
            self.root.after(0, self._update_progress, pct, "Baixando...")
        elif d["status"] == "finished":
            # Fallback for formats that skip postprocessing entirely (e.g. a
            # single progressive stream with no merge/conversion needed) --
            # _postprocessor_hook won't fire in that case, so this is the
            # only chance to learn the final filepath for the codec check.
            filename = d.get("filename")
            if filename:
                self._last_filepath = filename
            self.root.after(0, self._update_progress, 100, "Processando...")

    def _update_progress(self, pct: float, text: str):
        self.progress["value"] = pct
        self.status_label.config(text=text)

    def _postprocessor_hook(self, d: dict):
        if d.get("status") == "finished":
            filepath = d.get("info_dict", {}).get("filepath")
            if filepath:
                self._last_filepath = filepath

    def _download_worker(self, url: str, mode: str, choice: str):
        out_dir = self.output_dir.get()
        os.makedirs(out_dir, exist_ok=True)
        outtmpl = os.path.join(out_dir, "%(title)s.%(ext)s")
        self._last_filepath = None

        opts = {
            "outtmpl": outtmpl,
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        if mode == "audio":
            quality = self.height_options.get(choice, 192)
            opts.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": str(quality),
                        }
                    ],
                }
            )
        else:
            height = self.height_options.get(choice)
            # Prefer H.264 (avc1) video + AAC/m4a audio since that combo plays
            # everywhere without extra codecs. If the site has no H.264 stream
            # (e.g. some 4K-only sources), we fall back to the best available
            # and re-encode to H.264 below so playback never breaks.
            hsuffix = f"[height<={height}]" if height else ""
            fmt = (
                f"bestvideo[vcodec^=avc]{hsuffix}+bestaudio[ext=m4a]/"
                f"bestvideo[vcodec^=avc]{hsuffix}+bestaudio/"
                f"bestvideo{hsuffix}+bestaudio/"
                f"best{hsuffix}"
            )
            opts.update({"format": fmt, "merge_output_format": "mp4"})

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as exc:
            self.root.after(0, self._on_download_error, str(exc))
            return

        reencode_failed = False
        if mode == "video" and self._last_filepath and os.path.exists(self._last_filepath):
            codec = _video_codec(self._last_filepath)
            if codec and codec not in ("h264",):
                self.root.after(0, self._update_progress, 100, "Convertendo para H.264 (compatibilidade)...")
                reencode_failed = not _reencode_to_h264(self._last_filepath)

        self.root.after(0, self._on_download_success, out_dir, reencode_failed)

    def _on_download_error(self, message: str):
        self.download_btn.config(state="normal")
        self.fetch_btn.config(state="normal")
        self.status_label.config(text="Erro no download.")
        messagebox.showerror("Erro", f"Falha ao baixar:\n{message}")

    def _on_download_success(self, out_dir: str, reencode_failed: bool = False):
        self.download_btn.config(state="normal")
        self.fetch_btn.config(state="normal")
        self.progress["value"] = 100
        self.status_label.config(text="Download concluído!")
        if reencode_failed:
            messagebox.showwarning(
                "Concluído com aviso",
                f"Download salvo em:\n{out_dir}\n\n"
                "O vídeo não usa o codec H.264 e a conversão automática falhou "
                "(verifique se o ffmpeg instalado suporta libx264). O arquivo pode "
                "não reproduzir em todos os players.",
            )
        else:
            messagebox.showinfo("Concluído", f"Download salvo em:\n{out_dir}")


def main():
    root = tk.Tk()
    DownloaderApp(root)
    sv_ttk.set_theme("dark")
    root.mainloop()


if __name__ == "__main__":
    main()
