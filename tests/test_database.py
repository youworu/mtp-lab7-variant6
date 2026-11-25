"""Проверки запросов на настоящей базе SQLite."""

import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

import database


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = database.connect(":memory:")
        self.addCleanup(self.connection.close)
        database.create_schema(self.connection)

    def test_added_book_uses_existing_author(self) -> None:
        author = "Рэй Брэдбери"
        for title in ("Вино из одуванчиков", "451° по Фаренгейту"):
            self.assertTrue(database.add_book(self.connection, title, author))

        authors = self.connection.execute("SELECT name FROM authors").fetchall()
        self.assertEqual(authors, [(author,)])

    def test_repeated_book_stays_single(self) -> None:
        database.add_book(self.connection, "Солярис", "Станислав Лем")

        self.assertFalse(database.add_book(self.connection, "Солярис", "Станислав Лем"))
        self.assertEqual(len(database.list_books(self.connection)), 1)

    def test_join_returns_each_book_with_its_author(self) -> None:
        database.add_book(self.connection, "Солярис", "Станислав Лем")
        database.add_book(self.connection, "Машина времени", "Герберт Уэллс")

        self.assertEqual(
            database.list_books(self.connection),
            [("Машина времени", "Герберт Уэллс"), ("Солярис", "Станислав Лем")],
        )

    def test_empty_title_or_author_is_rejected_before_insertion(self) -> None:
        for title, author in (("", "Автор"), ("Книга", " ")):
            with self.subTest(title=title, author=author):
                with self.assertRaises(ValueError):
                    database.add_book(self.connection, title, author)

        authors = self.connection.execute("SELECT name FROM authors").fetchall()
        self.assertEqual(authors, [])
        self.assertEqual(database.list_books(self.connection), [])

    def test_title_and_author_with_apostrophes(self) -> None:
        title, author = "O'Connor's Stories", "Flannery O'Connor"

        database.add_book(self.connection, title, author)

        self.assertEqual(database.find_books(self.connection, title), [(title, author)])

    def test_search_uses_full_title_and_case(self) -> None:
        database.add_book(self.connection, "Машина времени", "Герберт Уэллс")
        database.add_book(self.connection, "Машина времени", "Другой автор")
        database.add_book(self.connection, "Машина времени. Сборник", "Герберт Уэллс")

        self.assertEqual(
            database.find_books(self.connection, "Машина времени"),
            [("Машина времени", "Герберт Уэллс"), ("Машина времени", "Другой автор")],
        )
        self.assertEqual(database.find_books(self.connection, "машина времени"), [])
        self.assertEqual(database.find_books(self.connection, "Машина"), [])

    def test_sqlite_chooses_title_index(self) -> None:
        database.add_book(self.connection, "Солярис", "Станислав Лем")

        plan = database.explain_search(self.connection, "Солярис")

        self.assertTrue(
            any("SEARCH books" in step and "idx_books_title" in step for step in plan),
            plan,
        )

    def test_book_requires_existing_author(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO books (title, author_id) VALUES (?, ?)", ("Солярис", 999)
            )

    def test_transaction_rolls_back_book_and_author(self) -> None:
        with self.assertRaises(RuntimeError), self.connection:
            database.add_book(self.connection, "Солярис", "Станислав Лем")
            raise RuntimeError("Отмена транзакции")

        self.assertEqual(database.list_books(self.connection), [])
        authors = self.connection.execute("SELECT name FROM authors").fetchall()
        self.assertEqual(authors, [])

    def test_committed_book_survives_reopening(self) -> None:
        with TemporaryDirectory() as folder:
            path = str(Path(folder) / "library.sqlite3")
            with closing(database.connect(path)) as connection, connection:
                database.create_schema(connection)
                database.add_book(connection, "Солярис", "Станислав Лем")

            with closing(database.connect(path)) as connection:
                database.create_schema(connection)
                self.assertEqual(
                    database.list_books(connection), [("Солярис", "Станислав Лем")]
                )


if __name__ == "__main__":
    unittest.main()
