"""Таблицы и запросы каталога книг."""

import sqlite3


BOOKS_QUERY = """
    SELECT books.title, authors.name
    FROM books
    JOIN authors ON authors.id = books.author_id
"""
BOOK_ORDER = " ORDER BY books.title, authors.name"


def connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            author_id INTEGER NOT NULL REFERENCES authors(id),
            UNIQUE (author_id, title)
        )
    """)


def add_book(connection: sqlite3.Connection, title: str, author: str) -> bool:
    """Добавляет книгу и при необходимости автора. Возвращает признак вставки."""
    title, author = title.strip(), author.strip()
    if not title or not author:
        raise ValueError("Укажите название книги и имя автора")

    connection.execute(
        "INSERT INTO authors (name) VALUES (?) ON CONFLICT (name) DO NOTHING",
        (author,),
    )
    result = connection.execute("""
        INSERT INTO books (title, author_id)
        SELECT ?, id FROM authors WHERE name = ?
        ON CONFLICT (author_id, title) DO NOTHING
    """, (title, author))
    return result.rowcount == 1


def list_books(connection: sqlite3.Connection) -> list[tuple[str, str]]:
    return connection.execute(BOOKS_QUERY + BOOK_ORDER).fetchall()
