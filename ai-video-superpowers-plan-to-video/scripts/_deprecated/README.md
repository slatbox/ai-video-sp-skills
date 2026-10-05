本目录脚本已废弃，勿用：

- concat.py：**在 iSH 下不可用**。它用 ffmpeg concat 解复用器 + list.txt；iSH 的 ffmpeg 只转换命令行参数里的路径，list.txt 内部路径不转换，必然报 Impossible to open。
  替代：用 ffmpeg-skill 的 scripts/join.py（各段作为命令行输入）。
- tailframe.py：v1.1.0 起流程不再需要（分镜板已链式连续，连贯片段不再生成尾帧首帧图）。
