# -*- coding: utf-8 -*-
"""
Скрипт для запуска тестов с различными опциями
Использование: python run_tests.py [опции]
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd):
    """Запускает команду и возвращает результат"""
    print(f"\n{'='*60}")
    print(f"Выполнение: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Запуск тестов AutoService")

    parser.add_argument("--all", action="store_true", help="Запустить все тесты")

    parser.add_argument(
        "--core", action="store_true", help="Запустить тесты клиентского модуля (core)"
    )

    parser.add_argument(
        "--admin",
        action="store_true",
        help="Запустить тесты менеджерского модуля (admin_panel)",
    )

    parser.add_argument(
        "--integration", action="store_true", help="Запустить интеграционные тесты"
    )

    parser.add_argument(
        "--performance", action="store_true", help="Запустить тесты производительности"
    )

    parser.add_argument(
        "--security", action="store_true", help="Запустить тесты безопасности"
    )

    parser.add_argument(
        "--coverage", action="store_true", help="Запустить с измерением покрытия кода"
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Подробный вывод (verbosity=2)"
    )

    parser.add_argument(
        "--keepdb", action="store_true", help="Сохранить тестовую базу данных"
    )

    parser.add_argument(
        "--parallel", type=int, metavar="N", help="Запустить в N параллельных процессов"
    )

    parser.add_argument(
        "--fast", action="store_true", help="Быстрый режим (parallel=auto, keepdb)"
    )

    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return 0

    base_cmd = ["python", "manage.py", "test"]

    test_targets = []

    if args.core:
        test_targets.append("core")

    if args.admin:
        test_targets.append("admin_panel")

    if args.integration:
        test_targets.append("tests_integration")

    if args.performance:
        test_targets.append("tests_performance")

    if args.security:
        test_targets.append("tests_integration.SecurityValidationTestCase")

    if args.all or not test_targets:
        test_targets = []

    if args.coverage:
        cmd = [
            "coverage",
            "run",
            "--source=core,admin_panel,loyalty_program,payments,notifications",
        ]
        cmd.extend(["manage.py", "test"])
    else:
        cmd = base_cmd.copy()

    cmd.extend(test_targets)

    if args.verbose:
        cmd.append("--verbosity=2")

    if args.keepdb or args.fast:
        cmd.append("--keepdb")

    if args.parallel:
        cmd.append(f"--parallel={args.parallel}")
    elif args.fast:
        cmd.append("--parallel=auto")

    returncode = run_command(cmd)

    if args.coverage and returncode == 0:
        print("\n" + "=" * 60)
        print("Генерация отчета о покрытии кода...")
        print("=" * 60 + "\n")

        subprocess.run(["coverage", "report"])

        print("\n" + "=" * 60)
        print("Генерация HTML отчета...")
        print("=" * 60 + "\n")

        subprocess.run(["coverage", "html"])

        print("\n" + "=" * 60)
        print("HTML отчет создан в папке htmlcov/")
        print("Откройте htmlcov/index.html в браузере")
        print("=" * 60 + "\n")

    return returncode


if __name__ == "__main__":
    sys.exit(main())
