"""题面数据模型：抓取结果与两个后端之间传递的统一结构。"""

from dataclasses import dataclass, field


@dataclass
class Problem:
    """一道题的数据，覆盖 HTML 与 LaTeX 两个后端的消费需求。"""

    pid: str
    title: str
    english: str = ""
    type: str = "传统型"
    index: int = 0
    # HTML 后端：DOM 提取的节 HTML 与样例
    time_limit: str = ""                      # 如 "500ms"
    memory_limit: str = ""                    # 如 "16.00MB"
    sections: dict = field(default_factory=dict)   # 节名 -> 渲染后 HTML
    samples: list = field(default_factory=list)    # [{"kind","n","text"}]
    # LaTeX 后端：lentille-context 的 Markdown 源
    content: dict = field(default_factory=dict)    # background/description/formatI/formatO/hint
    limits: dict = field(default_factory=dict)     # {"time": [ms...], "memory": [KB...]}
    md_samples: list = field(default_factory=list) # [[输入, 输出], ...]
    statement_tex: str = ""                   # LaTeX 题面片段（生成时填充）

    @property
    def english_name(self) -> str:
        """模拟赛显示名：english 或空（不暴露洛谷题号）。"""
        return self.english.strip()

    @property
    def exec_name(self) -> str:
        """可执行文件名：english 或 t{编号}。"""
        return self.english_name or f"t{self.index}"


@dataclass
class Contest:
    """比赛配置（contest.json + CLI 合并结果）。"""

    name: str = "模拟赛"
    date: str = ""
    time: str = ""
    duration: str = ""
    notes: list = field(default_factory=list)
