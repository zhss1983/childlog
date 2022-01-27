from asyncio import run, sleep
from datetime import date, datetime
from logging import INFO, basicConfig, info
from os import popen
from platform import system

# БЛОК НАСТРОЕК:
# 1) Список игнорируемых процессов.
ignore_list_windows = ('cmd.exe', 'tasklist.exe')
ignore_list_linux = ('ps', 'sh')
# 2) Количество фрагментов на которые нарезается строка отчёта для Linux
max_linux_split = 14
# 3) Время сна между проверками
sleep_time = 60
# 4) формат даты и времени.
FORMAT = '%d %b %Y %H:%M'

tasklist = dict()  # Актуальный список запущенных задач

def split_windows(output):
    def cuts(string: str,
             mapping=((0, -1),)) -> tuple:  # mapping: tuple[tuple[int, int]]
        """
        Режет строку string на tuple по маске mapping.
        mapping содержит не изменяемый список из tulple по 2 int элемента
        Это позиции от какого символа начиная вырезать и по какой символ.
        Полученные строки тримируются c обеих сторон по маске '\n\r\t '.
        """
        out = string.replace('\xa0', '')
        return tuple(out[pos:cut].strip('\n\r\t ') for (pos, cut) in mapping)

    """
    Генератор строк с данными о запущенных приложениях для Windows.
    Основывается на размере 3 по счёту строки состоящей из пробелов и знаков =. 
    """
    mapping, abs_pos, new_pos = output[2].split(' '), 0, 0
    for pos in range(len(mapping)):
        new_pos = abs_pos + len(mapping[pos]) + 1
        mapping[pos] = (abs_pos, new_pos)
        abs_pos = new_pos
    return (cuts(output[pos], mapping) for pos in (1, *range(3, len(output))))

def split_linux(output):
    """
    Генератор строк с данными о запущенных приложениях для Linux.
    Основывается на том, что в строке до самого конца нет блоков с пробелами
    внутри значимых фрагментов, а всего таких блоков 14 штук. Это позволило
    просто нарезать строки на 14 фрагментов игнорируя повторяющиеся пробелы.
    """
    for line in output:
        out = ''
        while out != line:
            out = line
            line = line.replace('  ', ' ')
        yield tuple(
            out.strip('\n\r\t ') for out in line.split(' ', max_linux_split))

def log_dict(lines, key_map, value_map, key_ignore, ignore_list):
    """
    Обновляет список программ запущенных в настоящий момент в системе.
    Логирует новые и остановленные, последние удаляет из словаря.
    """
    keys = set(tasklist.keys())
    for line in lines:
        key = tuple(line[pos] for pos in key_map)
        if key[key_ignore] in ignore_list:
            continue
        value = tuple(line[pos] for pos in value_map)
        if key not in keys:
            tasklist[key] = value
            info(f'R {datetime.now():{FORMAT}} > {key}:{value}')
        else:
            keys.remove(key)
    for key in keys:
        if key[key_ignore] in ignore_list:
            continue
        info(f'S {datetime.now():{FORMAT}} > {key}:{tasklist.pop(key)}')

async def log_cicle(
        cmd, split_gen, key_map, value_map, key_ignore, ignore_list):
    """
    Проверяет каждые sleep_time секунд какие задачи запущены в системе.
    Запускает логирование.

    cmd: команда для запуска.
    split_gen: генератор нарезки получаемого списка строк на tuple-ы.
    key_map: список позиций в нарезанной строке данных для формирования ключа.
    value_map: список позиций в нарезанной строке данных для формирования
               значения.
    key_ignore: номер позиции внутри сформированного ключа для проверки наличия
                значения в списка игнорирования.
    ignore_list: список игнорируемых значений - программа не будет их никак
                 обрабатывать.
    """
    while True:
        log_dict(
            split_gen(tuple(popen(cmd, 'r'))),
            key_map,
            value_map,
            key_ignore,
            ignore_list
        )
        await sleep(sleep_time)

if __name__ == '__main__':
    sysname = system()
    basicConfig(
        filename=f'{date.today()}_tasklist.log',
        level=INFO
    )
    info(f'\n\nLogging for {sysname}\'s tasks is running.\n\n')

    if sysname == 'Windows':
        cmd = 'tasklist'
        key_map = (0, 1)
        key_ignore = 0
        value_map = (2, 3, 4)
        run(log_cicle(
            cmd=cmd,
            split_gen=split_windows,
            key_map=key_map,
            value_map=value_map,
            key_ignore=key_ignore,
            ignore_list=ignore_list_windows
        ))
    elif sysname == 'Linux':
        cmd = 'ps -el'
        key_map = (2, 3, 13)
        key_ignore = 2
        value_map = (0, 1, *range(4, 13))
        run(log_cicle(
            cmd=cmd,
            split_gen=split_linux,
            key_map=key_map,
            value_map=value_map,
            key_ignore=key_ignore,
            ignore_list=ignore_list_windows
        ))
    else:
        error_msg = (f'\n\nThis program can\'t work on {sysname} system.\n'
                     f'Эта программа" не может работать на {sysname} системе.')
        info(error_msg)
        raise BaseException(error_msg)
