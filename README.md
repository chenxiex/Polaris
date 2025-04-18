# Polaris 北极星隐蔽通信协议

一种基于社交网络场景的隐蔽通信方案。

## 环境设置

程序仅在 python 3.11 上测试通过。

```bash
pip install requirements.txt
```

然后，按照`.env.example`内的示例，创建`.env`文件，并根据自身情况填入相应的环境变量的值。**注意**，这一步必须完成！

## 运行

```bash
> python main.py --help
usage: main.py [-h] --mode {send,receive,continue} --id ID --file FILE

Polaris 数据传输工具

options:
  -h, --help            show this help message and exit
  --mode {send,receive,continue}
                        工作模式: send(发送), receive(接收), continue(继续发送)
  --id ID               发送目标ID，格式为 帖子编号/楼层编号
  --file FILE           输入或输出文件路径（绝对路径）
``` 

如果你使用样例的 github_issue_forum 作为论坛实现，那么 `--id` 的参数应该为 `issue number/comment楼层数`。例如，如果你希望隐写后的帖子发布在 `https://github.com/username/repo/issues/1`的第`2`个comment，那么你应该使用 `--id 1/2`。接收同理。