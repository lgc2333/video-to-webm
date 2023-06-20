<!-- markdownlint-disable MD033 -->

# Video To WebM

This is a simple script that converts a video or gif file to Telegram WebM video sticker format using `ffmpeg`.

这是一个简单的脚本，使用 `ffmpeg` 将视频或 gif 文件转换为 Telegram WebM 视频贴纸格式。

## Requirements / 依赖

- Python 3.6+ (developed with Python 3.10.10 / 使用 Python 3.10.10 开发)
- [ffmpeg & ffprobe](https://ffmpeg.org/download.html)
- Required Python packages (install with command below) / 需要的 Python 包（使用下面的命令安装）：

  ```bash
  pip install pydantic ffmpeg-python
  ```

## Usage / 用法

```text
usage / 用法: video-to-webm.py [-h] [-i INPUT] [-o OUTPUT] [-n] [-y]

options / 参数:
  -h, --help            show this help message and exit / 显示此帮助消息并退出
  -i INPUT, --input INPUT
                        input file / 输入文件路径（如果未指定则提示）
  -o OUTPUT, --output OUTPUT
                        output file / 输出文件路径（默认为输入文件名）
  -n, --nearest         use nearest neighbor scaling / 使用最近邻插值缩放
  -y, --yes             default to all prompts (overwrite output file, etc.) / 默认使用所有提示的默认值（覆盖输出文件等）
```

## Contact / 联系方式

- Telegram: [@lgc2333](https://t.me/lgc2333) / [@stupmbot](https://t.me/stupmbot)
- Discord: [lgc2333](https://discordapp.com/users/810486152401256448)
- Email: [lgc2333@126.com](mailto:lgc2333@126.com)
- QQ: 3076823485 / Group: [1105946125](https://jq.qq.com/?_wv=1027&k=Z3n1MpEp)

## Sponsor Me / 赞助我

- [AFDian / 爱发电](https://afdian.net/@lgc2333)
- <details>
    <summary>QR Code / 收款码 (Click to expand / 点击展开)</summary>

  ![讨饭](https://raw.githubusercontent.com/lgc2333/ShigureBotMenu/master/src/imgs/sponsor.png)

  </details>

## License / 许可证

This project is licensed under the terms of the MIT license. See [LICENSE](LICENSE) for more information.

本项目使用 MIT 许可证授权。有关更多信息，请参见 [LICENSE](LICENSE)。
