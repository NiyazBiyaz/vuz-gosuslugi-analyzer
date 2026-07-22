#!/bin/env -S python3

# Copyright (c) 2026 NiyazBiyaz (Niyaz Akhmetov) <niyazik114422@gmail.com>
# Licensed under the MIT License. See LICENSE file for license text.
# Распространяется под лицензией MIT. Полный текст лицензии см. в файле LICENSE.

# Если коротко, делайте с этим кодом что угодно (продавайте, меняйте, улучшайте),
# но оставляйте оригинальный файл лицензии и заголовок копирайта.


import csv
from datetime import datetime
import sys

from common import (
    ProgramInfo,
    Status,
    StudentInfo,
    Vuz,
    ensure_no_quotes,
    parse_date,
)
from index import locate_files


NON_ACCEPT = "—"
WITHOUT_EXAMS = "Без вступительных испытаний"


def main(vuz: Vuz, keep_ids: set[int]):
    print(f"Обрабатывается: {vuz.name} ({vuz.data_folder})")
    students = _read_tables(vuz)
    sorted_list = _sorted_by_priority(list(students.values()), vuz.programs, keep_ids)
    _write_lists(vuz, sorted_list)


def _read_tables(vuz: Vuz):
    students: dict[int, StudentInfo] = {}

    gosuslugi_dialect = _GosuslugiDialect()

    for program in vuz.programs:
        with open(program.full_path, encoding="utf-8-sig") as f_table:
            f_table.readline()
            lines = csv.reader(f_table, gosuslugi_dialect)

            for line in lines:
                (_, prior, accept, total, exams, portfolio, status, id, date) = (
                    _try_schemas(line)
                )

                if id in students:
                    student = students[id]
                    student.priorities[prior] = program
                    student.statuses[program.name] = status
                else:
                    student = StudentInfo(
                        id,
                        {prior: program},
                        accept,
                        exams,
                        total,
                        portfolio,
                        {program.name: status},
                        date,
                    )
                    students[id] = student

                program.students.append(student)

    return students


def _write_lists(vuz: Vuz, sorted_list: list[tuple[StudentInfo, ProgramInfo | None]]):
    pathname = f"{vuz.name}-списки.csv"
    with open(pathname, "w") as f:
        f.write(
            "Идентификатор,Балл по сортировке,Подано согласие,Приоритет программы,Название программы\n"
        )

        for stud, program in sorted_list:
            pr_name = program.name if program is not None else "Не проходит"
            priority = stud.get_priority_of_program(program) if program else 0
            f.write(
                f"{stud.id},{stud.sort_score_str()},{stud.accept},{priority},{pr_name}\n"
            )
    print(f"Файл {pathname} создан успешно.")


def _sorted_by_priority(
    students: list[StudentInfo],
    programs: list[ProgramInfo],
    keep_ids: set[int],
    require_accept: bool = True,
) -> list[tuple[StudentInfo, ProgramInfo | None]]:
    counts = {p.name: p.count for p in programs}

    final_list: list[tuple[StudentInfo, ProgramInfo | None]] = []
    cannot_list: list[StudentInfo] = []

    students.sort(key=StudentInfo.sort_score, reverse=True)

    for student in students:
        for pr_name in counts:
            if student.statuses.get(pr_name) == Status.STATUS_DROPPED:
                continue
            if require_accept and not student.accept and student.id not in keep_ids:
                continue
            if pr_name not in [p.name for p in student.priorities.values()]:
                continue

            priors = sorted(student.priorities.items(), key=lambda p: p[0])
            for _, program in priors:
                if counts[program.name] == 0:
                    continue
                counts[program.name] -= 1
                final_list.append((student, program))
                break
            else:
                continue

            break
        else:
            cannot_list.append(student)

    final_list += [(student, None) for student in cannot_list if student.accept]

    return final_list


def _schema1(row: list[str]):
    order, prior, accept, total, exams, portfolio, status, id, date = row
    return order, prior, accept, total, exams, portfolio, status, id, date


def _schema2(row: list[str]):
    order, id, prior, accept, total, exams, portfolio, status, date = row
    if exams == "—":
        exams = ""
    return order, prior, accept, total, exams, portfolio, status, id, date


def _try_schemas(
    row: list[str],
) -> tuple[int, int, bool, int, tuple[int, int, int] | str, int, Status, int, datetime]:  # type: ignore  # It's never None
    schemas = [_schema1, _schema2]
    last_e = None
    for schema in schemas:
        try:
            res = schema(row)
            return _parse(*res)
        except ValueError as e:
            last_e = e

    if last_e is not None:
        raise last_e


def _parse(order, prior, accept: str, total, exams, portfolio, status, id, date):
    order = int(order)
    prior = int(prior)
    b_accept = accept != NON_ACCEPT
    total = int(total)
    exams = [int(e) for e in exams.split()] if exams != WITHOUT_EXAMS else WITHOUT_EXAMS
    if isinstance(exams, list):
        # У некоторых людей не все 3 экзамена прописаны,
        # поэтому добавляем им нули чтобы не падал скрипт
        exams += [0, 0, 0]
        exams = exams[0], exams[1], exams[2]

    try:
        status = Status(status)
    except ValueError:
        print(
            f"Неучтенный статус: '{status}'. Оставьте сообщение об этой ошибке: https://github.com/NiyazBiyaz/vuz-gosuslugi-analyzer/issues"
        )
        status = Status.STATUS_UNKNOWN

    portfolio = int(portfolio)
    id = int(id)
    date = parse_date(date)
    return order, prior, b_accept, total, exams, portfolio, status, id, date


class _GosuslugiDialect(csv.Dialect):
    def __init__(self):
        self.delimiter = ";"
        self.doublequote = False
        self.lineterminator = "\n"
        self.quoting = csv.QUOTE_ALL
        self.quotechar = '"'
        super().__init__()


if __name__ == "__main__":
    keep_ids = {int(id) for id in sys.argv if id.isdigit()}

    if keep_ids:
        print(
            "В списках будут оставлены коды участников даже если согласие не было подано:"
        )
        for id in keep_ids:
            print(f"    {id}")

    for v in locate_files():
        main(v, keep_ids)
