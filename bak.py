from flask import Flask, request, jsonify, render_template_string, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os
import subprocess

app = Flask(__name__)
CORS(app)

SAVE_DIR = "/root/project/haungyuyang/chenxi/Polaris/data/"
MAIN_DIR = "/root/project/haungyuyang/chenxi/Polaris/main.py"
INPUT_FILE = os.path.join(SAVE_DIR, "input.txt")
OUTPUT_FILE = os.path.join(SAVE_DIR, "recover.txt")

@app.route('/')
def index():
    """根路径路由，返回主页"""
    try:
        return send_from_directory('.', 'index.html')
    except FileNotFoundError:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>瞒天过网 智隐于行</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 50px; text-align: center; }
                .container { max-width: 600px; margin: 0 auto; }
                .btn { display: inline-block; padding: 10px 20px; margin: 10px; 
                      background: #007bff; color: white; text-decoration: none; 
                      border-radius: 5px; }
                .btn:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>瞒天过网 智隐于行</h1>
                <h2>面向大语言模型的隐蔽通信系统</h2>
                <p>Flask后端服务已启动</p>
                <a href="send.html" class="btn">发送信息</a>
                <a href="receive.html" class="btn">接收信息</a>
                <hr>
                <p>API端点: <code>/process</code> (POST)</p>
                <p>支持的操作: send, receive</p>
            </div>
        </body>
        </html>
        '''

@app.route('/<path:filename>')
def serve_static(filename):
    """为静态文件提供服务"""
    try:
        return send_from_directory('.', filename)
    except FileNotFoundError:
        return f"文件 {filename} 未找到", 404

@app.route('/process', methods=['POST'])
def processtext():
    try:
        if 'userId' not in request.form or not request.form['userId'].strip():
            return jsonify({'error': 'User ID is required'}), 400
        userid = request.form['userId']
        processingtype = request.form.get('processingType', 'r')
        workmode = request.form.get('workmode', '').lower()

        if workmode == 'send':
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400

            file = request.files['file']


            os.makedirs(os.path.dirname(INPUT_FILE), exist_ok=True)

            file_content = file.read()
            with open(INPUT_FILE, 'wb') as f:
                f.write(file_content)
            #print(f"文件内容已写入 {INPUT_FILE}")

            try:
                subprocess.run(['python', MAIN_DIR, '--mode', 'send', '--file', INPUT_FILE, '--id', userid, '--no-confirm'], check=True)
            except subprocess.CalledProcessError as e:
                print(f"无法启动main.py: {e}")
                return jsonify({
                    'error': f"无法启动main.py: {e}",
                    'success': False
                }), 500

            return jsonify({
                'success': True,
                'userId': userid,
                'fileLength': len(file_content),
                'processedText': "发送成功",  
                'message': '隐写载体发送完成'
            })
        elif workmode == 'receive':
            try:
                subprocess.run(['python', MAIN_DIR, '--mode', 'receive', '--file', OUTPUT_FILE, '--id', userid, '--no-confirm'], check=True)
            except subprocess.CalledProcessError as e:
                print(f"无法启动main.py: {e}")
                return jsonify({
                    'error': f"无法启动main.py: {e}",
                    'success': False
                }), 500
            
            with open(OUTPUT_FILE, 'r') as f:
                filetext=f.read()

            return jsonify({
                'success': True,
                'userId': userid,
                'fileLength': filetext,
                'processedText': "接收成功",  
                'message': '隐写载体接收完成'
            })
        else:
            return jsonify({
                'error': 'Invalid 1 specified',
                'success': False
            }), 400

    except subprocess.CalledProcessError as e:
        print(f"无法启动1.py: {e}")
        return jsonify({
            'error': f"无法启动1.py: {e}",
            'success': False
        }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

