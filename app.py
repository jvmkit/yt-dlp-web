from flask import Flask, render_template, request, jsonify
import yt_dlp
import os
import threading
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# 存储下载任务的全局变量
download_tasks = {}

class DownloadTask:
    def __init__(self, url, options):
        self.url = url
        self.options = options
        self.status = 'pending'  # pending, downloading, paused, completed, error, cancelled
        self.progress = 0
        self.speed = 0
        self.eta = 0
        self.filename = ''
        self.title = ''
        self.error = None
        self.created_at = datetime.now()
        self.thread = None
        self.ydl = None
        self._should_stop = False
        self._should_pause = False
        self.total_bytes = 0
        self.downloaded_bytes = 0

    def to_dict(self):
        return {
            'url': self.url,
            'status': self.status,
            'progress': self.progress,
            'speed': self.speed,
            'eta': self.eta,
            'filename': self.filename,
            'title': self.title,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'total_bytes': self.total_bytes,
            'downloaded_bytes': self.downloaded_bytes
        }

    def pause(self):
        self._should_pause = True
        self.status = 'paused'

    def resume(self):
        self._should_pause = False
        self.status = 'downloading'

    def cancel(self):
        self._should_stop = True
        self.status = 'cancelled'

    def should_stop(self):
        return self._should_stop

    def should_pause(self):
        return self._should_pause

def my_hook(d):
    if d['status'] == 'downloading':
        # 计算下载进度
        task_id = d['info_dict']['id']
        if task_id in download_tasks:
            task = download_tasks[task_id]
            
            # 检查是否应该停止或暂停
            if task.should_stop():
                raise Exception('Task cancelled')
            if task.should_pause():
                raise Exception('Task paused')
                
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            
            task.downloaded_bytes = downloaded
            task.total_bytes = total
            
            if total > 0:
                task.progress = round((downloaded / total) * 100, 2)
            else:
                task.progress = 0
                
            task.speed = d.get('speed', 0)
            task.eta = d.get('eta', 0)
            task.filename = d.get('filename', '')
            task.status = 'downloading'
    elif d['status'] == 'finished':
        task_id = d['info_dict']['id']
        if task_id in download_tasks:
            task = download_tasks[task_id]
            task.status = 'completed'
            task.progress = 100

def download_video(task):
    ydl_opts = {
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'no_warnings': True,
        'progress_hooks': [my_hook]
    }
    
    ydl_opts.update(task.options)
    
    while not task.should_stop():
        try:
            if task.should_pause():
                continue
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                task.ydl = ydl
                info = ydl.extract_info(task.url, download=False)
                task.title = info.get('title', '未知标题')
                
                if task.status != 'paused':
                    ydl.download([task.url])
                    break
                    
        except Exception as e:
            if str(e) == 'Task cancelled':
                task.status = 'cancelled'
                break
            elif str(e) == 'Task paused':
                task.status = 'paused'
                continue
            else:
                task.error = str(e)
                task.status = 'error'
                print(f"下载错误: {str(e)}")
                break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/formats', methods=['POST'])
def get_formats():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': '请提供URL'}), 400

    ydl_opts = {
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    }

    proxy = request.form.get('proxy', '')
    if proxy:
        ydl_opts['proxy'] = proxy

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            format_list = []
            
            for f in formats:
                format_info = {
                    'format_id': f.get('format_id', 'N/A'),
                    'ext': f.get('ext', 'N/A'),
                    'resolution': f.get('resolution', 'N/A'),
                    'filesize': 'N/A' if not f.get('filesize') else f'{f.get("filesize")/1024/1024:.2f}MB',
                    'vcodec': f.get('vcodec', 'none'),
                    'acodec': f.get('acodec', 'none')
                }
                format_list.append(format_info)
            
            return jsonify({
                'formats': format_list,
                'title': info.get('title', '未知标题')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def start_download():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': '请提供URL'}), 400
        
    format_type = request.form.get('format', 'best')
    selected_format = request.form.get('selected_format')
    
    options = {
        'proxy': request.form.get('proxy', ''),
        'merge_output_format': 'mp4'
    }
    
    # 处理下载路径
    download_path = request.form.get('download_path')
    if download_path and os.path.isdir(download_path):
        options['outtmpl'] = os.path.join(download_path, '%(title)s.%(ext)s')
    else:
        options['outtmpl'] = '%(title)s.%(ext)s'
    
    # 处理cookies文件
    cookies_file = request.files.get('cookies')
    if cookies_file:
        # 保存cookies文件到临时目录
        cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_cookies.txt')
        cookies_file.save(cookies_path)
        if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
            options['cookies'] = cookies_path
        else:
            return jsonify({'error': 'Cookies文件保存失败或文件为空'}), 400
    
    if format_type == 'bestvideo+bestaudio/best':
        options['format'] = 'bestvideo+bestaudio/best'
    elif format_type == 'bestvideo,bestaudio':
        options['format'] = 'bestvideo,bestaudio'
        options.pop('merge_output_format', None)
    elif format_type == 'worstvideo+worstaudio':
        options['format'] = 'worstvideo+worstaudio'
    elif format_type == 'custom' and selected_format:
        options['format'] = selected_format
    else:
        options['format'] = 'best'
    
    # 创建新的下载任务
    with yt_dlp.YoutubeDL({
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'proxy': request.form.get('proxy', '')
    }) as ydl:
        info = ydl.extract_info(url, download=False)
        task_id = info['id']
        
        if task_id not in download_tasks:
            task = DownloadTask(url, options)
            download_tasks[task_id] = task
            task.thread = threading.Thread(target=download_video, args=(task,))
            task.thread.start()
            return jsonify({'task_id': task_id, 'message': '下载已开始'})
        else:
            return jsonify({'error': '该视频已在下载队列中'}), 400

@app.route('/tasks')
def get_tasks():
    return jsonify({
        'tasks': {task_id: task.to_dict() for task_id, task in download_tasks.items()}
    })

@app.route('/task/<task_id>/pause', methods=['POST'])
def pause_task(task_id):
    if task_id in download_tasks:
        task = download_tasks[task_id]
        if task.status == 'downloading':
            task.pause()
            return jsonify({'message': '下载已暂停'})
    return jsonify({'error': '任务不存在或无法暂停'}), 404

@app.route('/task/<task_id>/resume', methods=['POST'])
def resume_task(task_id):
    if task_id in download_tasks:
        task = download_tasks[task_id]
        if task.status == 'paused':
            task.resume()
            task.thread = threading.Thread(target=download_video, args=(task,))
            task.thread.start()
            return jsonify({'message': '下载已恢复'})
    return jsonify({'error': '任务不存在或无法恢复'}), 404

@app.route('/task/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    if task_id in download_tasks:
        task = download_tasks[task_id]
        task.cancel()
        return jsonify({'message': '下载已取消'})
    return jsonify({'error': '任务不存在'}), 404

@app.route('/task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    if task_id in download_tasks:
        task = download_tasks[task_id]
        if task.status in ['completed', 'error', 'cancelled']:
            del download_tasks[task_id]
            return jsonify({'message': '任务已删除'})
        return jsonify({'error': '只能删除已完成、出错或已取消的任务'}), 400
    return jsonify({'error': '任务不存在'}), 404

@app.route('/select_directory', methods=['POST'])
def select_directory():
    try:
        directory = request.form.get('directory')
        if not directory:
            return jsonify({'error': '请提供目录路径'}), 400
            
        # 检查目录是否存在且可写
        if os.path.isdir(directory) and os.access(directory, os.W_OK):
            return jsonify({'path': directory, 'valid': True})
        else:
            return jsonify({'error': '目录不存在或无写入权限', 'valid': False}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, port=5000)