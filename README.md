# yt-dlp GUI

一个简单的yt-dlp图形界面工具。

安装 yt-dlp (程序本体) : https://github.com/yt-dlp/yt-dlp/wiki/Installation
yt-dlp 支持下载视频网站列表 : https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md?plain=1

## 功能

- 下载视频
- 支持代理设置
- 支持MP4格式下载
- 黑色主题界面

## 使用方法

1. 输入视频URL
2. 选择是否需要代理
3. 选择是否需要MP4格式
4. 点击Download开始下载

## 打包

```bash
# 清理临时文件
clear.bat

# 打包程序
build.bat
```

## 依赖

- Python 3.x
- ttkthemes
- yt-dlp 
