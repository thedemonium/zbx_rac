#!/bin/env python3
# -*- coding: utf-8 -*-
# version 0.9.1

import argparse
import json
import logging
import sys

from typing import Dict, List, Union, NamedTuple, Any
from collections import Counter

from lib_rac import Client1C, UserDecorators

logger = logging.getLogger("zbx_rac")
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.DEBUG)


def discovery(args):
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    db_list = server.get_db_list()
    return Client1C.get_zabbix_lld(db_list)


@UserDecorators.to_json
def session(args):
    result = {}
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    session = server.get_session_list(args.db_id)
    result["total sessions"] = len(session)
    if result["total sessions"] > 0:
        result["hibernate"] = Client1C.counter_session(session, "hibernate", "yes")
        _ = Counter([x["app-id"] for x in session])
        result.update(dict(_))
    return result

@UserDecorators.to_json
def total_sessions(args):
    """Возвращает общее количество сессий во всех базах кластера."""
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    sessions = server.get_cluster_sessions()
    return len(sessions)


@UserDecorators.to_json
def process(args):
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    process = server.get_process_list()
    result = []
    for i, proc in enumerate(process):
        proc["id"] = i
        result.append(proc)
    return result


@UserDecorators.to_json
def licenses(args):
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    lic = server.get_license_list(args.db_id)
    result = Counter([x["short-presentation"] for x in lic])
    return result

@UserDecorators.to_json
def total_licenses(args):
    """Возвращает общее количество лицензий во всех базах кластера."""
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    lic = server.get_cluster_licenses()
    return len(lic)


@UserDecorators.to_json
def locks(args):
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    lock = server.get_lock_list(args.db_id)
    return len(lock)

@UserDecorators.to_json
def total_locks(args):
    """Возвращает общее количество блокировок во всех базах кластера."""
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    locks = server.get_cluster_locks()
    return len(locks)

@UserDecorators.to_json
def db_info(args):
    server = Client1C(args.hostname, args.cls_user, args.cls_pwd, args.rac_path)
    result = server.get_db_info(args.db_id, args.db_user, args.db_pwd)
    return result[0]


def _add_common_args(parser):
    """Добавить общие аргументы для всех subparsers."""
    parser.add_argument(
        "-s", dest="hostname", required=True, help="-s hostname | ip"
    )
    parser.add_argument(
        "-cls-user",
        dest="cls_user",
        default=None,
        help="Имя администратора кластера 1С",
    )
    parser.add_argument(
        "-cls-pwd",
        dest="cls_pwd",
        default=None,
        help="пароль администратора кластера 1С",
    )
    parser.add_argument(
        "--rac-path",
        dest="rac_path",
        default=None,
        help="Полный путь к rac.exe (если не найден автоматически)",
    )


parser = argparse.ArgumentParser(description="Скрипт для сбора данных сервера 1С")
parser.add_argument(
    "--rac-path",
    dest="rac_path",
    default=None,
    help="Полный путь к rac.exe (если не найден автоматически)",
)
subparsers = parser.add_subparsers(
    title="subcommands", description="valid subcommands", help="description"
)

# discovery
discovery_parser = subparsers.add_parser(
    "discovery", help="поиск баз данных Zabbix LLD", parents=[argparse.ArgumentParser(add_help=False)]
)
discovery_parser.add_argument(
    "-s", dest="hostname", required=True, help="-s hostname | ip"
)
discovery_parser.add_argument(
    "-cls-user", dest="cls_user", default=None,
    help="Имя администратора кластера 1С",
)
discovery_parser.add_argument(
    "-cls-pwd", dest="cls_pwd", default=None,
    help="пароль администратора кластера 1С",
)
discovery_parser.add_argument(
    "--rac-path", dest="rac_path", default=None,
    help="Полный путь к rac.exe (если не найден автоматически)",
)
discovery_parser.set_defaults(func=discovery)

# session
session_parser = subparsers.add_parser(
    "session", help="Отчет по сесиям для БД", parents=[argparse.ArgumentParser(add_help=False)]
)
session_parser.add_argument(
    "-s", dest="hostname", required=True, help="-s hostname | ip"
)
session_parser.add_argument(
    "-cls-user", dest="cls_user", default=None,
    help="Имя администратора кластера 1С",
)
session_parser.add_argument(
    "-cls-pwd", dest="cls_pwd", default=None,
    help="пароль администратора кластера 1С",
)
session_parser.add_argument(
    "--rac-path", dest="rac_path", default=None,
    help="Полный путь к rac.exe (если не найден автоматически)",
)
session_parser.add_argument(
    "-db-id", dest="db_id", required=True, help="ID БД(INFOBASE)"
)
session_parser.set_defaults(func=session)

# process
process_parser = subparsers.add_parser(
    "process", help="Отчет по процессам кластера 1С", parents=[argparse.ArgumentParser(add_help=False)]
)
process_parser.add_argument(
    "-s", dest="hostname", required=True, help="-s hostname | ip"
)
process_parser.add_argument(
    "-cls-user", dest="cls_user", default=None,
    help="Имя администратора кластера 1С",
)
process_parser.add_argument(
    "-cls-pwd", dest="cls_pwd", default=None,
    help="пароль администратора кластера 1С",
)
process_parser.add_argument(
    "--rac-path", dest="rac_path", default=None,
    help="Полный путь к rac.exe (если не найден автоматически)",
)
process_parser.set_defaults(func=process)

# licenses
licenses_parser = subparsers.add_parser(
    "licenses", help="Отчет по лицензиям для БД", parents=[argparse.ArgumentParser(add_help=False)]
)
licenses_parser.add_argument(
    "-s", dest="hostname", required=True, help="-s hostname | ip"
)
licenses_parser.add_argument(
    "-cls-user", dest="cls_user", default=None,
    help="Имя администратора кластера 1С",
)
licenses_parser.add_argument(
    "-cls-pwd", dest="cls_pwd", default=None,
    help="пароль администратора кластера 1С",
)
licenses_parser.add_argument(
    "--rac-path", dest="rac_path", default=None,
    help="Полный путь к rac.exe (если не найден автоматически)",
)
licenses_parser.add_argument(
    "-db-id", dest="db_id", required=True, help="ID БД(INFOBASE)"
)
licenses_parser.set_defaults(func=licenses)

# total_licenses
total_licenses_parser = subparsers.add_parser(
    "total_licenses", 
    help="Общее количество лицензий во всех базах кластера", 
    parents=[argparse.ArgumentParser(add_help=False)]
)
total_licenses_parser.add_argument("-s", dest="hostname", required=True, help="-s hostname | ip")
total_licenses_parser.add_argument("-cls-user", dest="cls_user", default=None, help="Имя администратора кластера 1С")
total_licenses_parser.add_argument("-cls-pwd", dest="cls_pwd", default=None, help="пароль администратора кластера 1С")
total_licenses_parser.add_argument("--rac-path", dest="rac_path", default=None, help="Полный путь к rac.exe")
total_licenses_parser.set_defaults(func=total_licenses)

# locks
locks_parser = subparsers.add_parser(
    "locks", help="Отчет по блокировкам для БД", parents=[argparse.ArgumentParser(add_help=False)]
)
locks_parser.add_argument(
    "-s", dest="hostname", required=True, help="-s hostname | ip"
)
locks_parser.add_argument(
    "-cls-user", dest="cls_user", default=None,
    help="Имя администратора кластера 1С",
)
locks_parser.add_argument(
    "-cls-pwd", dest="cls_pwd", default=None,
    help="пароль администратора кластера 1С",
)
locks_parser.add_argument(
    "--rac-path", dest="rac_path", default=None,
    help="Полный путь к rac.exe (если не найден автоматически)",
)
locks_parser.add_argument(
    "-db-id", dest="db_id", required=True, help="ID БД(INFOBASE)"
)
locks_parser.set_defaults(func=locks)

# total_sessions
total_sessions_parser = subparsers.add_parser(
    "total_sessions", 
    help="Общее количество сессий во всех базах кластера", 
    parents=[argparse.ArgumentParser(add_help=False)]
)
total_sessions_parser.add_argument("-s", dest="hostname", required=True, help="-s hostname | ip")
total_sessions_parser.add_argument("-cls-user", dest="cls_user", default=None, help="Имя администратора кластера 1С")
total_sessions_parser.add_argument("-cls-pwd", dest="cls_pwd", default=None, help="пароль администратора кластера 1С")
total_sessions_parser.add_argument("--rac-path", dest="rac_path", default=None, help="Полный путь к rac.exe")
total_sessions_parser.set_defaults(func=total_sessions)

# info
info_parser = subparsers.add_parser(
    "info", help="Информация о базе 1С", parents=[argparse.ArgumentParser(add_help=False)]
)
info_parser.add_argument(
    "-s", dest="hostname", required=True, help="-s hostname | ip"
)
info_parser.add_argument(
    "-cls-user", dest="cls_user", default=None,
    help="Имя администратора кластера 1С",
)
info_parser.add_argument(
    "-cls-pwd", dest="cls_pwd", default=None,
    help="пароль администратора кластера 1С",
)
info_parser.add_argument(
    "--rac-path", dest="rac_path", default=None,
    help="Полный путь к rac.exe (если не найден автоматически)",
)
info_parser.add_argument(
    "-db-id", dest="db_id", required=True, help="ID БД(INFOBASE)"
)
info_parser.add_argument(
    "-db-user", dest="db_user", required=True,
    help="Имя администратора базы 1С",
)
info_parser.add_argument(
    "-db-pwd", dest="db_pwd", required=True,
    help="Пароль администратора базы 1С",
)
info_parser.set_defaults(func=db_info)

# total_locks
total_locks_parser = subparsers.add_parser(
    "total_locks", 
    help="Общее количество блокировок во всех базах кластера", 
    parents=[argparse.ArgumentParser(add_help=False)]
)
total_locks_parser.add_argument("-s", dest="hostname", required=True, help="-s hostname | ip")
total_locks_parser.add_argument("-cls-user", dest="cls_user", default=None, help="Имя администратора кластера 1С")
total_locks_parser.add_argument("-cls-pwd", dest="cls_pwd", default=None, help="пароль администратора кластера 1С")
total_locks_parser.add_argument("--rac-path", dest="rac_path", default=None, help="Полный путь к rac.exe")
total_locks_parser.set_defaults(func=total_locks)

if __name__ == "__main__":
    args = parser.parse_args()
    if not vars(args).get("func"):
        parser.print_usage()
    else:
        try:
            print(args.func(args))
        except SystemExit:
            raise
        except Exception as e:
            logger.error("Ошибка выполнения: %s", e, exc_info=True)
            if vars(args).get("func") is discovery:
                print(json.dumps({"data": []}))
            else:
                print(json.dumps({}))