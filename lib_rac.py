# -*- coding: utf-8 -*-
import logging, json, subprocess, os, sys, shutil
from typing import Dict, List, Union, Callable, TypeVar, Any, Optional


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


ListRac = List[Dict[str, str]]


class UserDecorators:
    @classmethod
    def to_json(cls, func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            result = json.dumps(result)
            return result

        return wrapper


class Client1C:
    def __init__(
        self,
        hostname: str,
        cls_user: Union[str, None] = None,
        cls_pwd: Union[str, None] = None,
        rac_path: Union[str, None] = None,
    ) -> None:
        self.hostname = hostname
        self.cls_user = cls_user
        self.cls_pwd = cls_pwd
        self.rac_executable = self._find_rac(rac_path)
        self.cluster_id = self.get_cluster_id()

    @staticmethod
    def _find_rac(rac_path: Union[str, None] = None) -> str:
        """Определить полный путь к rac/rac.exe.

        Порядок поиска:
        1. Явно переданный rac_path
        2. Поиск в PATH через shutil.which
        3. Автоопределение на Windows (реестр, стандартные пути)
        4. Автоопределение на Linux (стандартные пути)
        """
        # 1. Явно переданный путь
        if rac_path:
            rac_path = os.path.expandvars(os.path.expanduser(rac_path))
            if os.path.isfile(rac_path):
                logger.debug("Используется явно указанный путь: %s", rac_path)
                return rac_path
            else:
                raise FileNotFoundError(
                    "Файл rac не найден по указанному пути: {}".format(rac_path)
                )

        # 2. Поиск в PATH
        rac_name = "rac.exe" if sys.platform == "win32" else "rac"
        which_result = shutil.which(rac_name)
        if which_result:
            logger.debug("rac найден в PATH: %s", which_result)
            return which_result

        # 3. Автоопределение на Windows
        if sys.platform == "win32":
            found = Client1C._find_rac_windows()
            if found:
                return found

        # 4. Автоопределение на Linux
        if sys.platform.startswith("linux"):
            found = Client1C._find_rac_linux()
            if found:
                return found

        raise FileNotFoundError(
            "Не удалось найти утилиту rac. "
            "Укажите путь явно через --rac-path. "
            "Искавшие расположения: PATH, стандартные директории 1С."
        )

    @staticmethod
    def _parse_version(ver_str: str):
        """Разобрать строку версии вида '8.3.27.1688' в кортеж int для сортировки."""
        parts = []
        for p in ver_str.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(p)
        return tuple(parts)

    @staticmethod
    def _find_rac_in_versioned_dir(base_dir: str, exe_name: str = "rac.exe") -> Optional[str]:
        """Найти exe с максимальной версией в base_dir/<version>/bin/.

        Ищет поддиректории вида 8.3.XX.XXXX, сортирует по версии,
        возвращает путь к bin/<exe_name> из самой новой.
        """
        if not os.path.isdir(base_dir):
            return None
        version_dirs = []
        try:
            for entry in os.listdir(base_dir):
                full = os.path.join(base_dir, entry)
                if not os.path.isdir(full):
                    continue
                exe_path = os.path.join(full, "bin", exe_name)
                if os.path.isfile(exe_path):
                    version_dirs.append((Client1C._parse_version(entry), exe_path))
        except OSError:
            return None
        if not version_dirs:
            return None
        # Сортируем по версии, берём максимальную
        version_dirs.sort(key=lambda x: x[0])
        best = version_dirs[-1][1]
        logger.debug("Выбран последний билд в %s: %s", base_dir, best)
        return best

    @staticmethod
    def _find_rac_windows() -> Optional[str]:
        """Поиск rac.exe на Windows: 1cv8 (последний билд), реестр, 1CE."""
        import winreg

        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get(
            "ProgramFiles(x86)", r"C:\Program Files (x86)"
        )

        # 3a. C:\Program Files\1cv8\<version>\bin\rac.exe — берём последний билд
        v8_roots = [
            os.path.join(program_files, "1cv8"),
            os.path.join(program_files_x86, "1cv8"),
            r"C:\Program Files\1cv8",
        ]
        for root in v8_roots:
            found = Client1C._find_rac_in_versioned_dir(root, "rac.exe")
            if found:
                return found

        # 3b. Поиск через реестр: HKLM\SOFTWARE\1C\1Cv8 -> InstallPath
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\1C\1Cv8"
            ) as key:
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                if install_path:
                    # Сначала пробуем current
                    rac_candidate = os.path.join(
                        install_path, "current", "bin", "rac.exe"
                    )
                    if os.path.isfile(rac_candidate):
                        return rac_candidate
                    # Затем ищем последний билд среди версий
                    found = Client1C._find_rac_in_versioned_dir(install_path, "rac.exe")
                    if found:
                        return found
        except (OSError, FileNotFoundError):
            logger.debug("Реестр 1С не найден или недоступен")

        # 3c. C:\Program Files\1C\1CE\<version>\bin\rac.exe — как запасной вариант
        standard_roots = [
            os.path.join(program_files, "1C", "1CE"),
            os.path.join(program_files_x86, "1C", "1CE"),
        ]
        for root in standard_roots:
            found = Client1C._find_rac_in_versioned_dir(root, "rac.exe")
            if found:
                return found

        return None

    @staticmethod
    def _find_rac_linux() -> Optional[str]:
        """Поиск rac на Linux по стандартным путям."""
        candidates = [
            "/opt/1C/v8/current/bin/rac",
            "/opt/1c/v8/current/bin/rac",
        ]
        # Добавляем все версии из /opt/1C/v8/
        for base in ["/opt/1C/v8", "/opt/1c/v8"]:
            if os.path.isdir(base):
                try:
                    for entry in os.listdir(base):
                        candidates.append(
                            os.path.join(base, entry, "bin", "rac")
                        )
                except OSError:
                    pass

        for candidate in candidates:
            if os.path.isfile(candidate):
                logger.debug("rac найден: %s", candidate)
                return candidate

        return None

    def get_cluster_id(self) -> str:
        command = "cluster list {}".format(self.hostname)
        result = self._exec_rac(command)
        return result[0]["cluster"]

    def get_db_list(self) -> ListRac:
        command = "infobase --cluster={} summary list {}".format(
            self.cluster_id, self.hostname
        )
        if self.cls_user and self.cls_pwd:
            command += " --cluster-user={} --cluster-pwd={}".format(
                self.cls_user, self.cls_pwd
            )
        result = self._exec_rac(command)
        return result

    def get_session_list(self, db_id: str) -> ListRac:
        command = "session --cluster={} list --infobase={} {}".format(
            self.cluster_id, db_id, self.hostname
        )
        if self.cls_user and self.cls_pwd:
            command += " --cluster-user={} --cluster-pwd={}".format(
                self.cls_user, self.cls_pwd
            )
        result = self._exec_rac(command)
        return result

    def get_lock_list(self, db_id: str) -> ListRac:
        command = "lock --cluster={} list --infobase={} {}".format(
            self.cluster_id, db_id, self.hostname
        )
        if self.cls_user and self.cls_pwd:
            command += " --cluster-user={} --cluster-pwd={}".format(
                self.cls_user, self.cls_pwd
            )
        result = self._exec_rac(command)
        return result

    def get_license_list(self, db_id: str) -> ListRac:
        command = "session --cluster={} list --infobase={} {} --licenses".format(
            self.cluster_id, db_id, self.hostname
        )
        if self.cls_user and self.cls_pwd:
            command += " --cluster-user={} --cluster-pwd={}".format(
                self.cls_user, self.cls_pwd
            )
        result = self._exec_rac(command)
        return result

    def get_db_info(
        self,
        db_id: str,
        user_name: Union[str, None] = None,
        user_pwd: Union[str, None] = None,
    ) -> ListRac:
        command = "infobase --cluster={} info --infobase={} {}".format(
            self.cluster_id, db_id, self.hostname
        )
        if self.cls_user and self.cls_pwd:
            command += " --cluster-user={} --cluster-pwd={}".format(
                self.cls_user, self.cls_pwd
            )
        if user_name and user_pwd:
            command += " --infobase-user={} --infobase-pwd={}".format(
                user_name, user_pwd
            )
        result = self._exec_rac(command)
        return result

    def get_process_list(self) -> ListRac:
        command = "process --cluster={} list {}".format(
            self.cluster_id, self.hostname
        )
        if self.cls_user and self.cls_pwd:
            command += " --cluster-user={} --cluster-pwd={}".format(
                self.cls_user, self.cls_pwd
            )
        result = self._exec_rac(command)
        return result

    def _exec_rac(self, command_args: str) -> ListRac:
        """Выполнить команду rac с полным путём к исполняемому файлу.

        command_args — строка аргументов БЕЗ префикса 'rac',
        например: 'cluster list --agent=SQLHOLD2'
        """
        cmd_list = [self.rac_executable] + command_args.split()
        logger.debug("Выполняется команда: %s", " ".join(cmd_list))
        result = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # rac.exe на русской Windows выводит в cp866, не в UTF-8
        stdout_text = self._decode_output(result.stdout)
        stderr_text = self._decode_output(result.stderr)
        if stderr_text.strip():
            err = "Error subprocess.run, cmd: {}, Error: {}".format(
                cmd_list, stderr_text.strip()
            )
            logger.error(err)
            raise IOError(err)
        return Client1C._row_output_to_dict(stdout_text)

    @staticmethod
    def _decode_output(raw: bytes) -> str:
        """Декодировать вывод rac.exe с подбором кодировки.

        На русской Windows rac.exe использует cp866 (OEM-кодировка консоли).
        Пробуем cp866 → cp1251 → utf-8.
        """
        for enc in ("cp866", "cp1251", "utf-8"):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        # Финальный fallback с заменой неразбираемых символов
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _row_output_to_dict(output: str) -> ListRac:
        result = []
        for block in output.split("\n\n"):
            if block:
                dict_block = {}
                for line in block.split("\n"):
                    if ":" not in line:
                        continue
                    k, v = line.split(":", maxsplit=1)
                    k, v = k.strip(), v.strip("\"' \r")
                    dict_block[k] = v
                if dict_block:
                    result.append(dict_block)
        return result

    @staticmethod
    @UserDecorators.to_json
    def get_zabbix_lld(output: ListRac) -> ListRac:
        result = []
        for item in output:
            new_item = {}
            for x, y in item.items():
                new_item["{{#{}}}".format(x.upper())] = y
            result.append(new_item)
        return result

    @staticmethod
    def counter_session(session_list: ListRac, d_key: str, v_filter: str) -> int:
        return len([x for x in session_list if x[d_key] == v_filter])