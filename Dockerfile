# 使用Python 3.10作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
COPY app.py .
COPY templates/ ./templates/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建下载目录
RUN mkdir -p /app/downloads

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DOWNLOAD_PATH=/app/downloads

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "app.py"]