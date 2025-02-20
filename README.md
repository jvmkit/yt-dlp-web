# YT-DLP Web下载器

一个基于yt-dlp的Web界面下载工具，支持在线下载视频，提供友好的用户界面和丰富的功能选项。

## 功能特点

- 🎯 支持多种视频格式下载
- 🚀 支持暂停/恢复/取消下载
- 📊 实时显示下载进度和速度
- 🔧 自定义下载格式和质量
- 🌐 支持设置代理
- 🍪 支持导入Cookies文件
- 📁 自定义下载目录
- 🎨 美观的Web界面

## 安装说明

### 方式一：直接运行

1. 确保已安装Python 3.10或更高版本
2. 安装ffmpeg（用于视频处理）
3. 克隆项目并安装依赖：

```bash
git clone <repository-url>
cd yt-dlp
pip install -r requirements.txt
```

4. 运行应用：

```bash
python app.py
```

5. 访问 http://localhost:5000 开始使用

### 方式二：Docker部署

1. 构建Docker镜像：

```bash
docker build -t yt-dlp-web .
```

2. 运行容器：

```bash
docker run -d -p 5000:5000 -v /your/download/path:/app/downloads yt-dlp-web
```

## 使用说明

1. 在主页输入要下载的视频URL
2. 可选配置：
   - 选择下载格式和质量
   - 设置代理服务器
   - 上传Cookies文件（用于需要登录的网站）
   - 选择下载保存目录
3. 点击下载按钮开始下载
4. 在下载列表中查看进度，可以：
   - 暂停/恢复下载
   - 取消下载
   - 删除已完成的任务

## 环境变量

- `PYTHONUNBUFFERED=1`：Python输出不缓冲
- `DOWNLOAD_PATH=/app/downloads`：默认下载目录

## 常见问题

1. **下载速度慢怎么办？**
   - 尝试设置代理服务器
   - 检查网络连接
   - 选择较低质量的格式

2. **无法下载需要登录的视频？**
   - 导出浏览器的Cookies文件并上传
   - 确保Cookies文件格式正确

3. **下载的视频没有声音？**
   - 选择`bestvideo+bestaudio/best`格式
   - 确保ffmpeg已正确安装

## 技术栈

- 后端：Flask + yt-dlp
- 前端：Bootstrap 5
- 容器化：Docker

## 注意事项

- 请遵守相关法律法规和视频平台的使用条款
- 建议使用代理服务器以提高下载稳定性
- 大文件下载可能需要较长时间，请耐心等待

## 许可证

本项目基于MIT许可证开源