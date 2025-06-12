import sys

def echo_args():
    # sys.argv是一个列表，其中第一个元素是脚本名称，后面的元素是命令行参数
    for arg in sys.argv[1:]:  # 从第二个元素开始迭代，以跳过脚本名称
        print(arg)

if __name__ == "__main__":
    echo_args()
