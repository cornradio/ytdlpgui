import customtkinter as ctk
from tkinter import messagebox, filedialog
import subprocess
import queue
import os
import sys
import threading
import tempfile
import webbrowser
import configparser
import shutil
import json
from datetime import datetime

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

_SUBPROCESS_FLAGS = {}
if IS_WIN and hasattr(subprocess, 'CREATE_NO_WINDOW'):
    _SUBPROCESS_FLAGS['creationflags'] = subprocess.CREATE_NO_WINDOW

def _run(*args, **kwargs):
    kwargs = {**_SUBPROCESS_FLAGS, **kwargs}
    return subprocess.run(*args, **kwargs)

def _popen(*args, **kwargs):
    kwargs = {**_SUBPROCESS_FLAGS, **kwargs}
    return subprocess.Popen(*args, **kwargs)

if IS_WIN:
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

if IS_MAC:
    try:
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    except ImportError:
        pass

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class YtDlpGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("yt-dlp GUI v3.0 by kasusa")
        self.geometry("900x650")
        self.minsize(650, 500)

        if IS_WIN:
            try:
                self.iconbitmap(resource_path("icon.ico"))
            except:
                pass
        else:
            try:
                from PIL import Image, ImageTk
                icon_img = Image.open(resource_path("icon.png"))
                self._icon_photo = ImageTk.PhotoImage(icon_img)
                self.iconphoto(True, self._icon_photo)
            except:
                pass

        self.config_parser = configparser.ConfigParser()
        default_download = os.path.join(os.path.expanduser("~"), "Downloads")
        try:
            self.config_parser.read('settings.ini')
            self.download_path = self.config_parser.get('Settings', 'download_path')
            self.ytdlp_path = self.config_parser.get('Settings', 'ytdlp_path')
        except:
            self.download_path = default_download
            self.ytdlp_path = "yt-dlp"

        if not os.path.isabs(self.download_path) or not os.path.exists(self.download_path):
            self.download_path = default_download
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path, exist_ok=True)

        self.last_downloaded_file = None
        self.queue = queue.Queue()
        self.active_processes = {}
        self.download_counter = 0
        self.history_file = 'download_history.json'
        self.history_data = []
        self.tags_data = []

        self._build_ui()
        self.load_history()
        self.load_tags()
        self.reload_cookie_files()
        self.after(100, self.process_queue)
        self.after(500, self.check_environment)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Top bar ---
        self.top_bar = ctk.CTkFrame(self, height=36, corner_radius=0)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_columnconfigure(10, weight=1)

        ctk.CTkLabel(self.top_bar, text="yt-dlp GUI", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=(12, 20), pady=6)

        self.rename_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self.top_bar, text="重命名", variable=self.rename_var,
                        command=self._toggle_rename, width=70, checkbox_width=18, checkbox_height=18).grid(
            row=0, column=1, padx=4, pady=6)

        self.cookie_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self.top_bar, text="Cookie", variable=self.cookie_var,
                        command=self._toggle_cookie, width=70, checkbox_width=18, checkbox_height=18).grid(
            row=0, column=2, padx=4, pady=6)

        self.proxy_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self.top_bar, text="代理", variable=self.proxy_var,
                        command=self._toggle_proxy, width=60, checkbox_width=18, checkbox_height=18).grid(
            row=0, column=3, padx=4, pady=6)

        self.mp4_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self.top_bar, text="MP4", variable=self.mp4_var,
                        width=55, checkbox_width=18, checkbox_height=18).grid(
            row=0, column=4, padx=4, pady=6)

        self.mp3_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self.top_bar, text="MP3", variable=self.mp3_var,
                        width=55, checkbox_width=18, checkbox_height=18).grid(
            row=0, column=5, padx=4, pady=6)

        self.help_menu_button = ctk.CTkButton(self.top_bar, text="帮助 ▾", width=60,
                                              fg_color="transparent",
                                              text_color=("gray20", "gray80"),
                                              hover_color=("gray85", "gray30"),
                                              command=self._show_help_menu)
        self.help_menu_button.grid(row=0, column=6, padx=4, pady=6)

        # spacer
        ctk.CTkLabel(self.top_bar, text="").grid(row=0, column=10)

        self.download_button = ctk.CTkButton(self.top_bar, text="▶ 下载", width=80,
                                             fg_color=("#2fa572", "#2fa572"),
                                             hover_color=("#1a8a5a", "#1a8a5a"),
                                             font=ctk.CTkFont(size=13, weight="bold"),
                                             command=self.start_download)
        self.download_button.grid(row=0, column=11, padx=(4, 8), pady=6)

        self.stop_button = ctk.CTkButton(self.top_bar, text="■", width=32,
                                         fg_color=("gray70", "gray30"),
                                         hover_color=("#cc4444", "#cc4444"),
                                         command=self.stop_all_downloads)
        self.stop_button.grid(row=0, column=12, padx=(0, 12), pady=6)

        # --- Main content ---
        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(3, weight=1)

        # URL row
        url_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        url_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        url_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(url_frame, text="URL:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=(0, 8))

        self.url_var = ctk.StringVar()
        self.url_entry = ctk.CTkEntry(url_frame, textvariable=self.url_var, height=32,
                                      placeholder_text="在此粘贴视频链接...")
        self.url_entry.grid(row=0, column=1, sticky="ew")
        self.url_entry.bind('<Return>', lambda e: self.start_download())

        btn_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=(8, 0))

        ctk.CTkButton(btn_frame, text="清除参数", width=70, height=30,
                      fg_color="transparent", border_width=1,
                      text_color=("gray20", "gray80"),
                      border_color=("gray60", "gray40"),
                      hover_color=("gray85", "gray30"),
                      command=self.clean_url_params).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="清空", width=50, height=30,
                      fg_color="transparent", border_width=1,
                      text_color=("gray20", "gray80"),
                      border_color=("gray60", "gray40"),
                      hover_color=("gray85", "gray30"),
                      command=self.clear_url).pack(side="left", padx=2)

        # Detail panels (rename / cookie / proxy)
        self.detail_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.detail_frame.grid_columnconfigure(0, weight=1)

        # Rename detail
        self.rename_panel = ctk.CTkFrame(self.detail_frame, fg_color=("gray92", "gray20"), corner_radius=8)
        rename_inner = ctk.CTkFrame(self.rename_panel, fg_color="transparent")
        rename_inner.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(rename_inner, text="文件名:").pack(side="left")
        self.rename_entry = ctk.CTkEntry(rename_inner, width=180, height=28)
        self.rename_entry.pack(side="left", padx=(4, 12))
        ctk.CTkLabel(rename_inner, text="标签:").pack(side="left")
        self.tag_var = ctk.StringVar()
        self.tag_entry = ctk.CTkComboBox(rename_inner, width=120, height=28, variable=self.tag_var, values=[])
        self.tag_entry.pack(side="left", padx=(4, 8))
        ctk.CTkButton(rename_inner, text="×", width=28, height=28, command=self.clear_all_tags).pack(side="left")

        # Cookie detail
        self.cookie_panel = ctk.CTkFrame(self.detail_frame, fg_color=("gray92", "gray20"), corner_radius=8)
        cookie_inner = ctk.CTkFrame(self.cookie_panel, fg_color="transparent")
        cookie_inner.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(cookie_inner, text="Cookie:").pack(side="left")
        self.cookie_combo_var = ctk.StringVar()
        self.cookie_combo = ctk.CTkComboBox(cookie_inner, width=160, height=28,
                                            variable=self.cookie_combo_var, values=[], state="readonly")
        self.cookie_combo.pack(side="left", padx=(4, 8))
        for txt, cmd in [("添加", self.add_cookie_file), ("编辑", self.open_cookie_file),
                         ("删除", self.delete_cookie_file), ("刷新", self.reload_cookie_files)]:
            ctk.CTkButton(cookie_inner, text=txt, width=45, height=28, command=cmd).pack(side="left", padx=2)

        # Proxy detail
        self.proxy_panel = ctk.CTkFrame(self.detail_frame, fg_color=("gray92", "gray20"), corner_radius=8)
        proxy_inner = ctk.CTkFrame(self.proxy_panel, fg_color="transparent")
        proxy_inner.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(proxy_inner, text="代理地址:").pack(side="left")
        self.proxy_entry = ctk.CTkEntry(proxy_inner, width=220, height=28, placeholder_text="127.0.0.1:7890")
        self.proxy_entry.pack(side="left", padx=(4, 8))
        ctk.CTkButton(proxy_inner, text="7890", width=50, height=28,
                      command=lambda: (self.proxy_entry.delete(0, "end"),
                                       self.proxy_entry.insert(0, "127.0.0.1:7890"))).pack(side="left")

        # Tabview for log / history
        self.tabview = ctk.CTkTabview(self.content, corner_radius=8)
        self.tabview.grid(row=3, column=0, sticky="nsew", padx=16, pady=(4, 8))

        self.tab_log = self.tabview.add("日志")
        self.tab_history = self.tabview.add("历史记录")

        # Log textbox
        self.log_text = ctk.CTkTextbox(self.tab_log, font=ctk.CTkFont(family="Menlo" if IS_MAC else "Consolas", size=12),
                                       state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

        # History
        history_top = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        history_top.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(history_top, text="双击条目填充 URL", font=ctk.CTkFont(size=11),
                     text_color=("gray50", "gray60")).pack(side="left")
        ctk.CTkButton(history_top, text="清空记录", width=70, height=26,
                      fg_color="transparent", border_width=1,
                      text_color=("gray20", "gray80"),
                      border_color=("gray60", "gray40"),
                      hover_color=("gray85", "gray30"),
                      command=self.clear_history).pack(side="right")

        self.history_text = ctk.CTkTextbox(self.tab_history, font=ctk.CTkFont(size=12), state="disabled")
        self.history_text.pack(fill="both", expand=True)
        self.history_text.bind("<Double-Button-1>", self.on_history_select)

        # --- Status bar ---
        self.status_frame = ctk.CTkFrame(self, height=32, corner_radius=0)
        self.status_frame.grid(row=3, column=0, sticky="ew")
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_var = ctk.StringVar(value="准备就绪")
        ctk.CTkLabel(self.status_frame, textvariable=self.status_var,
                     font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
                     anchor="w").grid(row=0, column=0, padx=12, sticky="w")

        status_btns = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        status_btns.grid(row=0, column=1, padx=8, pady=4)

        ctk.CTkButton(status_btns, text="环境检查", width=70, height=24,
                      fg_color="transparent", hover_color=("gray85", "gray30"),
                      text_color=("gray20", "gray80"),
                      border_width=1, border_color=("gray60", "gray40"),
                      font=ctk.CTkFont(size=11), command=self.check_environment).pack(side="left", padx=2)
        self.upgrade_btn = ctk.CTkButton(status_btns, text="升级 yt-dlp", width=80, height=24,
                      fg_color="transparent", hover_color=("gray85", "gray30"),
                      text_color=("gray20", "gray80"),
                      border_width=1, border_color=("gray60", "gray40"),
                      font=ctk.CTkFont(size=11), command=self.upgrade_ytdlp)
        self.upgrade_btn.pack(side="left", padx=2)
        ctk.CTkButton(status_btns, text="打开文件夹", width=80, height=24,
                      fg_color="transparent", hover_color=("gray85", "gray30"),
                      text_color=("gray20", "gray80"),
                      border_width=1, border_color=("gray60", "gray40"),
                      font=ctk.CTkFont(size=11), command=self.open_download_folder).pack(side="left", padx=2)

    # --- Toggle panels ---
    def _update_detail_frame(self):
        any_visible = self.rename_var.get() or self.cookie_var.get() or self.proxy_var.get()
        if any_visible:
            self.detail_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        else:
            self.detail_frame.grid_forget()

    def _toggle_rename(self):
        if self.rename_var.get():
            self.rename_panel.grid(row=0, column=0, sticky="ew", pady=(2, 2))
        else:
            self.rename_panel.grid_forget()
        self._update_detail_frame()

    def _toggle_cookie(self):
        if self.cookie_var.get():
            self.cookie_panel.grid(row=1, column=0, sticky="ew", pady=(2, 2))
        else:
            self.cookie_panel.grid_forget()
        self._update_detail_frame()

    def _toggle_proxy(self):
        if self.proxy_var.get():
            self.proxy_panel.grid(row=2, column=0, sticky="ew", pady=(2, 2))
            if not self.proxy_entry.get():
                self.proxy_entry.insert(0, "127.0.0.1:7890")
        else:
            self.proxy_panel.grid_forget()
        self._update_detail_frame()

    # --- Help menu ---
    def _show_help_menu(self):
        import tkinter as tk
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="GitHub 仓库", command=self.open_github_repo)
        menu.add_command(label="快速答疑 FAQ", command=self.open_github_faq)
        menu.add_command(label="bilibili 教程", command=self.open_bilibili_video)
        menu.add_command(label="kasusa的Appstore", command=self.open_appstore)
        menu.add_separator()
        menu.add_command(label="下载 yt-dlp", command=self.get_ytdlp)
        menu.add_command(label="下载 ffmpeg", command=self.get_ffmpeg)
        menu.add_command(label="加速下载", command=self.search_cn_mirror)
        menu.add_separator()
        menu.add_command(label="打开程序目录 (放置二进制文件)", command=self.open_bin_dir)
        menu.add_separator()
        menu.add_command(label="升级 yt-dlp", command=self.upgrade_ytdlp)

        x = self.help_menu_button.winfo_rootx()
        y = self.help_menu_button.winfo_rooty() + self.help_menu_button.winfo_height()
        menu.tk_popup(x, y)

    # --- URL actions ---
    def clean_url_params(self):
        url = self.url_var.get().strip()
        if '?' in url:
            base_url = url.split('?')[0]
            if base_url != url:
                self.url_var.set(base_url)
                self.set_status("已删除 URL 参数")
                self.log(f"Cleaned URL: {base_url}")

    def clear_url(self):
        self.url_var.set("")

    # --- Cookie management ---
    def reload_cookie_files(self):
        cookies_dir = "cookies"
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir, exist_ok=True)
        files = [f for f in os.listdir(cookies_dir) if f.endswith('.txt')]
        self.cookie_combo.configure(values=files)
        if files and self.cookie_combo_var.get() not in files:
            self.cookie_combo_var.set(files[0])
        elif not files:
            self.cookie_combo_var.set("")

    def add_cookie_file(self):
        dialog = ctk.CTkInputDialog(text="请输入文件名（不含扩展名）:", title="新建 Cookie 文件")
        name = dialog.get_input()
        if not name:
            return
        name = name.strip()
        if not name:
            return
        for char in '<>:"/\\|?*':
            name = name.replace(char, '_')
        if not name.endswith('.txt'):
            name += '.txt'

        cookies_dir = "cookies"
        os.makedirs(cookies_dir, exist_ok=True)
        file_path = os.path.join(cookies_dir, name)
        if os.path.exists(file_path):
            messagebox.showwarning("文件已存在", f"文件 {name} 已存在")
            return
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n# Edit cookies below\n\n")
        self.log(f"已创建: {name}")
        self.reload_cookie_files()
        self.cookie_combo_var.set(name)
        self.open_cookie_file()

    def open_cookie_file(self):
        selected = self.cookie_combo_var.get()
        if not selected:
            return
        cookie_path = os.path.join("cookies", selected)
        if not os.path.exists(cookie_path):
            return
        try:
            if IS_WIN:
                _popen(['notepad', cookie_path])
            elif IS_MAC:
                _run(['open', '-a', 'TextEdit', cookie_path])
            else:
                _run(['xdg-open', cookie_path])
        except Exception as e:
            self.log(f"Error opening: {e}")

    def delete_cookie_file(self):
        selected = self.cookie_combo_var.get()
        if not selected:
            return
        if messagebox.askyesno("确认删除", f"确定要删除 {selected} 吗？"):
            try:
                os.remove(os.path.join("cookies", selected))
                self.log(f"已删除: {selected}")
                self.reload_cookie_files()
            except Exception as e:
                self.log(f"删除失败: {e}")

    # --- Tags ---
    def load_tags(self):
        try:
            if os.path.exists('tags_history.json'):
                with open('tags_history.json', 'r', encoding='utf-8') as f:
                    self.tags_data = json.load(f)
            self._update_tag_combo()
        except:
            self.tags_data = []

    def save_tags(self):
        try:
            with open('tags_history.json', 'w', encoding='utf-8') as f:
                json.dump(self.tags_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _update_tag_combo(self):
        self.tag_entry.configure(values=list(self.tags_data))

    def clear_all_tags(self):
        if not self.tags_data:
            return
        if messagebox.askyesno("确认", "确定要清除所有标签吗？"):
            self.tags_data = []
            self.save_tags()
            self._update_tag_combo()
            self.tag_var.set("")
            self.log("所有标签已清除")

    # --- History ---
    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history_data = json.load(f)
            self.update_history_display()
        except:
            self.history_data = []

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def update_history_display(self):
        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", "end")
        for item in reversed(self.history_data[-50:]):
            title = item.get('title', 'Unknown')
            url = item.get('url', '')
            if len(title) > 40:
                title = title[:37] + "..."
            if len(url) > 50:
                url = url[:47] + "..."
            self.history_text.insert("end", f"{title}  |  {url}\n")
        self.history_text.configure(state="disabled")

    def add_to_history(self, url, title=None):
        for item in self.history_data:
            if item.get('url') == url:
                item['timestamp'] = datetime.now().isoformat()
                if title:
                    item['title'] = title
                self.save_history()
                self.update_history_display()
                return
        self.history_data.append({
            'url': url,
            'title': title or 'Unknown',
            'timestamp': datetime.now().isoformat()
        })
        if len(self.history_data) > 1000:
            self.history_data = self.history_data[-1000:]
        self.save_history()
        self.update_history_display()

    def on_history_select(self, event):
        try:
            index = self.history_text.index("current")
            line_num = int(index.split(".")[0])
            line_content = self.history_text.get(f"{line_num}.0", f"{line_num}.end").strip()
            if "|" in line_content:
                displayed_count = min(50, len(self.history_data))
                actual_index = len(self.history_data) - line_num
                if 0 <= actual_index < len(self.history_data):
                    url = self.history_data[actual_index].get('url', '')
                    self.url_var.set(url)
                    title = self.history_data[actual_index].get('title', '')
                    self.set_status(f"已加载: {title}")
        except:
            pass

    def clear_history(self):
        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？"):
            self.history_data = []
            self.save_history()
            self.update_history_display()
            self.log("历史记录已清空")

    # --- Download ---
    def get_video_title(self, url):
        try:
            cmd = [self.ytdlp_path, url, "--print", "%(title)s", "--no-download"]
            if self.proxy_var.get():
                proxy = self.proxy_entry.get()
                if proxy:
                    cmd.extend(["--proxy", proxy])
            if self.cookie_var.get():
                selected = self.cookie_combo_var.get()
                if selected:
                    cookie_path = os.path.join("cookies", selected)
                    if os.path.exists(cookie_path):
                        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                        tmp.close()
                        shutil.copy2(cookie_path, tmp.name)
                        cmd.extend(["--cookies", tmp.name])
            result = _run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                title = result.stdout.strip()
                return title if title else None
        except:
            pass
        return None

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            self.log("请输入 URL")
            return

        self.add_to_history(url, "获取中...")
        thread = threading.Thread(target=self._download_worker, args=(url,), daemon=True)
        thread.start()

    def _download_worker(self, url):
        self.download_counter += 1
        download_id = self.download_counter

        self.queue.put(f"[下载 {download_id}] 正在获取视频信息...")

        video_title = self.get_video_title(url)
        if video_title:
            self.add_to_history(url, video_title)
            self.queue.put(f"[下载 {download_id}] 标题: {video_title}")
        else:
            self.add_to_history(url, "Unknown")

        short_url = url[:50] + "..." if len(url) > 50 else url
        self.queue.put(f"[下载 {download_id}] 开始: {short_url}")

        command = [self.ytdlp_path, url]

        if self.proxy_var.get():
            proxy = self.proxy_entry.get()
            if proxy:
                command.extend(["--proxy", proxy])

        if self.cookie_var.get():
            selected = self.cookie_combo_var.get()
            if selected:
                cookie_path = os.path.join("cookies", selected)
                if os.path.exists(cookie_path):
                    try:
                        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                        tmp.close()
                        shutil.copy2(cookie_path, tmp.name)
                        command.extend(["--cookies", tmp.name])
                    except:
                        pass

        command.extend(["-U"])

        if self.mp4_var.get():
            command.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
            command.extend(["--merge-output-format", "mp4"])

        if self.mp3_var.get():
            command.extend(["--extract-audio", "--audio-format", "mp3"])

        if self.rename_var.get():
            base_name = self.rename_entry.get().strip()
            tag_val = self.tag_var.get().strip()
            if base_name or tag_val:
                name = base_name if base_name else "%(title)s"
                if tag_val:
                    name = f"{name}#{tag_val}"
                    if tag_val not in self.tags_data:
                        self.tags_data.append(tag_val)
                        self.after(0, self.save_tags)
                        self.after(0, self._update_tag_combo)
                for c in '<>:"/\\|?*':
                    name = name.replace(c, '_')
                command.extend(["-o", f"{name}.%(ext)s"])
            else:
                command.extend(["-o", "%(title)s-%(id)s.%(ext)s"])
        else:
            command.extend(["-o", "%(title)s-%(id)s.%(ext)s"])

        command.extend(["-P", self.download_path])
        self._run_process(command, download_id)

    def _run_process(self, command, download_id):
        try:
            process = _popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1, universal_newlines=True)
            self.active_processes[download_id] = process

            for line in iter(process.stdout.readline, ''):
                if self.active_processes.get(download_id) is None:
                    break
                if line:
                    self.queue.put(f"[下载 {download_id}] {line.rstrip()}")
                if process.poll() is not None:
                    break

            process.stdout.close()
            return_code = process.wait()

            if download_id in self.active_processes:
                del self.active_processes[download_id]

            if return_code in (0, 1):
                self.queue.put(f"[下载 {download_id}] 完成!")
                self.after(0, lambda: self.set_status(f"下载 {download_id} 完成", duration=5000))
            else:
                self.queue.put(f"[下载 {download_id}] 失败 (错误码: {return_code})")
                self.after(0, lambda: self.set_status(f"下载 {download_id} 失败", duration=5000))

        except Exception as e:
            self.queue.put(f"[下载 {download_id}] 错误: {e}")
            if download_id in self.active_processes:
                del self.active_processes[download_id]

    def stop_all_downloads(self):
        if not self.active_processes:
            self.set_status("没有正在下载的任务", duration=2000)
            return
        stopped = 0
        for did, proc in list(self.active_processes.items()):
            try:
                if IS_WIN:
                    _run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.terminate()
                stopped += 1
                self.queue.put(f"[下载 {did}] 已停止")
            except:
                pass
        self.active_processes.clear()
        if stopped:
            self.set_status(f"已停止 {stopped} 个下载任务", duration=3000)

    # --- Environment check ---
    def check_environment(self):
        self.log("━" * 45)
        self.log("  环境检查")
        self.log("━" * 45)
        thread = threading.Thread(target=self._check_env_worker, daemon=True)
        thread.start()

    def _check_env_worker(self):
        issues = []

        # Check yt-dlp
        try:
            result = _run([self.ytdlp_path, "--version"],
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                ver = result.stdout.strip()
                self.queue.put(f"  ✓ yt-dlp 已安装 (版本: {ver})")
                # Check path
                which_cmd = "where" if IS_WIN else "which"
                loc = _run([which_cmd, self.ytdlp_path],
                                    capture_output=True, text=True, timeout=5)
                if loc.returncode == 0:
                    self.queue.put(f"    路径: {loc.stdout.strip()}")
            else:
                self.queue.put("  ✗ yt-dlp 未正常工作")
                issues.append("yt-dlp")
        except FileNotFoundError:
            self.queue.put("  ✗ yt-dlp 未安装!")
            issues.append("yt-dlp")
            if IS_MAC:
                self.queue.put("    安装方式:")
                self.queue.put("      brew install yt-dlp")
                self.queue.put("      或 pip3 install yt-dlp")
            elif IS_WIN:
                self.queue.put("    安装方式:")
                self.queue.put("      winget install yt-dlp")
                self.queue.put("      或 pip install yt-dlp")
            else:
                self.queue.put("    安装: pip3 install yt-dlp")
        except Exception as e:
            self.queue.put(f"  ✗ yt-dlp 检查失败: {e}")
            issues.append("yt-dlp")

        # Check ffmpeg
        try:
            result = _run(["ffmpeg", "-version"],
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                first_line = result.stdout.split('\n')[0]
                self.queue.put(f"  ✓ ffmpeg 已安装 ({first_line.strip()})")
                which_cmd = "where" if IS_WIN else "which"
                loc = _run([which_cmd, "ffmpeg"],
                                    capture_output=True, text=True, timeout=5)
                if loc.returncode == 0:
                    self.queue.put(f"    路径: {loc.stdout.strip()}")
            else:
                self.queue.put("  ✗ ffmpeg 未正常工作")
                issues.append("ffmpeg")
        except FileNotFoundError:
            self.queue.put("  ✗ ffmpeg 未安装!")
            self.queue.put("    ⚠ 没有 ffmpeg 将无法合并视频和音频!")
            issues.append("ffmpeg")
            if IS_MAC:
                self.queue.put("    安装方式:")
                self.queue.put("      brew install ffmpeg")
            elif IS_WIN:
                self.queue.put("    安装方式:")
                self.queue.put("      winget install ffmpeg")
                self.queue.put("      或从 https://ffmpeg.org/download.html 下载")
            else:
                self.queue.put("    安装: sudo apt install ffmpeg")
        except Exception as e:
            self.queue.put(f"  ✗ ffmpeg 检查失败: {e}")
            issues.append("ffmpeg")

        # Check ffprobe (usually comes with ffmpeg)
        try:
            result = _run(["ffprobe", "-version"],
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.queue.put("  ✓ ffprobe 已安装")
            else:
                self.queue.put("  ✗ ffprobe 未正常工作")
        except FileNotFoundError:
            self.queue.put("  ✗ ffprobe 未安装 (通常随 ffmpeg 一起安装)")
        except:
            pass

        # Summary
        self.queue.put("━" * 45)
        if not issues:
            self.queue.put("  ✓ 环境正常，所有依赖已就绪!")
            self.after(0, lambda: self.set_status("环境检查通过", duration=3000))
        else:
            missing = "、".join(issues)
            self.queue.put(f"  ⚠ 缺少: {missing}")
            self.queue.put("  请按上方提示安装后重新检查")
            self.queue.put("")
            self.queue.put("  💡 提示: 也可以从「帮助」菜单下载二进制文件,")
            self.queue.put("     放入「打开程序目录」所示的文件夹中即可")
            self.after(0, lambda: self.set_status(f"缺少依赖: {missing}", duration=5000))
        self.queue.put("")

    # --- Upgrade ---
    def upgrade_ytdlp(self):
        """Show popup menu with multiple upgrade method options."""
        import tkinter as tk
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="yt-dlp -U（自更新）",
                         command=lambda: self._run_upgrade("yt-dlp -U",
                                                           [self.ytdlp_path, "-U"]))
        menu.add_command(label="pipx upgrade yt-dlp",
                         command=lambda: self._run_upgrade("pipx upgrade yt-dlp",
                                                           ["pipx", "upgrade", "yt-dlp"]))
        menu.add_command(label="pip install --upgrade yt-dlp",
                         command=lambda: self._run_upgrade("pip install --upgrade yt-dlp",
                                                           ["pip", "install", "--upgrade", "yt-dlp"]))
        menu.add_command(label="pip3 install --upgrade yt-dlp",
                         command=lambda: self._run_upgrade("pip3 install --upgrade yt-dlp",
                                                           ["pip3", "install", "--upgrade", "yt-dlp"]))
        if IS_MAC:
            menu.add_command(label="brew upgrade yt-dlp",
                             command=lambda: self._run_upgrade("brew upgrade yt-dlp",
                                                               ["brew", "upgrade", "yt-dlp"]))
        elif IS_WIN:
            menu.add_command(label="scoop update yt-dlp",
                             command=lambda: self._run_upgrade("scoop update yt-dlp",
                                                               ["scoop", "update", "yt-dlp"]))
            menu.add_command(label="winget upgrade yt-dlp",
                             command=lambda: self._run_upgrade("winget upgrade yt-dlp",
                                                               ["winget", "upgrade", "yt-dlp"]))

        # Position the popup at the status bar upgrade button if possible
        try:
            btn = self.upgrade_btn
            x = btn.winfo_rootx()
            y = btn.winfo_rooty() - btn.winfo_height() * 6
        except:
            x = self.winfo_pointerx()
            y = self.winfo_pointery()
        menu.tk_popup(x, y)

    def _run_upgrade(self, label, cmd):
        """Log the chosen method and start the upgrade thread."""
        self.log(f"正在升级 yt-dlp（方式: {label}）...")
        self.log("─" * 40)
        self.set_status(f"正在升级... ({label})")
        thread = threading.Thread(target=self._upgrade_worker, args=(label, cmd), daemon=True)
        thread.start()

    def _upgrade_worker(self, label, cmd):
        try:
            result = _run([self.ytdlp_path, "--version"], capture_output=True, text=True, timeout=10)
            ver = result.stdout.strip() if result.returncode == 0 else "未知"
            self.queue.put(f"当前版本: {ver}")

            up = _run(cmd, capture_output=True, text=True, timeout=120)
            output = (up.stdout.strip() + "\n" + up.stderr.strip()).strip()
            if output:
                for line in output.splitlines():
                    self.queue.put(f"  {line}")

            if up.returncode == 0:
                result2 = _run([self.ytdlp_path, "--version"], capture_output=True, text=True, timeout=10)
                new_ver = result2.stdout.strip() if result2.returncode == 0 else "未知"
                if new_ver != ver:
                    self.queue.put(f"升级成功! {ver} → {new_ver}")
                else:
                    self.queue.put(f"已是最新版本: {new_ver}")
                self.after(0, lambda: self.set_status(f"yt-dlp {new_ver}", duration=5000))
            else:
                self.queue.put(f"升级失败（{label}），请检查该工具是否已安装")
                self.after(0, lambda: self.set_status("升级失败，请手动升级", duration=5000))
        except FileNotFoundError:
            self.queue.put(f"找不到命令: {cmd[0]}，请确认已安装该工具")
            self.after(0, lambda: self.set_status("升级失败：命令未找到", duration=5000))
        except Exception as e:
            self.queue.put(f"升级出错: {e}")

    # --- Open folder ---
    def open_download_folder(self):
        if self.download_path and os.path.isdir(self.download_path):
            try:
                if IS_WIN:
                    os.startfile(os.path.realpath(self.download_path))
                elif IS_MAC:
                    _run(['open', self.download_path])
                else:
                    _run(['xdg-open', self.download_path])
            except Exception as e:
                self.log(f"无法打开文件夹: {e}")
        else:
            self.log(f"路径不存在: {self.download_path}")

    # --- Links ---
    def open_github_repo(self):
        webbrowser.open("https://github.com/cornradio/ytdlpgui")

    def open_github_faq(self):
        webbrowser.open("https://github.com/cornradio/ytdlpgui/blob/main/how-to-use-cookie.md")

    def open_bilibili_video(self):
        webbrowser.open("https://www.bilibili.com/video/BV1oJ7ezEEqK")

    def open_appstore(self):
        webbrowser.open("https://appstore.cornradio.org/")

    def get_ytdlp(self):
        webbrowser.open("https://github.com/yt-dlp/yt-dlp/releases/latest")

    def get_ffmpeg(self):
        webbrowser.open("https://github.com/BtbN/FFmpeg-Builds/releases")

    def search_cn_mirror(self):
        webbrowser.open("https://www.baidu.com/s?wd=github+加速")

    def open_bin_dir(self):
        bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.log(f"程序目录: {bin_dir}")
        self.log("将下载的 yt-dlp / ffmpeg 二进制文件放入此目录即可使用")
        try:
            if IS_WIN:
                os.startfile(bin_dir)
            elif IS_MAC:
                _run(['open', bin_dir])
            else:
                _run(['xdg-open', bin_dir])
        except Exception as e:
            self.log(f"无法打开目录: {e}")

    # --- Utility ---
    def log(self, message):
        self.queue.put(message)

    def set_status(self, message, duration=3000):
        self.status_var.set(message)
        if hasattr(self, '_status_timer'):
            self.after_cancel(self._status_timer)
        self._status_timer = self.after(duration, lambda: self.status_var.set("准备就绪"))

    def process_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.configure(state="disabled")
                self.log_text.see("end")
                self.queue.task_done()
        except queue.Empty:
            pass
        self.after(100, self.process_queue)


if __name__ == '__main__':
    app = YtDlpGUI()
    app.mainloop()
