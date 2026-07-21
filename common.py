# Copyright (c) 2026 NiyazBiyaz (Niyaz Akhmetov) <niyazik114422@gmail.com>
# Licensed under the MIT License. See LICENSE file for license text.
# Распространяется под лицензией MIT. Полный текст лицензии см. в файле LICENSE.


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


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
