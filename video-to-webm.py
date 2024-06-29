from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Iterator, List, Optional, TypeVar, overload
from typing_extensions import TypeAlias, override

import ffmpeg
from cookit import flatten

parser = ArgumentParser()
parser.add_argument(
    "-i",
    "--input",
    help=(
        "input files or folders (prompted if not specified, "
        "can be specified multiple times, or specify a folder) / "
        "输入文件或文件夹路径（如果未指定则提示，可指定多项，或指定一个文件夹）"
    ),
    action="extend",
    nargs="*",
    default=None,
)
parser.add_argument(
    "-o",
    "--output",
    help=(
        'output folder (defaults to "output" folder under current working directory) / '
        "输出文件夹（默认为工作目录下的 output 文件夹）"
    ),
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
    help=(
        "default to all prompts (overwrite output file, etc.) / "
        "默认使用所有提示的默认值（覆盖输出文件等）"
    ),
)

args = parser.parse_args()
yes = args.yes


T = TypeVar("T")

InputTransformer: TypeAlias = Callable[[str], T]


@dataclass
class FFProbeInfoStream:
    width: int
    height: int
    duration: float
    avg_frame_rate: str


@dataclass
class FFProbeInfo:
    streams: List[FFProbeInfoStream]


class ValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

    @override
    def __str__(self) -> str:
        return self.args[0]


def iter_all_files(path: Path) -> Iterator[Path]:
    if path.is_dir():
        for file in path.iterdir():
            if file.is_dir():
                yield from iter_all_files(file)
            else:
                yield file
    else:
        yield path


def prompt(question: str, default: bool = True) -> bool:
    if yes:
        return default
    y_str = "y" if default else "Y"
    n_str = "n" if default else "N"
    response = input(f"{question} [{y_str}/{n_str}] ").lower()
    if not response:
        return default
    return response == "y"


@overload
def input_multi(question: str, transformer: InputTransformer[T]) -> List[T]: ...
@overload
def input_multi(question: str, transformer: None = None) -> List[str]: ...
def input_multi(
    question: str,
    transformer: Optional[InputTransformer[T]] = None,
) -> List[Any]:
    print(question)
    print(
        "Please input each item on a separate line, empty line to end / "
        "请输入项目，每行算作一项，留空行结束输入",
    )

    items = []
    while True:
        item = input("> ")
        if not item:
            break
        if transformer:
            try:
                item = transformer(item)
            except Exception as e:
                print(f"输入有误，请重新输入：{e}")
                continue
        items.append(item)

    return items


def input_file_transformer(path_str: str) -> List[Path]:
    path = Path(path_str)
    if not path.exists():
        raise ValidationError(f"File does not exist / 文件不存在 ({path})")
    return list(iter_all_files(path))


def process_one(input_path: Path, output_path: Path):
    if output_path.exists() and (
        not prompt(
            "Output file already exists. Overwrite? / 输出文件已存在，是否覆盖？",
        )
    ):
        print("Skip converting / 跳过转换")
        return

    input_info = FFProbeInfo(**ffmpeg.probe(str(input_path)))
    input_stream = input_info.streams[0]

    fr1, fr2 = input_stream.avg_frame_rate.split("/")
    frame_rate = int(fr1) / int(fr2)

    input_video = ffmpeg.input(str(input_path)).video

    if input_stream.width != 512 or input_stream.height != 512:
        if not prompt(
            "File size is not 512x512. Scale? / 文件画幅不是 512x512，是否缩放？",
        ):
            exit()
        use_nearest = args.nearest or prompt(
            "Use nearest neighbor scaling? / 是否使用最近邻插值缩放？",
            default=args.nearest,
        )
        width, height = (
            (512, -1) if input_stream.width > input_stream.height else (-1, 512)
        )
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
        if not prompt(
            "Frame rate is higher than 30. Reduce? / 帧率高于 30，是否降低？",
        ):
            exit()
        input_video = input_video.filter("fps", fps=30, round="down")

    if input_stream.duration > 3:
        if not prompt(
            "Video is longer than 3 seconds. Speed up? / 视频长度超过 3 秒，是否加速？",
        ):
            exit()
        speed = 3 / input_stream.duration
        input_video = input_video.filter("setpts", f"{speed}*PTS")

    with TemporaryDirectory() as tmp_path_name:
        tmp_path_png_expr = str(Path(tmp_path_name) / "%d.png")

        print("Converting to png frames... / 转换为 png 帧...")
        ffmpeg.output(input_video, tmp_path_png_expr).run()

        print("Converting to webm... / 转换为 webm ...")
        out_kwargs = {}
        for i in range(2):
            (
                ffmpeg.input(tmp_path_png_expr, framerate=frame_rate)
                .output(
                    str(output_path),
                    format="webm",
                    pix_fmt="yuva420p",
                    **out_kwargs,
                )
                .overwrite_output()
                .run()
            )
            if output_path.stat().st_size <= 256 * 1024:
                print("Transform Done! / 转换完成!")
                break

            if not i:
                print(
                    "File size is larger than 256 KB. Reduce quality... / "
                    "文件大小超过 256 KB，降低质量...",
                )
                out_kwargs["crf"] = 20
                out_kwargs["b:v"] = "600k"
            else:
                print(
                    "File is still too large, transform failed. / "
                    "文件仍然过大，转换失败。",
                )
                output_path.unlink(missing_ok=True)


def main() -> int:
    if args.input:
        input_paths = Path(args.input)
        if not input_paths.exists():
            print("Input path does not exist / 输入文件路径不存在")
            return 1
        input_paths = (
            list(iter_all_files(input_paths)) if input_paths.is_dir() else [input_paths]
        )
    else:
        input_paths = flatten(
            input_multi(
                "Enter input file or folder paths / 输入输入文件或文件夹路径: ",
                input_file_transformer,
            ),
        )

    output_path = Path(args.output) if args.output else (Path.cwd() / "output")
    if not output_path.exists():
        ok = prompt(
            "Output dir does not exist, create? / 输出文件夹不存在，是否创建？",
        )
        if not ok:
            print("Aborting / 中止")
            return 1
        output_path.mkdir(parents=True)

    for it in input_paths:
        process_one(it, output_path / f"{it.stem}.webm")

    print("All Done! / 全部搞定！")
    return 0


if __name__ == "__main__":
    exit(main())
