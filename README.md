<!-- markdownlint-disable MD033 -->

# Video To WebM

This is a simple script that converts a video or gif file to Telegram WebM video sticker format using `ffmpeg`.  
这是一个简单的脚本，使用 `ffmpeg` 将视频或 gif 文件转换为 Telegram WebM 视频贴纸格式。

## Requirements / 依赖

- Python 3.9+ (developed with Python 3.10.10 / 使用 Python 3.10.10 开发)
- [ffmpeg & ffprobe](https://ffmpeg.org/download.html)
- Required Python packages: (install with command below)  
  需要的 Python 包：（使用下面的命令安装）

  ```bash
  pip install "cookit[pyd]" ffmpeg-python
  ```

## Usage / 用法

```text
usage: video-to-webm.py [-h] [-i [INPUT ...]] [-o OUTPUT] [-n | --nearest | --no-nearest] [-y]

options:
  -h, --help
          show this help message and exit

  -i [INPUT ...], --input [INPUT ...]
          input files or folders (prompted if not specified, can be specified multiple times, or specify a folder)
          输入文件或文件夹路径（如果未指定则提示，可指定多项，或 指定一个文件夹）

  -o OUTPUT, --output OUTPUT
          output folder (defaults to "output" folder under current working directory)
          输出文件夹（默认为工作目录下的 output 文件夹）

  -n, --nearest, --no-nearest
          use nearest neighbor scaling
          是否使用最近邻插值缩放

  -y, --yes
          default to all prompts (overwrite output file, etc.)
          默认使用所有提示的默认值（覆盖输出文件等）
```

## Contact / 联系方式

- Telegram: [@lgc2333](https://t.me/lgc2333) / [@stupmbot](https://t.me/stupmbot)
- Discord: [lgc2333](https://discordapp.com/users/810486152401256448)
- Email: [lgc2333@126.com](mailto:lgc2333@126.com)
- QQ: 3076823485 / Group: [1105946125](https://jq.qq.com/?_wv=1027&k=Z3n1MpEp)

## Sponsor Me / 赞助我

**[Click here for more information  
点击这里获取更多信息](https://blog.lgc2333.top/donate)**

Thanks for your support! Your support will make me continue to create contents!  
感谢大家的赞助！你们的赞助将是我继续创作的动力！

## License / 许可证

This project is licensed under the terms of the MIT license. See [LICENSE](LICENSE) for more information.  
本项目使用 MIT 许可证授权。有关更多信息，请参见 [LICENSE](LICENSE)。
