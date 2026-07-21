# Copyright (c) 2026 NiyazBiyaz (Niyaz Akhmetov) <niyazik114422@gmail.com>
# Licensed under the MIT License. See LICENSE file for license text.
# Распространяется под лицензией MIT. Полный текст лицензии см. в файле LICENSE.


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TypedDict


def normalize_program_name(name: str | Path) -> str:
    if isinstance(name, str):
        name = Path(name)

    pr_name = name.name

    parts = pr_name.replace("_", " ").split(".")
    return ".".join(parts[:-2])


def ensure_no_quotes(value: str):
    value = value.strip()
    if value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


@dataclass
class ProgramInfo:
    name: str
    full_path: Path
    count: int
    students: list[StudentInfo]


class Status(Enum):
    STATUS_PENDING = "На рассмотрении"
    STATUS_MEMBER = "Участвуете в конкурсе"
    STATUS_PROCESSING = "Передано в вуз"
    STATUS_PENDING_EXAMS = "Ожидаются результаты испытаний"
    STATUS_DROPPED = "Конкурсная группа исключена"
    STATUS_DROPPED_BY_VUZ = "Вуз отклонил выбор конкурсной группы"
    STATUS_UNKNOWN = "Неучтенный статус"


@dataclass
class StudentInfo:
    id: int
    priorities: dict[int, ProgramInfo]
    accept: bool
    exam_scores: tuple[int, int, int] | str
    total_score: int
    portfolio_score: int
    statuses: dict[str, Status]
    date_added: datetime

    def sort_score(self):
        exams_score = (
            self.total_score
            if isinstance(self.exam_scores, str)
            else sum(self.exam_scores)
        )
        bvi = 1000 if isinstance(self.exam_scores, str) else 0
        port = self.portfolio_score if bvi == 0 else 0

        return exams_score + bvi + port

    def sort_score_str(self):
        score = self.sort_score()
        return score if score < 1000 else "БВИ"

    def get_priority_of_program(self, program: ProgramInfo):
        for prior, prog in self.priorities.items():
            if prog == program:
                return prior
        raise ValueError(
            f"Program '{program.name}' is not selected for student with code {self.id}."
        )


def parse_date(date: str) -> datetime:
    date, _, time = date.split()
    day, mon, year = [int(d) for d in date.split(".")]
    hour, min = [int(t) for t in time.split(":")]

    return datetime(year, mon, day, hour, min)


@dataclass
class Vuz:
    name: str
    data_folder: Path | str
    programs: list[ProgramInfo] = field(default_factory=list)

    @property
    def path_folder(self):
        if isinstance(self.data_folder, str):
            return Path(self.data_folder)
        return self.data_folder

    def to_indexable(self) -> IndexableVuz:
        return {"name": self.name, "folder": str(self.data_folder)}


class IndexableVuz(TypedDict):
    name: str
    folder: str
