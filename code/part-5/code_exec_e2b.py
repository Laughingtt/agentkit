# runnable: no
# depends: e2b-code-interpreter
# usage: python code_exec_e2b.py   （需要先把 E2B_API_KEY 写进环境变量；本书全程不执行代码文件）

# Ch26 的示范：把「执行代码」做成一个工具。代码不跑在你的机器上，
# 跑在一台别人托管的沙箱里——你需要的是一个远程沙箱服务的 API key。

# ⚠️ 刻意缺席的一段：全文没有任何一处把模型输出的字符串交给本机子进程执行。
#    那是 26.10 要点名的反例，不是示范。真要写，也必须先经过一层隔离环境。

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any

# 一份执行契约的全部硬边界。集中放在这里，是为了让"上限是什么"在第一屏就有答案。
MAX_STDOUT_CHARS = 8000        # 标准输出最多回传多少字符
MAX_STDERR_CHARS = 4000        # 标准错误留的窗口小些——它多半是给人看的诊断
SANDBOX_TIMEOUT_SECONDS = 300  # 一个沙箱连续运行多久之后自动挂起
CODE_TIMEOUT_SECONDS = 60      # 单次执行的墙钟超时


@dataclass
class ExecResult:
    """run_python 的返回值。

    四个字段一个都不缺：成功靠 ok=True 表示，失败靠 ok=False 加一段
    stderr 表示，而不是换成另一种返回结构。所以模型不必先猜"这次会返回什么"
    再决定怎么读。固定形状比省几个字段重要。
    """

    ok: bool
    stdout: str
    stderr: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        # 用 JSON 而不是 repr：模型见过的训练数据里 JSON 远多于 Python 对象的打印形式。
        return json.dumps(asdict(self), ensure_ascii=False)


def _clip(text: str, limit: int) -> str:
    """截断一段输出，并在断口留一句说明。

    留这句说明是因为：模型看到戛然而止的 stdout，会以为"程序就是这样算完的"，
    然后拿着半张报表继续往下推理——这是 code execution 里最常见的一种幻觉。
    """
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...（已截断，这段原本共 {len(text)} 字符）"


def _collect(execution: Any) -> ExecResult:
    """把 SDK 返回的执行结果压成契约里那一个固定形状：合并、截断、判定成败。

    成败只看 error 字段——它不为空才叫跑砸了；stdout 里印了什么不算数。
    """
    # artifacts 收的是"存到文件里的东西"：图、CSV、报表。
    # 这里不实现取文件那一步，只把契约里的这一栏占住并写清它该装什么。
    return ExecResult(
        ok=execution.error is None,
        stdout=_clip("\n".join(execution.logs.stdout), MAX_STDOUT_CHARS),
        stderr=_clip("\n".join(execution.logs.stderr), MAX_STDERR_CHARS),
        artifacts=[],
    )


def run_python(code: str, timeout: int = CODE_TIMEOUT_SECONDS) -> ExecResult:
    """在一个新建的沙箱里跑一段 Python：建 → 跑 → 收 → 拆。

    每次调用一个干净环境，代价是每次都付启动开销。26.7 讲另一种写法——
    会话内复用同一个沙箱——以及它的两种代价。
    """
    from e2b_code_interpreter import Sandbox

    # 一个沙箱也不开网络。模型写的代码里冒出一个网络请求是常态，
    # 而它一旦能出网，机器上一切可读的东西都成了可以被外传的数据。
    # 需要装包时走模板预装，而不是在这里现开一个口子。
    sandbox = Sandbox.create(
        timeout=SANDBOX_TIMEOUT_SECONDS,
        allow_internet_access=False,
    )
    try:
        return _collect(sandbox.run_code(code, timeout=timeout))
    finally:
        # 本文件里最要紧的一行：忘了拆，沙箱就在你的账号下一直活着，
        # 而这类服务是按秒计费的。
        sandbox.kill()


class Session:
    """会话内复用一个沙箱（26.7 的另一种写法）。

    沙箱建一次，之后每次执行都在同一个环境里——上一次装好的包还在，
    上一次定义的变量还在，上一次写下的文件还在。
    """

    def __init__(self, timeout: int = SANDBOX_TIMEOUT_SECONDS):
        from e2b_code_interpreter import Sandbox

        self._sandbox = Sandbox.create(
            timeout=timeout,
            allow_internet_access=False,
        )

    def run(self, code: str, timeout: int = CODE_TIMEOUT_SECONDS) -> ExecResult:
        return _collect(self._sandbox.run_code(code, timeout=timeout))

    def close(self) -> None:
        """会话结束时必须调它。

        与 run_python 里的 finally 是同一个道理，区别只是这次要靠调用方记得，
        所以被做成显式的一步，而不是藏在对象被回收时。
        """
        self._sandbox.kill()


# 错误示范（26.10.1 的完整分析在这里）：
#     import subprocess
#     subprocess.run(["python3", "-c", model_output], check=True)
#
# 第一条错：model_output 是一段还没被执行过的字符串，而第一步执行的就是"交给解释器"。
# 第二条错：它跑在你的进程旁边而不是墙里，写文件、读密钥、占内存都是默认而非可能。
# 第三条错：它根本没有上限可绕，因为根本没有人设过上限。


if __name__ == "__main__":
    # 没有凭据就早退并说清原因，而不是让读者对着栈回溯猜。
    if not os.environ.get("E2B_API_KEY"):
        raise SystemExit("需要先设置环境变量 E2B_API_KEY")

    # 一次最小调用：交一段代码，拿回一段结果。
    print(run_python("print(1 + 1)").to_json())

    # 一次会话内复用：两段代码共享一个沙箱，第二段看得见第一段留下的变量。
    session = Session()
    try:
        session.run("total = 6 * 7")
        print(session.run("print(total)").to_json())
    finally:
        session.close()
