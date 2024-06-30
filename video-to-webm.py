import asyncio
import traceback
from argparse import ArgumentParser, BooleanOptionalAction
from asyncio import Semaphore, Task
from asyncio.subprocess import DEVNULL, PIPE
from contextlib import suppress
from contextvars import ContextVar
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Iterator, List, Optional, Sequence, TypeVar, overload
from typing_extensions import TypeAlias, override
from weakref import WeakSet

import ffmpeg
from cookit import flatten
from cookit.pyd import type_validate_python
from pydantic import BaseModel

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
    action=BooleanOptionalAction,
    default=None,
    help="use nearest neighbor scaling / 是否使用最近邻插值缩放",
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

process_sem = Semaphore(4)
processing_filename = ContextVar[str]("processing_filename")

T = TypeVar("T")

InputTransformer: TypeAlias = Callable[[str], T]


class FFProbeInfoStream(BaseModel):
    width: int
    height: int
    duration: float
    avg_frame_rate: str


class FFProbeInfo(BaseModel):
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
    y_str = "Y" if default else "n"
    n_str = "n" if default else "N"
    response = input(f"{question} [{y_str}/{n_str}] ").lower()
    if not response:
        return default
    return response == "y"


def ctx_print(*msg: str):
    if msg:
        with suppress(Exception):
            filename = processing_filename.get()
            m_0, *ms = msg
            return print(f"{filename} | {m_0}", *ms)
    return print(*msg)


def ctx_prompt(question: str, default: bool = True) -> bool:
    with suppress(Exception):
        filename = processing_filename.get()
        return prompt(f"{filename} | {question}", default)
    return prompt(question, default)


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
        item = input(f"No. {len(items) + 1} > ")
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
    path = Path(path_str.strip("'\""))
    if not path.exists():
        raise ValidationError(f"File does not exist / 文件不存在 ({path})")
    return list(iter_all_files(path))


async def run(commands: Sequence[str]):
    proc = await asyncio.create_subprocess_exec(
        *commands,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=PIPE,
    )
    code = await proc.wait()
    if code != 0:
        raise RuntimeError(f"Execute command {commands} failed")
    return proc


async def process_one(input_path: Path, output_path: Path):
    ctx_print("Start processing / 开始处理")

    if output_path.exists() and (
        not ctx_prompt(
            "Output file already exists. Overwrite? / 输出文件已存在，是否覆盖？",
        )
    ):
        ctx_print("Skip converting / 跳过转换")
        return

    input_info = type_validate_python(
        FFProbeInfo,
        await asyncio.to_thread(ffmpeg.probe, str(input_path)),
    )
    input_stream = input_info.streams[0]

    fr1, fr2 = input_stream.avg_frame_rate.split("/")
    frame_rate = int(fr1) / int(fr2)

    input_video = ffmpeg.input(str(input_path)).video

    if input_stream.width != 512 or input_stream.height != 512:
        if not ctx_prompt(
            "File size is not 512x512. Scale? / 文件画幅不是 512x512，是否缩放？",
        ):
            return
        use_nearest = (
            ctx_prompt(
                "Use nearest neighbor scaling? / 是否使用最近邻插值缩放？",
            )
            if args.nearest is None
            else bool(args.nearest)
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
        if not ctx_prompt(
            "Frame rate is higher than 30. Reduce? / 帧率高于 30，是否降低？",
        ):
            return
        input_video = input_video.filter("fps", fps=30, round="down")
        frame_rate = 30

    if input_stream.duration > 3:
        if not ctx_prompt(
            "Video is longer than 3 seconds. Speed up? / 视频长度超过 3 秒，是否加速？",
        ):
            return
        speed = 3 / input_stream.duration
        input_video = input_video.filter("setpts", f"{speed}*PTS")

    with TemporaryDirectory() as tmp_path_name:
        tmp_path_png_expr = str(Path(tmp_path_name) / "%d.png")

        ctx_print("Converting to png frames... / 转换为 png 帧...")
        await run(ffmpeg.output(input_video, tmp_path_png_expr).compile())

        ctx_print("Converting to webm... / 转换为 webm ...")
        out_kwargs = {}
        for i in range(2):
            await run(
                ffmpeg.input(tmp_path_png_expr, framerate=frame_rate)
                .output(
                    str(output_path),
                    format="webm",
                    pix_fmt="yuva420p",
                    **out_kwargs,
                )
                .overwrite_output()
                .compile(),
            )
            if output_path.stat().st_size <= 256 * 1024:
                ctx_print("Transform Done! / 转换完成!")
                break

            if not i:
                ctx_print(
                    "File size is larger than 256 KB. Reduce quality... / "
                    "文件大小超过 256 KB，降低质量...",
                )
                out_kwargs["crf"] = 20
                out_kwargs["b:v"] = "600k"
            else:
                ctx_print(
                    "File is still too large, transform failed. / "
                    "文件仍然过大，转换失败。",
                )
                output_path.unlink(missing_ok=True)


async def main() -> int:
    if args.input:
        input_paths = [Path(x) for x in args.input]
        if p := next((x for x in input_paths if not x.exists()), None):
            print(f"Input path does not exist / 输入文件路径不存在 ({p})")
            return 1
        input_paths = flatten(list(iter_all_files(p)) for p in input_paths)
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

    async def _proc_one(path: Path):
        processing_filename.set(path.name)
        async with process_sem:
            try:
                await process_one(path, output_path / f"{path.stem}.webm")
            except Exception:
                ctx_print("Error while processing / 处理时出错")
                traceback.print_exc()

    tasks = WeakSet[Task]()
    for path in input_paths:
        while process_sem.locked():
            await asyncio.sleep(0)
        tasks.add(asyncio.create_task(_proc_one(path)))

    await asyncio.gather(*tasks)
    print("All Done! / 全部搞定！")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
