#!/bin/env -S python3

# Copyright (c) 2026 NiyazBiyaz (Niyaz Akhmetov) <niyazik114422@gmail.com>
# Licensed under the MIT License. See LICENSE file for license text.
# Распространяется под лицензией MIT. Полный текст лицензии см. в файле LICENSE.

# Если коротко, делайте с этим кодом что угодно (продавайте, меняйте, улучшайте),
# но оставляйте оригинальный файл лицензии и заголовок копирайта.


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
    write_lists(vuz, sorted_list)


def _read_tables(vuz: Vuz):
    students: dict[int, StudentInfo] = {}

    for program in vuz.programs:
        with open(program.full_path) as f_table:
            f_table.readline()

            for line in f_table:
                (order, prior, accept, total, exams, portfolio, status, id, date) = [
                    ensure_no_quotes(value) for value in line.split(";")
                ]
                order = int(order)
                prior = int(prior)
                accept = accept != NON_ACCEPT
                total = int(total)
                exams = (
                    [int(e) for e in exams.split()]
                    if exams != WITHOUT_EXAMS
                    else WITHOUT_EXAMS
                )
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


def write_lists(vuz: Vuz, sorted_list: list[tuple[StudentInfo, ProgramInfo | None]]):
    pathname = f"{vuz.name}-списки.csv"
    with open(pathname, "w") as f:
        f.write("Идентификатор,Название программы,Подано согласие\n")

        for stud, program in sorted_list:
            name = program.name if program is not None else "Не проходит"
            f.write(f"{stud.id},{name},{stud.accept}\n")
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

    students.sort(key=_student_score, reverse=True)

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


def _student_score(student: StudentInfo):
    exams_score = (
        student.total_score
        if isinstance(student.exam_scores, str)
        else sum(student.exam_scores)
    )
    bvi = 1000 if isinstance(student.exam_scores, str) else 0
    port = student.portfolio_score if bvi == 0 else 0

    return exams_score + bvi + port


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
