# Copyright (c) 2026 NiyazBiyaz (Niyaz Akhmetov) <niyazik114422@gmail.com>
# Licensed under the MIT License. See LICENSE file for license text.
# Распространяется под лицензией MIT. Полный текст лицензии см. в файле LICENSE.


import json
from pathlib import Path
from typing import Iterable

from common import ProgramInfo, Vuz, normalize_program_name


VUZS_PATH = Path("vuzs.json")

DENY_VARIANTS = {"н", "не", "нет", "неа", "n", "no", "not"}
ACCEPT_VARIANTS = {"д", "да", "конечно", "ага", "y", "yeah", "yes"}


def locate_files() -> list[Vuz]:
    vuzs = _read_vuzs()
    _read_data_indexes(vuzs)
    return vuzs


def _read_vuzs() -> list[Vuz]:
    folders = list(_scan_folders())
    vuzs: list[Vuz] | None = None
    if not VUZS_PATH.exists():
        print(f"Файл {VUZS_PATH} не найден...")

        if len(folders) == 0:
            print("Нечего делать.")
            return []

        vuzs = _dialogue_add_vuzs(folders)

        if not vuzs:
            print("Нечего делать.")
            return []

    vuzs = []

    with open(VUZS_PATH) as f_vuzs:
        vuzs_json = json.load(f_vuzs)

        if not isinstance(vuzs_json, list):
            raise TypeError(
                f"Неверный формат файла vuzs.json: используйте список JSON."
            )

        for vuz in vuzs_json:
            try:
                assert isinstance(vuz, dict), (
                    "Неверный формат файла vuzs.json: используйте объект JSON для значений списка."
                )
                assert "name" in vuz, (
                    "Неверный формат файла vuzs.json: поле 'name' не объявлено."
                )
                assert "folder" in vuz, (
                    "Неверный формат файла vuzs.json: поле 'folder' не объявлено."
                )
            except AssertionError as e:
                raise TypeError(e.args[0]) from e

            vuz = Vuz(vuz["name"], vuz["folder"], [])
            vuzs.append(vuz)

    registered_folders = [v.path_folder.resolve() for v in vuzs]
    same_length = len(registered_folders) == len(folders)
    different_content = not same_length or any(
        registered.resolve() != existing.resolve()
        for registered in registered_folders
        for existing in folders
    )
    if different_content:
        for v in vuzs:
            if not v.path_folder.exists():
                print(f"Директория вуза {v.name} '{v.data_folder}' не найдена.")
                if _dialogue_remove_vuz(v):
                    vuzs.remove(v)

        _save_vuzs_json(vuzs)

        for folder in folders:
            if folder.resolve() not in registered_folders:
                vuzs = _dialogue_add_vuzs([folder], vuzs) or []

    return vuzs


def _read_data_indexes(vuzs: Iterable[Vuz]):
    for v in vuzs:
        folder = v.data_folder
        if isinstance(folder, str):
            folder = Path(folder)

        if not folder.exists():
            raise FileNotFoundError(f"Директория {folder} не найдена.")

        if not (folder / "index.json").exists():
            is_index_created = _dialogue_add_index(folder)
            if not is_index_created:
                print(f"Директория '{folder}' пропущена...")
                continue

        list_dir = [
            {"normalized": normalize_program_name(pr_path), "path": pr_path}
            for pr_path in folder.iterdir()
            if pr_path.suffix == ".csv"
        ]
        dir_names = [
            normalize_program_name(pr_path)
            for pr_path in folder.iterdir()
            if pr_path.suffix == ".csv"
        ]

        with open(folder / "index.json") as f_index:
            index = json.load(f_index)
            if not isinstance(index, dict):
                raise TypeError(
                    f"Неверный формат файла {(folder / 'index.json').resolve()}. Используйте объект JSON."
                )

        for found in dir_names:
            if found not in index:
                print(f"Найдена потенциальная программа вуза: '{found}'.")
                if _get_accept("Хотите добавить программу в индекс директории?"):
                    index[found] = _get_number(
                        f"Введите количество свободных мест для программы '{found}': "
                    )

        for pr_name, count in index.copy().items():
            if pr_name not in dir_names:
                print(f"Программа '{pr_name}' не найдена в файлах директории {folder}.")
                if _get_accept(
                    f"Хотите удалить '{pr_name}' из индекса директории?", default=False
                ):
                    del index[pr_name]
                else:
                    print(f"Программа '{pr_name}' будет пропущена при обработке.")

                continue

            if not isinstance(count, int):
                raise TypeError(
                    f"Ожидалось целое число в значении напротив {pr_name} в файле {folder / 'index.json'}."
                )

            pr_path = [
                pr["path"].resolve() for pr in list_dir if pr["normalized"] == pr_name
            ]
            pr_path = min(pr_path)

            program = ProgramInfo(pr_name, pr_path, count, [])
            v.programs.append(program)

        # Ранее могло быть изменение индекса.
        with open(folder / "index.json", "w") as f_index:
            json.dump(index, f_index, indent=2, ensure_ascii=False)


def _scan_folders():
    for path in Path(".").iterdir():
        if path.is_file():
            continue

        if any(file.suffix == ".csv" for file in path.iterdir()):
            yield path


def _get_accept(hint: str = "", *, default: bool | None = None):
    hint = f"{hint} " + (
        "(да/нет)" if default is None else "(ДА/нет)" if default else "(да/НЕТ)"
    )
    while True:
        answer = input(hint + ": ").strip()
        if answer.lower() in DENY_VARIANTS:
            return False
        elif answer.lower() in ACCEPT_VARIANTS:
            return True

        if default is not None and len(answer) == 0:
            return default

        print("Ввод не распознан, повторите...")


def _dialogue_add_vuzs(
    folders: Iterable[Path], preserve: list[Vuz] | None = None
) -> list[Vuz] | None:
    vuzs: list[Vuz] = []

    if preserve:
        vuzs.extend(preserve)

    for folder in folders:
        print(
            f"Директория '{folder}' потенциально содержит файлы таблиц программ вуза."
        )
        if not _get_accept("Хотите добавить эту директорию как вуз?", default=True):
            continue

        name = input(
            f"Введите название для вуза, которое будет привязано к директории {folder}: "
        )

        vuzs.append(Vuz(name, folder, []))

    if len(vuzs) == 0:
        return

    _save_vuzs_json(vuzs)

    print(f"Файл {VUZS_PATH} успешно создан.")

    return vuzs


def _dialogue_add_index(folder: Path) -> bool:
    print(f"В директории {folder} отсутствует необходимый файл 'index.json'")
    if not _get_accept("Хотите заполнить индекс программ?"):
        return False

    programs_found = [
        normalize_program_name(pr_name)
        for pr_name in folder.iterdir()
        if pr_name.suffix == ".csv"
    ]

    programs = {}

    for program in programs_found:
        programs[program] = _get_number(
            f"Введите количество свободных мест для программы '{program}': "
        )
        break

    with open(folder / "index.json", "w") as f_index:
        json.dump(programs, f_index, indent=2, ensure_ascii=False)

    print(f"Файл {folder / 'index.json'} успешно создан.")
    return True


def _get_number(hint: str):
    while True:
        print(hint)
        value = input()
        if not value.isdigit():
            print("Число не распознано, повторите.")
            continue

        return int(value)


def _save_vuzs_json(vuzs: list[Vuz]) -> None:
    vuzs_json = [v.to_indexable() for v in vuzs]

    with open(VUZS_PATH, "w") as f_vuzs:
        json.dump(vuzs_json, f_vuzs, indent=2, ensure_ascii=False)


def _dialogue_remove_vuz(vuz: Vuz) -> bool:
    return _get_accept(f"Хотите удалить {vuz.name} из индекса?", default=False)
