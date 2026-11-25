"""Консольные команды каталога."""

import argparse
from contextlib import closing
import sqlite3

import database


def print_books(books: list[tuple[str, str]]) -> None:
    if not books:
        print("Книги не найдены.")
    for title, author in books:
        print(f"{title} — {author}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Каталог книг на SQLite")
    parser.add_argument("--db", default="library.sqlite3", help="Путь к базе")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Добавить книгу")
    add.add_argument("title", help="Название книги")
    add.add_argument("author", help="Имя автора")
    commands.add_parser("list", help="Вывести книги с авторами")
    args = parser.parse_args()

    try:
        with closing(database.connect(args.db)) as connection, connection:
            database.create_schema(connection)
            if args.command == "add":
                added = database.add_book(connection, args.title, args.author)
            else:
                books = database.list_books(connection)
    except (ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Ошибка каталога: {error}\n")

    if args.command == "add":
        print("Книга добавлена." if added else "Книга уже есть в каталоге.")
    else:
        print_books(books)


if __name__ == "__main__":
    main()
