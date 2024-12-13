from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import socket
import qrcode
import shutil
import subprocess
import re

app = Flask(__name__)
socketio = SocketIO(app)

# 存储提交的内容
submitted_contents = []


@app.route('/')
def home():
    return render_template_string('''  
    <!DOCTYPE html>
    <html>
    <head>
        <title>文本传输服务</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f4f4f4;
            }
            #editor {
                border: 1px solid #ccc;
                height: 300px;
                padding: 10px;
                overflow-y: auto;
                background-color: #fff;
                font-size: 16px;
                resize: none; /* 允许用户调整大小 */
            }
            #toolbar {
                margin-bottom: 5px;
            }
            button {
                margin-right: 5px;
                padding: 5px 10px;
                font-size: 14px; /* 增加按钮的字体大小以便更容易点击 */
            }
            .submitted-item {
                border: 1px solid #ddd;
                padding: 10px;
                margin: 10px 0;
                background-color: #fff;
                position: relative; /* 使按钮相对于这个元素定位 */
                max-width: 100%; /* 最大宽度为100% */
                overflow-wrap: break-word; /* 超出内容换行 */
            }
            .copy-button {
                position: absolute;
                top: 5px;
                right: 5px;
                display: none; /* 初始隐藏 */
                background-color: #808080; /* 灰色背景 */
                color: white; /* 白色文字 */
                border: none;
                padding: 5px;
                cursor: pointer;
            }
            .submitted-item:hover .copy-button {
                display: block; /* 鼠标悬停时显示 */
            }

            /* 媒体查询：针对手机端的适配 */
            @media (max-width: 600px) {
                body {
                    padding: 10px;
                }
                #editor {
                    height: 200px; /* 手机端减少高度 */
                    font-size: 14px; /* 手机端减小字体 */
                }
                button {
                    padding: 4px 8px; /* 手机端减小按钮大小 */
                    font-size: 12px; /* 减小按钮字体 */
                }
                .submitted-item {
                    font-size: 14px;  /* 提交内容适配 */
                    padding: 8px; /* 增加内边距，避免贴边 */
                }
            }
        </style>
    </head>
    <body>
        <h1>文本传输服务</h1>
        <div id="toolbar">
            <button onclick="clearEditor()">清空内容</button>
            <button onclick="addLink()">添加链接</button>
            <button onclick="addImage()">添加图片</button>
        </div>
        <div id="editor" contenteditable="true"></div>
        <br>
        <button id="submit-button">提交内容</button>
        <p id="response"></p>

        <h2>提交的内容</h2>
        <div id="submitted-content"></div>

        <script>
            const socket = io();

            // 提交按钮的点击事件
            document.getElementById('submit-button').addEventListener('click', function() {
                const content = document.getElementById('editor').innerHTML.trim(); // 获取内容并去除前后空白
                
                // 检查内容是否为空
                if (content === '') {
                    alert('内容不能为空！'); // 提示用户
                    return; // 阻止提交
                }

                // 发送提交的内容到服务器
                socket.emit('submit_content', { content: content });
                
                // 清空文本框
                document.getElementById('editor').innerHTML = ''; // 清空编辑器内容
            });

            // 处理服务器推送的内容
            socket.on('update_content', function(data) {
                addToSubmittedContent(data.content);
            });

            // 处理连接时获取已经提交的内容
            socket.on('previous_contents', function(contents) {
                contents.forEach(content => {
                    addToSubmittedContent(content);
                });
            });

            function addToSubmittedContent(content) {
                const submittedContentDiv = document.getElementById('submitted-content');
                const div = document.createElement('div');
                div.className = 'submitted-item';

                // 创建复制按钮
                const copyButton = document.createElement('button');
                copyButton.className = 'copy-button';
                copyButton.innerText = '复制';
                copyButton.onclick = function() {
                    copyFormattedContent(content); // 调用优化后的复制方法
                };

                div.innerHTML = content; // 将提交的内容放入div
                div.appendChild(copyButton); // 将复制按钮添加到div中
                submittedContentDiv.insertBefore(div, submittedContentDiv.firstChild); // 新内容放在顶部
            }

            // 优化后的复制方法
            function copyFormattedContent(htmlContent) {
                const isMobile = /Android|iPhone|iPad|iPod|Windows Phone/i.test(navigator.userAgent); // 检测是否为移动端

                if (!isMobile) {
                    // 非移动端：直接使用 Clipboard API 复制 HTML
                    if (navigator.clipboard && navigator.clipboard.write) {
                        const blob = new Blob([htmlContent], { type: 'text/html' });
                        const data = [new ClipboardItem({ 'text/html': blob })];
                        navigator.clipboard.write(data).then(() => {
                            alert('内容已复制到剪贴板！');
                        }).catch(err => {
                            console.error('复制失败:', err);
                            alert('复制失败，请手动复制内容！');
                        });
                        return;
                    }
                }

                // 移动端：使用隐藏 DOM 渲染格式化内容并复制
                const tempDiv = document.createElement('div');
                tempDiv.style.position = 'absolute';
                tempDiv.style.left = '-9999px';
                tempDiv.style.whiteSpace = 'pre-wrap'; // 保留换行
                tempDiv.innerHTML = htmlContent; // 渲染 HTML 到隐藏元素中
                document.body.appendChild(tempDiv);

                const range = document.createRange();
                range.selectNodeContents(tempDiv);

                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);

                try {
                    const success = document.execCommand('copy');
                    if (success) {
                        alert('内容已复制到剪贴板！');
                    } else {
                        alert('复制失败，请手动复制内容！');
                    }
                } catch (err) {
                    console.error('复制失败:', err);
                    alert('复制失败，请手动复制内容！');
                }

                // 移除临时元素
                selection.removeAllRanges();
                document.body.removeChild(tempDiv);
            }

            // 添加链接
            function addLink() {
                const url = prompt('输入链接地址');
                if (url) {
                    const editor = document.getElementById('editor');
                    editor.focus(); // 将焦点移到编辑器
                    document.execCommand('createLink', false, url); // 直接在光标处插入链接
                }
            }

            // 添加图片
            function addImage() {
                const imgUrl = prompt('输入图片地址');
                if (imgUrl) {
                    const editor = document.getElementById('editor');
                    editor.focus(); // 将焦点移到编辑器
                    document.execCommand('insertImage', false, imgUrl); // 直接在光标处插入图片
                }
            }

            // 清空编辑器内容的函数
            function clearEditor() {
                document.getElementById('editor').innerHTML = ''; // 清空编辑器内容
            }
        </script>
    </body>
    </html>
    ''')


@socketio.on('connect')
def handle_connect():
    # 当新用户连接时，发送之前提交的内容
    emit('previous_contents', submitted_contents)


@socketio.on('submit_content')
def handle_submit_content(data):
    content = data['content']
    submitted_contents.append(content)
    # 广播所有连接的客户端，推送最新内容
    emit('update_content', {'content': content}, broadcast=True)


def get_local_ip():
    """
    获取当前机器的局域网IP地址。
    """
    try:
        # 创建一个UDP套接字
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # 连接到任意外部地址，不会真的发出数据
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return 0


def get_ip_from_ipconfig():
    try:
        # 执行 ipconfig 命令
        result = subprocess.run(["ipconfig"], capture_output=True, text=True, shell=True)
        output = result.stdout

        # 按段分割每个适配器信息
        adapter_blocks = re.split(r"\n(?=\S+适配器 )", output)

        # 正则匹配适配器名称和 IPv4 地址
        ipv4_pattern = re.compile(r"^(?P<interface>.*?适配器 .*?):.*?IPv4 地址.*?:\s*(?P<ip>[\d.]+)", re.DOTALL)

        matches = []
        for block in adapter_blocks:
            match = ipv4_pattern.search(block)
            if match:
                matches.append((match.group("interface"), match.group("ip")))

        # 优先级列表
        interface_priority = ["无线局域网适配器", "以太网"]

        # 按优先级返回第一个匹配结果
        for preferred in interface_priority:
            for interface, ip in matches:
                if preferred in interface:
                    return ip

        return 0
    except Exception as e:
        return 0


def generate_qr_terminal(url):
    # 获取当前终端的宽度
    terminal_width = shutil.get_terminal_size().columns

    max_size = terminal_width // 2
    box_size = max(1, max_size)
    border = 2

    # 创建二维码对象
    qr = qrcode.QRCode(
        version=1,  # 控制二维码大小的版本，1是最小的
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # 错误修正级别
        box_size=box_size,  # 每个方格的大小
        border=border,  # 二维码边框的大小
    )

    qr.add_data(url)
    qr.make(fit=True)

    # 将二维码绘制成 ASCII 字符
    # qr.print_ascii(invert=True)

    # 获取二维码的矩阵
    qr_matrix = qr.get_matrix()

    # 选择合适的输出字符：'█' 、 '■'、 '▆'、 '▇'
    char = '█'

    # 输出二维码，使用选择的字符
    for row in qr_matrix:
        print(' '.join(char if cell else ' ' for cell in row))


if __name__ == '__main__':
    try:
        port = 9000
        # ip = get_local_ip()
        ip = get_ip_from_ipconfig()

        if ip != 0:
            address = f"http://{ip}:{port}"

            print("请扫描以下二维码或访问服务地址：")
            generate_qr_terminal(address)

            print(f"服务地址: {address}")

        socketio.run(app, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n服务已关闭。")
