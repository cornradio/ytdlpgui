import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import subprocess
import queue
import os
from ttkthemes import ThemedTk
import ctypes
import webbrowser
import configparser

# 设置DPI感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

class YtDlpGUI:
    def __init__(self, master):
        self.master = master
        master.title("yt-dlp GUI")
        
        # 设置主题
        self.style = ttk.Style()
        self.style.theme_use('equilux')  # 使用equilux主题作为基础
        
        # 配置主题颜色
        self.style.configure('TFrame', background='#464646')
        self.style.configure('TLabel', background='#464646', foreground='white', font=('Segoe UI', 10))
        self.style.configure('TButton', background='#2b2b2b', foreground='white', font=('Segoe UI', 10))
        self.style.configure('TCheckbutton', background='#464646', foreground='white', font=('Segoe UI', 10))
        self.style.configure('TEntry', fieldbackground='#2b2b2b', foreground='white', font=('Segoe UI', 10))
        
        # 配置按钮样式
        self.style.map('TButton',
            background=[('active', '#404040'), ('disabled', '#2b2b2b')],
            foreground=[('disabled', '#666666')])
        
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
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 读取配置文件
        self.config = configparser.ConfigParser()
        try:
            self.config.read('settings.ini')
            self.download_path = self.config.get('Settings', 'download_path')
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
        self.url_label.grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
        self.url_entry = ttk.Entry(self.main_frame, width=60)
        self.url_entry.grid(row=0, column=1, padx=8, pady=8, sticky=tk.W + tk.E)

        # 代理设置
        self.proxy_var = tk.BooleanVar()
        self.use_proxy_checkbutton = ttk.Checkbutton(self.main_frame, text="Use Proxy (e.g., 127.0.0.1:7890)",
                                                     variable=self.proxy_var, command=self.toggle_proxy_entry)
        self.use_proxy_checkbutton.grid(row=1, column=0, padx=8, pady=8, sticky=tk.W)

        self.proxy_entry = ttk.Entry(self.main_frame, width=60, state=tk.DISABLED)
        self.proxy_entry.grid(row=1, column=1, padx=8, pady=8, sticky=tk.W + tk.E)

        # MP4格式选项
        self.mp4_var = tk.BooleanVar()
        self.mp4_checkbutton = ttk.Checkbutton(self.main_frame, text="Download as MP4",
                                             variable=self.mp4_var)
        self.mp4_checkbutton.grid(row=2, column=0, padx=8, pady=8, sticky=tk.W)

        # MP3格式选项
        self.mp3_var = tk.BooleanVar()
        self.mp3_checkbutton = ttk.Checkbutton(self.main_frame, text="Download as MP3",
                                             variable=self.mp3_var)
        self.mp3_checkbutton.grid(row=2, column=1, padx=8, pady=8, sticky=tk.W)

        # 按钮区域
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.download_button = ttk.Button(self.button_frame, text="Download", command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=8)

        self.clear_button = ttk.Button(self.button_frame, text="Clear URL", command=self.clear_url)
        self.clear_button.pack(side=tk.LEFT, padx=8)

        # 日志区域
        self.log_frame = ttk.Frame(self.main_frame)
        self.log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = scrolledtext.ScrolledText(self.log_frame, width=80, height=25, 
                                                bg='#2b2b2b', fg='white', insertbackground='white',
                                                font=('Consolas', 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        # 底部按钮区域
        self.bottom_frame = ttk.Frame(self.main_frame)
        self.bottom_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        # 添加设置按钮
        self.settings_button = ttk.Button(self.bottom_frame, text="Settings ⚙️", command=self.open_settings)
        self.settings_button.pack(side=tk.LEFT, padx=8)

        # GitHub Repository Button
        self.github_button = ttk.Button(self.bottom_frame, text="GitHub", command=self.open_github_repo)
        self.github_button.pack(side=tk.LEFT, padx=8)

        # get ytdlp
        self.get_ytdlp_button = ttk.Button(self.bottom_frame, text="Get yt-dlp", command=self.get_ytdlp)
        self.get_ytdlp_button.pack(side=tk.LEFT, padx=8)

        self.open_folder_button = ttk.Button(self.bottom_frame, text="Open Folder 📂", command=self.open_download_folder, state=tk.NORMAL)
        self.open_folder_button.pack(side=tk.LEFT, padx=8)

        # 配置网格权重
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=1)

        # 设置窗口最小尺寸
        master.update_idletasks()
        master.minsize(500, 400)

        self.queue = queue.Queue()
        self.master.after(100, self.process_queue)

    def open_github_repo(self):
        webbrowser.open("https://github.com/cornradio/ytdlpgui")

    def get_ytdlp(self):
        webbrowser.open('https://github.com/yt-dlp/yt-dlp/wiki/Installation')

    def open_settings(self):
        """打开 settings.ini 文件"""
        settings_path = os.path.abspath('settings.ini')
        if os.path.exists(settings_path):
            try:
                if os.name == 'nt':  # Windows
                    os.system(f'notepad "{settings_path}"')
                elif os.uname().sysname == 'Darwin':  # macOS
                    subprocess.run(['open', '-a', 'TextEdit', settings_path])
                else:  # Linux
                    subprocess.run(['xdg-open', settings_path])
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
            USERNAME = os.getlogin()
            self.config['Settings'] = {
                'download_path': f'C:\\Users\\{USERNAME}\\Downloads',
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

    def start_download(self):
        url = self.url_entry.get()
        
        if not url:
            self.log("Error: Please enter a URL.")
            return

        # 使用配置文件中的 ytdlp 路径
        command = [self.ytdlp_path, "'" + url+"'"]
        
        proxy_address = None
        if self.proxy_var.get():
            proxy_address = self.proxy_entry.get()
            if not proxy_address: 
                self.log("Error: 'Use Proxy' is checked, but the proxy address is empty. Please provide a proxy or uncheck the box.")
                return
            command.extend(["--proxy", proxy_address])

        command.extend(["-U"])
        
        # Add format selection for MP4
        if self.mp4_var.get():
            command.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
        
        # Add format selection for MP3
        if self.mp3_var.get():
            command.extend(["--extract-audio", "--audio-format", "mp3"])
        
        command.extend(["-o", "\'%(title)s-%(id)s.%(ext)s\'"])
        
        # 使用配置文件中的下载路径
        command.extend(["-P", self.download_path])
        self.log(f"Files will be downloaded to: {self.download_path}")

        # 构建完整的命令字符串
        cmd_str = " ".join(command)
        self.log(f"Running: {cmd_str}")

        # 在Windows下使用cmd.exe执行命令
        if os.name == 'nt':
            # 使用cmd /k 来保持窗口打开
            full_cmd = f'cmd /k "{cmd_str}"'
            subprocess.Popen(full_cmd, shell=True)
        else:
            # 在Linux/Mac下使用终端
            if os.uname().sysname == 'Darwin':
                subprocess.Popen(['osascript', '-e', f'tell app "Terminal" to do script "{cmd_str}"'])
            else:
                subprocess.Popen(['x-terminal-emulator', '-e', cmd_str])

        self.download_button.config(state=tk.NORMAL)

    def run_yt_dlp(self, command):
        # 这个方法不再需要，因为我们直接在CMD窗口中执行命令
        pass

    def enable_open_folder_button(self):
        # This method now primarily ensures the button is normal.
        # If self.download_path is None, clicking it will log a message.
        self.open_folder_button.config(state=tk.NORMAL)

    def open_download_folder(self):
        if self.download_path and os.path.isdir(self.download_path): # Check if path exists and is a directory
            try:
                if os.name == 'nt': 
                    os.startfile(os.path.realpath(self.download_path))
                elif os.uname().sysname == 'Darwin': 
                    subprocess.run(['open', self.download_path], check=True)
                else: 
                    subprocess.run(['xdg-open', self.download_path], check=True)
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
                if os.name == 'nt':
                    # Windows系统下使用explorer选中文件
                    subprocess.run(['explorer', '/select,', self.last_downloaded_file], check=True)
                elif os.uname().sysname == 'Darwin':
                    # macOS系统下使用open命令
                    subprocess.run(['open', '-R', self.last_downloaded_file], check=True)
                else:
                    # Linux系统下使用xdg-open
                    subprocess.run(['xdg-open', os.path.dirname(self.last_downloaded_file)], check=True)
            except Exception as e:
                self.log(f"无法显示文件: {e}")
        else:
            self.log("没有找到最后下载的文件")

    def clear_url(self):
        self.url_entry.delete(0, tk.END)

    def log(self, message):
        self.queue.put(message)

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
    root.configure(bg='#464646')
    
    # 设置窗口图标（如果有的话）
    try:
        root.iconbitmap("icon.ico")  # 如果有图标文件的话
    except:
        pass
        
    gui = YtDlpGUI(root)
    root.mainloop()
