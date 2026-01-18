<img width="301" height="301" alt="icon" src="https://github.com/user-attachments/assets/9d62974d-0f93-4269-9a7e-518cb811a3e1" />

# yt-dlp GUI

一个简单的yt-dlp图形界面工具。(测试支持 youtube tiktok bilibili）

安装 yt-dlp (程序依赖) : https://github.com/yt-dlp/yt-dlp/wiki/Installation  
支持下载视频网站列表 : https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md?plain=1

![image](https://github.com/user-attachments/assets/abe642ae-b826-4cc1-947e-cf06ee7a1e55)

## FAQ
查看[快速答疑指南](https://github.com/cornradio/ytdlpgui/blob/main/how-to-use-cookie.md)

## 功能

- 下载视频
- 支持代理设置
- 支持使用cookie下载
- 支持MP4格式下载
- 简洁主题界面

## 使用方法

1. 输入视频URL
2. 选择是否需要代理
3. 选择是否需要使用cookie
4. 点击Download开始下载

## 使用方法 formac
mac版本需要从源代码使用,建议创建alias快捷启动
```
alias ytdlpgui="cd /Users/kasusa/Documents/GitHub/ytdlpgui;source .venv/bin/activate;python ytdlpgui.mac.py"
```
哦对了使用之前还要安装好ffmpeg和yt-dlp,我想这对一个mac用户来说都很简单.

```
安装包管理器 (Homebrew): 
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

一键安装依赖: 
brew install ffmpeg yt-dlp
```

## 打包

```bash
# 清理临时文件
clear.bat

# 打包程序
build.bat
```

## python依赖
- Python 3.x
- ttkthemes
- yt-dlp

## 其他下载
ytdlpgui
https://github.com/cornradio/ytdlpgui/releases/

ytdlpgui（支持cookie的版本）
https://github.com/cornradio/ytdlpgui/issues/2#issuecomment-3329523840

依赖下载（exe)  
ytdlp.exe https://github.com/yt-dlp/yt-dlp/releases/tag/2025.05.22  
ffmpeg.exe https://github.com/ffbinaries/ffbinaries-prebuilt/releases  

完整版 ytdlpgui + ffmpeg + ytdlp 压缩包直接下载
https://kasusa.lanzoul.com/i4gW92yf241e  



## 更新日志

### 2026-01-05

-  下载按钮改成绿色
-  url 自动删除参数
-  允许清空历史记录
-  增加状态栏和修改程序 UI 布局