import shutil
import time
from argparse import ArgumentParser
from pathlib import Path
from typing import List

import ffmpeg
from pydantic import BaseModel


class FFProbeInfoStream(BaseModel):
    width: int
    height: int
    duration: float
    avg_frame_rate: str


class FFProbeInfo(BaseModel):
    streams: List[FFProbeInfoStream]


parser = ArgumentParser()
parser.add_argument(
    "-i",
    "--input",
    help="input file (prompted if not specified) / 输入文件路径（如果未指定则提示）",
    default=None,
)
parser.add_argument(
    "-o",
    "--output",
    help="output file (defaults to input file name) / 输出文件路径（默认为输入文件名）",
    default=None,
)
parser.add_argument(
    "-n",
    "--nearest",
    action="store_true",
    help="use nearest neighbor scaling / 使用最近邻插值缩放",
)
parser.add_argument(
    "-y",
    "--yes",
    action="store_true",
    help="default to all prompts (overwrite output file, etc.) / 默认使用所有提示的默认值（覆盖输出文件等）",
)

args = parser.parse_args()
yes = args.yes


def prompt(question: str, default: bool = True) -> bool:
    if yes:
        return default
    response = input(f"{question} [y/N] ").lower()
    if not response:
        return default
    return response == "y"


if not args.input:
    input_path = input("Enter the path of the file / 输入文件路径: ")
    input_file = Path(input_path)
else:
    input_file = Path(args.input)

if not input_file.exists():
    print("File does not exist / 文件不存在")
    exit(1)

if args.output:
    output_file = Path(args.output)
else:
    print("Output file not specified. Using input file name. / 未指定输出文件，使用输入文件名。")
    output_file = input_file.with_suffix(".webm")

if output_file.exists() and (
    not prompt("Output file already exists. Overwrite? / 输出文件已存在，是否覆盖？")
):
    exit(0)

input_info = FFProbeInfo(**ffmpeg.probe(str(input_file)))
input_stream = input_info.streams[0]

fr1, fr2 = input_stream.avg_frame_rate.split("/")
frame_rate = int(fr1) / int(fr2)

input_video = ffmpeg.input(str(input_file)).video

if input_stream.width != 512 or input_stream.height != 512:
    if not prompt("File size is not 512x512. Scale? / 文件画幅不是 512x512，是否缩放？"):
        exit()
    use_nearest = args.nearest or prompt(
        "Use nearest neighbor scaling? / 是否使用最近邻插值缩放？",
        default=args.nearest,
    )
    width, height = (512, -1) if input_stream.width > input_stream.height else (-1, 512)
    kwargs = {
        "width": width,
        "height": height,
        "flags": "neighbor" if use_nearest else None,
    }
    input_video = input_video.filter(
        "scale",
        **{k: v for k, v in kwargs.items() if v is not None},
    )

if frame_rate > 30:
    if not prompt("Frame rate is higher than 30. Reduce? / 帧率高于 30，是否降低？"):
        exit()
    input_video = input_video.filter("fps", fps=30, round="down")

if input_stream.duration > 3:
    if not prompt("Video is longer than 3 seconds. Speed up? / 视频长度超过 3 秒，是否加速？"):
        exit()
    speed = 3 / input_stream.duration
    input_video = input_video.filter("setpts", f"{speed}*PTS")

tmp_path_name = f"temp_{time.time()*1000:.0f}"
tmp_path = Path(tmp_path_name)

try:
    print("Converting to png frames... / 转换为 png 帧...")
    if not tmp_path.exists():
        tmp_path.mkdir()
    ffmpeg.output(input_video, f"{tmp_path_name}/%d.png").run()

    print("Converting to webm... / 转换为 webm ...")
    out_kwargs = {}
    for i in range(2):
        (
            ffmpeg.input(f"{tmp_path_name}/%d.png", framerate=frame_rate)
            .output(str(output_file), format="webm", pix_fmt="yuva420p", **out_kwargs)
            .overwrite_output()
            .run()
        )
        if output_file.stat().st_size <= 256 * 1024:
            break

        if not i:
            print(
                "File size is larger than 256 KB. Reduce quality... / 文件大小超过 256 KB，降低质量...",
            )
            out_kwargs["crf"] = 20
            out_kwargs["b:v"] = "600k"
        else:
            print("File is still too large. / 文件仍然过大。")

finally:
    shutil.rmtree(tmp_path)

print("Done! / 搞定！")
