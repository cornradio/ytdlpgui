import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import subprocess
import queue
import os
import shlex
from ttkthemes import ThemedTk
import webbrowser
import configparser
import shutil
import tempfile
import json
from datetime import datetime

# macOS 版本 - 不需要 DPI 感知设置

# 设置 SSL 证书路径（解决 macOS 上的证书验证问题）
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except ImportError:
    pass  # 如果 certifi 未安装，使用系统默认

class YtDlpGUI:
    def __init__(self, master):
        self.master = master
        master.title("yt-dlp GUI")
        
        # 设置主题
        self.style = ttk.Style()
        self.style.theme_use('equilux')  # 使用equilux主题作为基础
        
        # macOS 系统字体
        mac_font = ('SF Pro Display', 10) if os.uname().sysname == 'Darwin' else ('Helvetica Neue', 10)
        mac_font_small = ('SF Pro Display', 9) if os.uname().sysname == 'Darwin' else ('Helvetica Neue', 9)
        mac_font_bold = ('SF Pro Display', 11, 'bold') if os.uname().sysname == 'Darwin' else ('Helvetica Neue', 11, 'bold')
        
        # 配置主题颜色
        self.style.configure('TFrame', background='#464646')
        self.style.configure('TLabel', background='#464646', foreground='white', font=mac_font)
        self.style.configure('TButton', background='#2b2b2b', foreground='white', font=mac_font)
        self.style.configure('TCheckbutton', background='#464646', foreground='white', font=mac_font)
        self.style.configure('TEntry', fieldbackground='#2b2b2b', foreground='white', font=mac_font)
        
        # 配置按钮样式
        self.style.map('TButton',
            background=[('active', '#404040'), ('disabled', '#2b2b2b')],
            foreground=[('disabled', '#666666')])
        
        # 状态栏按钮样式 - 小巧一点
        self.style.configure('Status.TButton', font=mac_font_small, padding=(4, 0))
        
        # 配置复选框样式
        self.style.map('TCheckbutton',
            background=[('active', '#404040')],
            foreground=[('disabled', '#666666')])
        
        # 配置输入框样式
        self.style.map('TEntry',
            fieldbackground=[('disabled', '#2b2b2b')],
            foreground=[('disabled', '#666666')])

        # 创建主框架
        self.main_frame = ttk.Frame(master, padding="15")
        self.main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 创建顶部菜单栏
        self.create_menu_bar()
        
        # 读取配置文件
        self.config = configparser.ConfigParser()
        try:
            self.config.read('settings.ini')
            self.download_path = self.config.get('Settings', 'download_path')
            # 如果路径是 Windows 路径，转换为 macOS 路径
            if 'C:\\' in self.download_path or self.download_path.startswith('C:'):
                self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
            elif not os.path.isabs(self.download_path):
                # 如果是相对路径，转换为绝对路径
                self.download_path = os.path.abspath(self.download_path)
            self.ytdlp_path = self.config.get('Settings', 'ytdlp_path')
        except:
            # 如果配置文件不存在或读取失败，使用默认值
            self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
            self.ytdlp_path = "yt-dlp"
            if not os.path.exists(self.download_path):
                self.download_path = os.getcwd()

        self.last_downloaded_file = None

        # URL输入区域
        self.url_label = ttk.Label(self.main_frame, text="URL:")
        self.url_label.grid(row=0, column=0, padx=12, pady=(12, 6), sticky=tk.W)
        
        # URL输入框和清除按钮的容器
        self.url_frame = ttk.Frame(self.main_frame)
        self.url_frame.grid(row=0, column=1, padx=12, pady=(12, 6), sticky=tk.W + tk.E)
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(self.url_frame, width=60, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.url_var.trace_add("write", self.on_url_change)
        self.url_entry.bind('<Return>', lambda e: self.start_download())  # Enter 键触发下载
        
        self.clear_button = ttk.Button(self.url_frame, text="Clear", width=5, command=self.clear_url)
        self.clear_button.pack(side=tk.LEFT, padx=(4, 0))
        
        self.url_frame.grid_columnconfigure(0, weight=1)

        # 代理设置
        self.proxy_var = tk.BooleanVar()
        self.use_proxy_checkbutton = ttk.Checkbutton(self.main_frame, text="Use Proxy",
                                                     variable=self.proxy_var, command=self.toggle_proxy_entry)
        self.use_proxy_checkbutton.grid(row=1, column=0, padx=12, pady=6, sticky=tk.W)

        self.proxy_entry = ttk.Entry(self.main_frame, width=60, state=tk.DISABLED)
        self.proxy_entry.grid(row=1, column=1, padx=12, pady=6, sticky=tk.W + tk.E)

        # 选项与下载按钮区域（合二为一）
        self.action_area = ttk.Frame(self.main_frame)
        self.action_area.grid(row=2, column=0, columnspan=2, padx=12, pady=10, sticky=(tk.W, tk.E))
        
        self.options_container = ttk.Frame(self.action_area)
        self.options_container.pack(side=tk.LEFT, fill=tk.Y)

        # Cookie设置
        self.cookie_var = tk.BooleanVar()
        self.cookie_frame = ttk.Frame(self.options_container)
        self.cookie_frame.pack(side=tk.TOP, anchor=tk.W, pady=2)
        
        self.use_cookie_checkbutton = ttk.Checkbutton(self.cookie_frame, text="Use Cookie",
                                                     variable=self.cookie_var)
        self.use_cookie_checkbutton.pack(side=tk.LEFT, padx=(0, 8))
        
        self.edit_cookie_button = ttk.Button(self.cookie_frame, text="编辑 Cookie", command=self.open_cookie_file)
        self.edit_cookie_button.pack(side=tk.LEFT, padx=8)

        # 格式选项区域
        self.format_frame = ttk.Frame(self.options_container)
        self.format_frame.pack(side=tk.TOP, anchor=tk.W, pady=2)
        
        self.mp4_var = tk.BooleanVar()
        self.mp4_checkbutton = ttk.Checkbutton(self.format_frame, text="Download as MP4",
                                             variable=self.mp4_var)
        self.mp4_checkbutton.pack(side=tk.LEFT, padx=(0, 16))
        
        self.mp3_var = tk.BooleanVar()
        self.mp3_checkbutton = ttk.Checkbutton(self.format_frame, text="Download as MP3",
                                             variable=self.mp3_var)
        self.mp3_checkbutton.pack(side=tk.LEFT, padx=8)

        # 下载按钮 - 移动到选项右侧，更加紧凑
        self.download_button = tk.Button(self.action_area, 
                                       text="Download（下载）", 
                                       command=self.start_download,
                                       font=mac_font_bold,
                                       fg='#00ff00',
                                       bg='#333333',
                                       activebackground='#444444',
                                       activeforeground='#5dfc5d',
                                       relief=tk.FLAT,
                                       borderwidth=0,
                                       highlightthickness=0,
                                       cursor='hand2',
                                       padx=40,
                                       pady=10)
        self.download_button.pack(side=tk.RIGHT, padx=12)


        # 历史记录和日志切换区域
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=12, pady=(0, 12))
        
        # 历史记录区域 - 整合边框和按钮
        self.history_frame = ttk.Frame(self.content_frame)
        self.history_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 内部标题和清空按钮区域
        self.history_inner_header = ttk.Frame(self.history_frame)
        self.history_inner_header.pack(fill=tk.X, padx=2, pady=2)
        
        self.history_label = ttk.Label(self.history_inner_header, text="历史记录:", font=mac_font_small + ('bold',))
        self.history_label.pack(side=tk.LEFT, padx=5)
        
        self.clear_history_button = tk.Button(self.history_inner_header, 
                                            text="清空记录", 
                                            command=self.clear_history,
                                            font=mac_font_small,
                                            fg='#888888',
                                            bg='#2b2b2b',
                                            activebackground='#404040',
                                            activeforeground='white',
                                            relief=tk.FLAT,
                                            padx=8)
        self.clear_history_button.pack(side=tk.RIGHT, padx=5)
        
        # 列表框 - 使用灰色边框，去除亮白色
        self.history_listbox = tk.Listbox(self.history_frame, 
                                          bg='#2b2b2b', 
                                          fg='#cccccc',
                                          selectbackground='#404040', 
                                          font=mac_font_small,
                                          borderwidth=0,
                                          highlightthickness=1,
                                          highlightbackground='#555555',  # 深灰色边框
                                          highlightcolor='#777777')       # 选中时的边框
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.history_listbox.bind('<Double-Button-1>', self.on_history_select)
        
        history_scrollbar = ttk.Scrollbar(self.history_frame, orient=tk.VERTICAL, command=self.history_listbox.yview)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.config(yscrollcommand=history_scrollbar.set)
        
        # 日志区域（默认隐藏）
        self.log_frame = ttk.Frame(self.content_frame)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, width=80, height=25, 
                                                bg='#2b2b2b', fg='white', insertbackground='white',
                                                font=('Menlo', 10))  # macOS 等宽字体
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 历史记录文件路径
        self.history_file = 'download_history.json'
        self.load_history()
        
        # 默认显示历史记录，隐藏日志
        self.log_frame.pack_forget()

        # 配置网格权重
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(1, weight=1)  # 主框架可扩展
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)  # 内容区域可扩展
        
        # 状态栏框架
        self.status_frame = ttk.Frame(master, style='TFrame')
        self.status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="准备就绪")
        self.status_bar = ttk.Label(self.status_frame, textvariable=self.status_var, relief=tk.FLAT, anchor=tk.W)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.style.configure('Status.TLabel', background='#333333', foreground='#aaaaaa', font=mac_font_small, padding=(10, 2))
        self.status_bar.configure(style='Status.TLabel')
        self.status_frame.configure(style='Status.TLabel') # 给框架也上色

        # 将切换日志和打开文件夹按钮放入状态栏右侧
        self.show_history_var = tk.BooleanVar(value=True)
        self.toggle_button = ttk.Button(self.status_frame, text="显示日志", command=self.toggle_content, style='Status.TButton')
        self.toggle_button.pack(side=tk.RIGHT, padx=2, pady=1)
        
        self.open_folder_button = ttk.Button(self.status_frame, text="打开文件夹", command=self.open_download_folder, style='Status.TButton')
        self.open_folder_button.pack(side=tk.RIGHT, padx=2, pady=1)

        # 设置窗口最小尺寸
        master.update_idletasks()
        master.minsize(500, 400)

        self.queue = queue.Queue()
        self.master.after(100, self.process_queue)

    def create_menu_bar(self):
        """创建顶部菜单栏（使用 ttk 组件）"""
        # 创建菜单栏框架
        self.menubar_frame = ttk.Frame(self.master)
        self.menubar_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=0, pady=0)
        self.menubar_frame.configure(style='TFrame')
        
        # Help 按钮
        self.help_button = ttk.Menubutton(self.menubar_frame, text="Help", direction='below')
        self.help_button.pack(side=tk.LEFT, padx=(0, 0))
        
        # 创建 Help 下拉菜单
        help_menu = tk.Menu(self.help_button, tearoff=0, bg='#2b2b2b', fg='white',
                           activebackground='#404040', activeforeground='white',
                           selectcolor='#404040', borderwidth=1)
        self.help_button['menu'] = help_menu
        
        help_menu.add_command(label="GitHub Repository", command=self.open_github_repo)
        help_menu.add_command(label="快速答疑 FAQ", command=self.open_github_faq)
        help_menu.add_command(label="bilibili 视频教程", command=self.open_bilibili_video)
        help_menu.add_separator()
        help_menu.add_command(label="下载 yt-dlp", command=self.get_ytdlp)
        help_menu.add_command(label="下载 ffmpeg", command=self.get_ffmpeg)
        
        # 分隔符标签
        separator_label = ttk.Label(self.menubar_frame, text="||", foreground='#888888')
        separator_label.pack(side=tk.LEFT, padx=(8, 8))
        
        # 版本信息标签
        version_label = ttk.Label(self.menubar_frame, text="ytdlpGUI v2.2 by kasusa (macOS)", foreground='#888888')
        version_label.pack(side=tk.LEFT, padx=(0, 8))
        
        # 配置菜单栏样式
        self.style.configure('TMenubutton', background='#2b2b2b', foreground='white', 
                            borderwidth=0, padding=(8, 4), relief='flat')
        self.style.map('TMenubutton',
                      background=[('active', '#404040'), ('!active', '#2b2b2b'), ('pressed', '#404040')],
                      foreground=[('active', 'white'), ('!active', 'white')],
                      relief=[('active', 'flat'), ('!active', 'flat')])
        
        # 确保菜单栏框架背景是黑色
        self.style.configure('TFrame', background='#464646')
        # 为菜单栏框架单独设置样式
        self.menubar_frame.configure(style='TFrame')


    def toggle_content(self):
        """切换历史记录和日志显示"""
        if self.show_history_var.get():
            # 切换到日志
            self.history_frame.pack_forget()
            self.log_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.toggle_button.config(text="显示历史记录")
            self.show_history_var.set(False)
        else:
            # 切换到历史记录
            self.log_frame.pack_forget()
            self.history_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.toggle_button.config(text="显示日志")
            self.show_history_var.set(True)

    def clear_history(self):
        """清空所有历史记录"""
        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？"):
            self.history_data = []
            self.save_history()
            self.update_history_display()
            self.log("History cleared.")

    def open_github_repo(self):
        webbrowser.open("https://github.com/cornradio/ytdlpgui")

    def open_github_faq(self):
        webbrowser.open("https://github.com/cornradio/ytdlpgui/blob/main/how-to-use-cookie.md")
    def open_bilibili_video(self):
        webbrowser.open("https://www.bilibili.com/video/BV1oJ7ezEEqK")

    def get_ytdlp(self):
        webbrowser.open('https://github.com/yt-dlp/yt-dlp/wiki/Installation')
    def get_ffmpeg(self):
        webbrowser.open('https://github.com/ffbinaries/ffbinaries-prebuilt/releases')

    def load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history_data = json.load(f)
            else:
                self.history_data = []
            self.update_history_display()
        except Exception as e:
            self.log(f"Error loading history: {e}")
            self.history_data = []

    def save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Error saving history: {e}")

    def update_history_display(self):
        """更新历史记录显示"""
        self.history_listbox.delete(0, tk.END)
        # 按时间倒序显示，最新的在前面
        for item in reversed(self.history_data[-50:]):  # 只显示最近50条
            title = item.get('title', 'Unknown')
            url = item.get('url', '')
            # 截断过长的标题和URL
            if len(title) > 40:
                title = title[:37] + "..."
            if len(url) > 40:
                url = url[:37] + "..."
            display_text = f"{title} | {url}"
            self.history_listbox.insert(0, display_text)

    def add_to_history(self, url, title=None):
        """添加历史记录"""
        # 检查是否已存在相同的URL
        for item in self.history_data:
            if item.get('url') == url:
                # 更新现有记录的时间
                item['timestamp'] = datetime.now().isoformat()
                if title:
                    item['title'] = title
                self.save_history()
                self.update_history_display()
                return
        
        # 添加新记录
        history_item = {
            'url': url,
            'title': title or 'Unknown',
            'timestamp': datetime.now().isoformat()
        }
        self.history_data.append(history_item)
        # 限制历史记录数量，最多保存1000条
        if len(self.history_data) > 1000:
            self.history_data = self.history_data[-1000:]
        self.save_history()
        self.update_history_display()

    def on_history_select(self, event):
        """双击历史记录项时填充URL"""
        selection = self.history_listbox.curselection()
        if selection and self.history_data:
            index = selection[0]
            # 由于显示是倒序的，需要转换索引
            # 只显示最近50条，所以需要计算实际索引
            displayed_count = min(50, len(self.history_data))
            actual_index = len(self.history_data) - 1 - index
            if 0 <= actual_index < len(self.history_data):
                url = self.history_data[actual_index].get('url', '')
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, url)
                title = self.history_data[actual_index].get('title', 'Unknown')
                self.log(f"Selected from history: {title}")
                self.set_status(f"已从历史记录加载: {title}")

    def open_settings(self):
        """打开 settings.ini 文件"""
        settings_path = os.path.abspath('settings.ini')
        if os.path.exists(settings_path):
            try:
                # macOS 使用 TextEdit 打开
                subprocess.run(['open', '-a', 'TextEdit', settings_path])
                self.log(f"opened settings.ini: {settings_path}")
                self.log(f"download_path: {self.download_path}")
                self.log(f"ytdlp_path: {self.ytdlp_path}")
                # 刷新配置文件
                self.config.read('settings.ini')
                self.download_path = self.config.get('Settings', 'download_path')
                self.ytdlp_path = self.config.get('Settings', 'ytdlp_path')
            except Exception as e:
                self.log(f"can't open settings.ini: {e}")
        else:
            self.log(f"settings.ini not found: {settings_path}")
            self.log(f"create settings.ini")
            # macOS 默认路径
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            self.config['Settings'] = {
                'download_path': downloads_path,
                'ytdlp_path': 'yt-dlp'
            }
            with open('settings.ini', 'w') as f:
                self.config.write(f)
            self.open_settings()

    def toggle_proxy_entry(self):
        """
        Enables or disables the proxy entry field based on the checkbox state.
        If enabled, sets the default proxy value "127.0.0.1:7890".
        Clears the proxy entry when disabled.
        """
        if self.proxy_var.get():
            self.proxy_entry.config(state=tk.NORMAL)
            self.proxy_entry.delete(0, tk.END)  # Clear any previous content
            self.proxy_entry.insert(0, "127.0.0.1:7890")  # Insert default proxy
        else:
            self.proxy_entry.delete(0, tk.END) # Clear content when disabling
            self.proxy_entry.config(state=tk.DISABLED)

    def open_cookie_file(self):
        """打开或创建 cookie.txt 文件供用户编辑"""
        cookie_path = os.path.abspath('cookie.txt')
        
        # 如果文件不存在，创建一个空的 Netscape 格式模板
        if not os.path.exists(cookie_path):
            try:
                with open(cookie_path, 'w', encoding='utf-8') as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    f.write("# This file was generated by ytdlpgui\n")
                    f.write("# You can edit this file with your cookies\n\n")
                self.log(f"Created cookie.txt: {cookie_path}")
            except Exception as e:
                self.log(f"Error creating cookie.txt: {e}")
                return
        
        # 打开文件 - macOS 使用 TextEdit
        try:
            subprocess.run(['open', '-a', 'TextEdit', cookie_path])
            self.log(f"Opened cookie.txt: {cookie_path}")
        except Exception as e:
            self.log(f"Error opening cookie.txt: {e}")

    def get_video_title(self, url):
        """获取视频标题"""
        try:
            # 构建获取信息的命令
            info_command = [self.ytdlp_path, url, "--print", "%(title)s", "--no-download"]
            
            # 添加代理设置（如果启用）
            if self.proxy_var.get():
                proxy_address = self.proxy_entry.get()
                if proxy_address:
                    info_command.extend(["--proxy", proxy_address])
            
            # 添加cookie设置（如果启用）
            if self.cookie_var.get():
                cookie_path = os.path.abspath('cookie.txt')
                if os.path.exists(cookie_path):
                    try:
                        temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                        temp_cookie_file.close()
                        shutil.copy2(cookie_path, temp_cookie_file.name)
                        info_command.extend(["--cookies", temp_cookie_file.name])
                    except:
                        pass
            
            result = subprocess.run(info_command, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                title = result.stdout.strip()
                return title if title else None
        except subprocess.TimeoutExpired:
            self.log("Timeout getting video title")
        except Exception as e:
            self.log(f"Could not get video title: {e}")
            self.set_status(f"获取视频信息失败")
        return None

    def start_download(self):
        url = self.url_entry.get()
        
        if not url:
            self.log("Error: Please enter a URL.")
            return

        # 获取视频标题并添加到历史记录
        self.log("Getting video information...")
        self.set_status("正在请求视频信息，请稍候...")
        video_title = self.get_video_title(url)
        if video_title:
            self.add_to_history(url, video_title)
            self.log(f"Video title: {video_title}")
            self.set_status(f"解析成功: {video_title}", duration=5000)
        else:
            # 即使获取标题失败，也记录URL
            self.add_to_history(url, None)
            self.set_status("无法解析视频标题，直接开始下载")

        # 使用配置文件中的 ytdlp 路径
        command = [self.ytdlp_path, url]
        
        proxy_address = None
        if self.proxy_var.get():
            proxy_address = self.proxy_entry.get()
            if not proxy_address: 
                self.log("Error: 'Use Proxy' is checked, but the proxy address is empty. Please provide a proxy or uncheck the box.")
                return
            command.extend(["--proxy", proxy_address])

        # Cookie设置
        if self.cookie_var.get():
            cookie_path = os.path.abspath('cookie.txt')
            if not os.path.exists(cookie_path):
                self.log("Error: 'Use Cookie' is checked, but cookie.txt file not found. Please click '编辑 Cookie' to create and edit the file.")
                return
            # 检查文件是否为空
            try:
                with open(cookie_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content or content.startswith('#') and len(content.split('\n')) <= 3:
                        self.log("Warning: cookie.txt appears to be empty or only contains comments. Please add your cookies.")
            except Exception as e:
                self.log(f"Error reading cookie.txt: {e}")
                return
            
            # 复制 cookie 文件到临时文件，避免 yt-dlp 修改原始文件
            try:
                temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                temp_cookie_file.close()
                shutil.copy2(cookie_path, temp_cookie_file.name)
                command.extend(["--cookies", temp_cookie_file.name])
                self.log(f"Using cookies from: {cookie_path} (copied to temp file to prevent modification)")
            except Exception as e:
                self.log(f"Error copying cookie file: {e}")
                return

        command.extend(["-U"])
        
        # Add format selection for MP4
        if self.mp4_var.get():
            command.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
            # 添加自动合并参数，确保视频和音频自动合并
            command.extend(["--merge-output-format", "mp4"])
        
        # Add format selection for MP3
        if self.mp3_var.get():
            command.extend(["--extract-audio", "--audio-format", "mp3"])
        
        command.extend(["-o", "%(title)s-%(id)s.%(ext)s"])
        
        # 使用配置文件中的下载路径（确保是 macOS 路径）
        if 'C:\\' in self.download_path or self.download_path.startswith('C:'):
            self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        command.extend(["-P", self.download_path])
        self.log(f"Files will be downloaded to: {self.download_path}")

        # macOS 下使用 Terminal.app 执行命令
        # 使用 shlex.quote 来正确转义 shell 参数（处理 zsh 的特殊字符）
        cmd_str = " ".join([shlex.quote(arg) for arg in command])
        self.log(f"Running: {cmd_str}")
        
        # 设置 SSL 证书环境变量（解决 macOS 证书验证问题）
        try:
            import certifi
            cert_path = certifi.where()
            # 在命令前添加环境变量设置
            env_cmd = f'export SSL_CERT_FILE={shlex.quote(cert_path)} && export REQUESTS_CA_BUNDLE={shlex.quote(cert_path)} && {cmd_str}'
        except ImportError:
            env_cmd = cmd_str
        
        # 使用 osascript 在 Terminal 中执行命令
        try:
            # 转义 AppleScript 中的特殊字符
            # 在 AppleScript 中，需要转义反斜杠和双引号
            escaped_cmd = env_cmd.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
            apple_script = f'tell application "Terminal" to do script "{escaped_cmd}"'
            subprocess.Popen(['osascript', '-e', apple_script])
        except Exception as e:
            self.log(f"Error starting download: {e}")
            # 如果 Terminal 方式失败，尝试直接执行（不推荐，因为可能没有终端输出）
            try:
                subprocess.Popen(command)
            except Exception as e2:
                self.log(f"Error executing command directly: {e2}")

        self.set_status("下载任务已在独立窗口中启动", duration=5000)
        self.download_button.config(state=tk.NORMAL)

    def run_yt_dlp(self, command):
        # 这个方法不再需要，因为我们直接在 Terminal 窗口中执行命令
        pass

    def enable_open_folder_button(self):
        # This method now primarily ensures the button is normal.
        # If self.download_path is None, clicking it will log a message.
        self.open_folder_button.config(state=tk.NORMAL)

    def open_download_folder(self):
        if self.download_path and os.path.isdir(self.download_path): # Check if path exists and is a directory
            try:
                # macOS 使用 open 命令打开文件夹
                subprocess.run(['open', self.download_path], check=True)
            except FileNotFoundError: # Should be caught by os.path.isdir, but as a fallback
                 self.log(f"Error: Download folder not found at {self.download_path}")
            except Exception as e:
                self.log(f"Could not open folder: {e}. Please open manually: {self.download_path}")
        elif self.download_path: # Path was set but is not a valid directory
            self.log(f"Error: Download path '{self.download_path}' is not a valid directory or does not exist.")
        else: # No download path has been set yet
            self.log("No download directory has been selected yet.")

    def show_last_downloaded_file(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            try:
                # macOS 使用 open -R 在 Finder 中显示文件
                subprocess.run(['open', '-R', self.last_downloaded_file], check=True)
            except Exception as e:
                self.log(f"无法显示文件: {e}")
        else:
            self.log("没有找到最后下载的文件")

    def clear_url(self):
        self.url_entry.delete(0, tk.END)

    def log(self, message):
        self.queue.put(message)

    def set_status(self, message, duration=3000):
        """设置状态栏信息，duration 毫秒后恢复"""
        self.status_var.set(message)
        # 取消之前的恢复任务（如果有）
        if hasattr(self, '_status_timer'):
            self.master.after_cancel(self._status_timer)
        self._status_timer = self.master.after(duration, lambda: self.status_var.set("准备就绪"))

    def on_url_change(self, *args):
        """自动删除 URL 中的参数"""
        url = self.url_var.get()
        if '?' in url:
            base_url = url.split('?')[0]
            if base_url != url:
                # 使用 after 处理以避免在 trace 回调中直接修改导致的一些界面焦点问题
                self.master.after_idle(lambda: self.url_var.set(base_url))
                self.set_status("已自动删除 URL 中的冗余参数 (?)")

    def process_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.config(state=tk.DISABLED)
                self.log_text.see(tk.END)
                self.queue.task_done()
        except queue.Empty:
            pass
        self.master.after(100, self.process_queue)

if __name__ == '__main__':
    root = ThemedTk(theme="equilux")
    root.configure(bg='#2b2b2b')  # 设置窗口背景为深黑色，菜单栏也会是黑色
    
    # 设置窗口图标（标题栏和任务栏）
    try:
        # 使用 icon.png 设置图标
        icon_image = tk.PhotoImage(file="icon.png")
        root.iconphoto(True, icon_image)  # True 表示同时设置任务栏图标
    except Exception as e:
        # macOS 不支持 iconbitmap，所以只尝试 PhotoImage
        pass
        
    gui = YtDlpGUI(root)
    root.mainloop()

