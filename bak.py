from flask import Flask, request, jsonify
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

