from dotenv import load_dotenv
load_dotenv()
import os
import subprocess
import shutil
import json
import argparse  # 新增导入 argparse 模块

class hist_obj:
    chunk_i: int
    chunk_nums: int
    curr_id: list[int]
    prev_id: list[int]

    def __init__(self, chunk_i:int, chunk_nums:int, curr_id:list[int], prev_id:list[int]):
        self.chunk_i = chunk_i
        self.chunk_nums = chunk_nums
        self.curr_id = curr_id
        self.prev_id = prev_id
    
    def to_dict(self):
        return {
            "chunk_i": self.chunk_i,
            "chunk_nums": self.chunk_nums,
            "curr_id": self.curr_id,
            "prev_id": self.prev_id
        }

class hist_recv_obj:
    prev_id: list[int]
    next_id: list[int]

    def __init__(self, prev_id:list[int], next_id:list[int]):
        self.prev_id = prev_id
        self.next_id = next_id
    
    def to_dict(self):
        return {
            "prev_id": self.prev_id,
            "next_id": self.next_id
        }

# 自定义JSON编码器
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, 'to_dict'):
            return o.to_dict()
        return super().default(o)

data_dir = ""
project_dir = ""
work_mode = ""

# 环境变量设置
def set_env():
    global data_dir, project_dir
    # DATA_DIR为相对当前文件的data文件夹，不存在则创建
    data_dir= os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    os.environ["DATA_DIR"] = data_dir
    # PROJECT_DIR为当前文件所在目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["PROJECT_DIR"] = project_dir

set_env()

# 输入模块
def parse_input():
    global work_mode
    
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="Polaris 数据传输工具")
    parser.add_argument("--mode", choices=["send", "receive", "continue"], required=True, help="工作模式: send(发送), receive(接收), continue(继续发送)")
    parser.add_argument("--id", required=False, help="发送目标ID，格式为 帖子编号/楼层编号")
    parser.add_argument("--file", required=False, help="输入或输出文件路径（绝对路径）")
    parser.add_argument("--no-confirm", action='store_true', help="跳过确认提示，直接执行操作")
    
    # 解析命令行参数
    args = parser.parse_args()
    work_mode = args.mode
    
    # 将 id 处理封装为函数
    def process_id(id):
        # 使用列表推导式，将id以"/"分割
        result = [i for i in id.split("/") if i]
        assert len(result) == 2, "ID格式错误，请使用'/''分割"
        assert all(i.isdigit() for i in result), "ID格式错误，请使用数字"
        return result
    
    input_obj = {}
    input_obj["no_confirm"] = args.no_confirm
    
    # 处理不同模式的参数
    if work_mode == "send":
        assert args.id is not None, "发送模式需要指定ID"
        assert args.file is not None, "发送模式需要指定输入文件"
        input_obj["id"] = process_id(args.id)
        input_file = args.file
        assert(os.path.exists(input_file)), f"隐写文件不存在：{input_file}"
        input_obj["input_file"] = input_file
        
    elif work_mode == "receive":
        assert args.id is not None, "接收模式需要指定ID"
        assert args.file is not None, "接收模式需要指定输出文件"
        input_obj["id"] = process_id(args.id)
        output_file = args.file
        input_obj["output_file"] = output_file
        
    elif work_mode == "continue":
        # 检查是否存在历史记录文件
        hist_file = os.path.join(data_dir, "hist.json")
        if not os.path.exists(hist_file):
            print("历史记录文件不存在，请先发送数据。")
            exit(1)
    
    return input_obj

# 压缩模块
def llmzip_set_env():
    llama_folder = os.getenv("LLAMA_FOLDER","")
    llmzip_folder = os.path.join(project_dir, "LLMzip")
    compression_folder = os.path.join(data_dir, "compression")
    os.makedirs(compression_folder, exist_ok=True)
    compressed_file_name = os.path.join(compression_folder, "LLMzip_511_AC.txt")
    return llama_folder, llmzip_folder, compression_folder, compressed_file_name

def compress_file(input_file, output_file):
    llama_folder, llmzip_folder, compression_folder, compressed_file_name = llmzip_set_env()
    try:
        env=os.environ.copy()
        result=subprocess.run(["torchrun", "--nproc_per_node", "1" ,"LLMzip_run.py", "--ckpt_dir", llama_folder, "--tokenizer_path", os.path.join(llama_folder,"tokenizer.model"), "--win_len", "511", "--text_file", input_file, "--compression_folder", compression_folder, "--encode_decode", "0"], check=True, text=True, cwd=llmzip_folder, env=env)
    except subprocess.CalledProcessError as e:
        print(f"压缩失败：{e}")
        exit(1)
    with open(compression_folder+"/LLMzip_511_metrics.json") as metrics_file:
        total_length = json.load(metrics_file)['$N_T$'][0]
    total_length= int(total_length)

    # 先将 total_length 写入 output_file，占用 4 个字节，用前导0填充
    with open(output_file, 'wb') as out_f:
        out_f.write(total_length.to_bytes(4, byteorder='big'))
        # 再写入压缩文件内容
        with open(compressed_file_name, 'rb') as in_f:
            out_f.write(in_f.read())
    # 删除compression_folder，然后重新创建空文件夹
    shutil.rmtree(compression_folder)
    os.makedirs(compression_folder, exist_ok=True)

# 解压缩模块
def decompress_file(input_file, output_file):
    llama_folder, llmzip_folder, compression_folder, compressed_file_name = llmzip_set_env()
    # 从输入文件中读取前4字节作为total_length，将剩余内容写入compressed_file_name
    with open(input_file, 'rb') as in_f:
        total_length = int.from_bytes(in_f.read(4), byteorder='big')
        with open(compressed_file_name, 'wb') as out_f:
            out_f.write(in_f.read())
    
    # 使用从文件中读取的total_length
    try:
        env = os.environ.copy()
        result=subprocess.run(["torchrun", "--nproc_per_node", "1", "LLMzip_run.py", "--ckpt_dir", llama_folder, "--tokenizer_path", os.path.join(llama_folder, "tokenizer.model"), "--win_len", "511", "--compression_folder", compression_folder, "--encode_decode", "1", "--save_file", output_file, "--verify_save_decoded", "0", "--total_length", str(total_length)], check=True, text=True, cwd=os.path.join(project_dir, "LLMzip"), env=env)
    except subprocess.CalledProcessError as e:
        print(f"解压缩失败：{e}")
        exit(1)
    # 删除compression_folder，然后重新创建空文件夹
    shutil.rmtree(compression_folder)
    os.makedirs(compression_folder, exist_ok=True)

# 分组模块
def split_file(input_file, output_dir, chunk_size=64):
    os.makedirs(output_dir, exist_ok=True)
    with open(input_file, 'rb') as in_f:
        chunk = in_f.read(chunk_size)
        i = 0
        while chunk:
            with open(os.path.join(output_dir, f"chunk_{i}.bin"), 'wb') as out_f:
                out_f.write(chunk)
            i += 1
            chunk = in_f.read(chunk_size)
    return i

# 分组发送历史读取
hist_file = os.path.join(data_dir, "hist.json")
def hist_read() -> hist_obj:
    with open(hist_file, 'r', encoding='utf-8') as f:
        if os.path.getsize(hist_file) == 0:
            raise Exception("历史记录文件为空")
        hist_data = json.load(f)
        hist = hist_obj(
            chunk_i=hist_data["chunk_i"],
            chunk_nums=hist_data["chunk_nums"],
            curr_id=hist_data["curr_id"],
            prev_id=hist_data["prev_id"]
        )
    return hist

# 分组发送历史写入
def hist_write(chunk_nums:int, chunk_i:int, prev_id:list[int], curr_id:list[int]):
    hist = hist_obj(chunk_i=chunk_i, chunk_nums=chunk_nums, curr_id=curr_id, prev_id=prev_id)
    with open(hist_file, 'w', encoding='utf-8') as f:
        json.dump(hist, f, ensure_ascii=False, cls=CustomJSONEncoder)

# 分组接收历史读取
hist_recv_file = os.path.join(data_dir, "hist_recv.json")
def hist_recv_read() -> dict[str, hist_recv_obj]:
    with open(hist_recv_file, 'r', encoding='utf-8') as f:
        if os.path.getsize(hist_recv_file) == 0:
            raise Exception("历史记录文件为空")
        hist_data = json.load(f)
        hist = {}
        for key, value in hist_data.items():
            if isinstance(value, dict):
                hist[key] = hist_recv_obj(
                    prev_id=value["prev_id"],
                    next_id=value["next_id"]
                )
            else:
                hist[key] = value  # 如果值已经是对象，直接使用
    return hist

# 隐写模块
def encode_file(prompt, secret, output, k=4):
    env = os.environ.copy()
    subprocess.run(["python", "main.py", "--encode_decode", "0", "--k", str(k), "--prompt", prompt, "--secret", secret, "--output", output], check=True, text=True, cwd=os.path.join(project_dir, "LLMsteg"), env=env)

def decode_file(prompt, cover, output, k=4):
    env = os.environ.copy()
    subprocess.run(["python", "main.py", "--encode_decode", "1", "--k", str(k), "--prompt", prompt, "--cover", cover, "--output", output], check=True, text=True, cwd=os.path.join(project_dir, "LLMsteg"), env=env)

# 论坛API操作模块
owner = os.getenv("OWNER")
repo = os.getenv("REPO")
from github_issue_forum import *

# 帧生成模块
stamp = 80
def create_frame(frame_file):
    hist = hist_read()
    with open(frame_file, 'wb') as f:
        f.write(stamp.to_bytes(1, byteorder='big'))
        f.write(hist.chunk_i.to_bytes(1, byteorder='big'))
        f.write(int(hist.prev_id[0]).to_bytes(1, byteorder='big'))
        f.write(int(hist.prev_id[1]).to_bytes(1, byteorder='big'))
        if hist.chunk_i<hist.chunk_nums-1:
            id = get_random_id(owner,repo)
            while id == hist.curr_id:
                id = get_random_id(owner,repo)
        else:
            id = [0,0]
        f.write(id[0].to_bytes(1, byteorder='big'))
        f.write(id[1].to_bytes(1, byteorder='big'))
        chunk_file = os.path.join(data_dir, "chunks", f"chunk_{hist.chunk_i}.bin")
        chunk_size = os.path.getsize(chunk_file)
        f.write(chunk_size.to_bytes(1, byteorder='big'))
        with open(chunk_file, 'rb') as chunk_fd:
            chunk_data = chunk_fd.read()
            f.write(chunk_data)
    print(f"当前帖子预计发送id为{hist.curr_id[0]}/{hist.curr_id[1]}，下一帧id为{id[0]}/{id[1]}。")
    return id

# 帧提取模块
def extract_frame(frame_file):
    with open(frame_file, 'rb') as f:
        f.seek(1)
        chunk_i = int.from_bytes(f.read(1), byteorder='big')
        prev_id = [int.from_bytes(f.read(1), byteorder='big'), int.from_bytes(f.read(1), byteorder='big')]
        next_id = [int.from_bytes(f.read(1), byteorder='big'), int.from_bytes(f.read(1), byteorder='big')]
        chunk_size = int.from_bytes(f.read(1), byteorder='big')
        chunk_data = f.read(chunk_size)
    print(f"正在提取第{chunk_i}个隐写帧")
    print(f"当前帧的上一帧id为{prev_id[0]}/{prev_id[1]}，下一帧id为{next_id[0]}/{next_id[1]}。")

    try:
        hist = hist_recv_read()
    except:
        print("接收历史记录文件不存在，正在创建...")
        hist = {}
    assert str(chunk_i) not in hist, f"第{chunk_i}个隐写帧已存在，请检查帖子。"
    hist[str(chunk_i)] = hist_recv_obj(prev_id, next_id)
    with open(hist_recv_file, 'w', encoding='utf-8') as f:
        json.dump(hist, f, ensure_ascii=False, cls=CustomJSONEncoder)

    chunk_file = os.path.join(data_dir, "chunks", f"chunk_{chunk_i}.bin")
    with open(chunk_file, 'wb') as chunk_fd:
        chunk_fd.write(chunk_data)
    return chunk_i

# 隐写与发送
def process_frame():
    hist = hist_read()
    print("正在生成第{}个隐写帧...".format(hist.chunk_i))
    frame_file = os.path.join(data_dir, "frame.bin")
    next_id = create_frame(frame_file)
    print(f"隐写帧生成完成。")

    print("正在获取帖子数据...")
    prompt = get_post_data(owner, repo, hist.curr_id[0], hist.curr_id[1])
    prompt_file = os.path.join(data_dir, "prompt.txt")
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print("获取完成。")

    print(f"正在隐写...")
    output_file = os.path.join(data_dir, "output.txt")
    encode_file(prompt_file, frame_file, output_file)
    print("隐写完成。")
    with open(output_file, 'r', encoding='utf-8') as f:
        print(f"隐写结果预览：\n{f.read()[:200]}...\n")

    print("正在发送...")
    send_post_data(owner, repo, hist.curr_id[0], output_file)
    print("发送完成。")
    hist.chunk_i += 1
    hist.prev_id = hist.curr_id
    hist.curr_id = next_id
    with open(hist_file, 'w', encoding='utf-8') as f:
        json.dump(hist, f, ensure_ascii=False, cls=CustomJSONEncoder)

# 接收与提取
def receive_frame(id):
    print("正在接收帖子数据...")
    comments = get_comment_data(owner, repo, id[0], id[1])
    post = get_post_data(owner, repo, id[0], id[1])
    prompt_file = os.path.join(data_dir, "prompt.txt")
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(post)
    print("获取完成。")

    print("正在提取隐写数据...")
    flag = False
    frame_file = os.path.join(data_dir, "frame.bin")
    for i in comments:
        comment_file = os.path.join(data_dir, "comment.txt")
        with open(comment_file, 'w', encoding='utf-8') as f:
            f.write(i)
        decode_file(prompt_file, comment_file, frame_file)

        with open(frame_file, 'rb') as f:
            verify_stamp = int.from_bytes(f.read(1), byteorder='big')
        if verify_stamp == stamp:
            flag = True
            with open(comment_file, 'r', encoding='utf-8') as f:
                print(f"找到含有隐写数据的评论：\n{f.read()[:200]}...\n")
            break
    if not flag:
        print("未找到隐写数据，请检查帖子。")
        exit(1)
    print("提取完成。")
    
    print("正在处理隐写帧...")
    extract_frame(frame_file)
    print("处理完成。")

def receive_frames():
    flag = True
    while flag:
        flag = False
        hist = hist_recv_read()
        for i_str,id in hist.items():
            i= int(i_str)
            if i-1 >= 0 and str(i-1) not in hist:
                print(f"第{i-1}个隐写帧缺失，正在接收...")
                receive_frame(id.prev_id)
                flag = True
                break
            if id.next_id != [0,0] and str(i+1) not in hist:
                print(f"第{i+1}个隐写帧缺失，正在接收...")
                receive_frame(id.next_id)
                flag = True
                break

# 主函数
def main():
    global work_mode
    input_obj=parse_input()

    if work_mode == "send":
        input_file = input_obj["input_file"]
        print("正在压缩文件...")
        compressed_file = os.path.join(data_dir, "compressed_file.bin")
        compress_file(input_file, compressed_file)
        print(f"压缩完成，压缩前文件大小：{os.path.getsize(input_file)} bytes，压缩后文件大小：{os.path.getsize(compressed_file)} bytes")

        print("正在分割文件...")
        chunk_nums=split_file(compressed_file, os.path.join(data_dir, "chunks"))
        print(f"分割完成，共分割为 {chunk_nums} 个文件")

        hist_write(chunk_nums, 0, [0, 0], input_obj["id"])
        for i in range(chunk_nums):
            process_frame()
            if not input_obj["no_confirm"]:
                pause = input("按回车键继续，输入exit退出：")
                if pause == "exit":
                    break
        hist = hist_read()
        if (hist.chunk_i == hist.chunk_nums):
            os.remove(hist_file)
            print("所有数据已发送完成。")
    
    elif work_mode == "receive":
        if os.path.exists(hist_recv_file):
            os.remove(hist_recv_file)
        output_file = input_obj["output_file"]
        id = input_obj["id"]
        receive_frame(id)
        
        receive_frames()

        print("正在合并文件...")
        hist = hist_recv_read()
        compressed_file = os.path.join(data_dir, "compressed_file.bin")
        with open(compressed_file, 'wb') as out_f:
            for i in range(len(hist)):
                chunk_file = os.path.join(data_dir, "chunks", f"chunk_{i}.bin")
                with open(chunk_file, 'rb') as in_f:
                    out_f.write(in_f.read())
        print("合并完成。")

        print("正在解压缩文件...")
        decompress_file(compressed_file, output_file)
        print("解压缩完成。")
        os.remove(hist_recv_file)
    
    elif work_mode == "continue":
        hist = hist_read()
        for i in range(hist.chunk_i, hist.chunk_nums):
            process_frame()
            if not input_obj["no_confirm"]:
                pause = input("按回车键继续，输入exit退出：")
                if pause == "exit":
                    break
        hist = hist_read()
        if (hist.chunk_i == hist.chunk_nums):
            os.remove(hist_file)
            print("所有数据已发送完成。")

if __name__ == "__main__":
    main()