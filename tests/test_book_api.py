import csv
import io
import json

import pytest

from tests.factories import auth_headers, register_and_login, valid_book_payload

pytestmark = pytest.mark.asyncio


async def create_book(client, token: str, **overrides) -> dict:
    resp = await client.post(
        "/api/v1/books/",
        json=valid_book_payload(**overrides),
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestAuthEnforcement:
    async def test_create_without_token_returns_401(self, client):
        resp = await client.post("/api/v1/books/", json=valid_book_payload())
        assert resp.status_code == 401

    async def test_patch_without_token_returns_401(self, client):
        resp = await client.patch(
            "/api/v1/books/00000000-0000-0000-0000-000000000000",
            json={},
        )
        assert resp.status_code == 401

    async def test_delete_without_token_returns_401(self, client):
        resp = await client.delete("/api/v1/books/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401

    async def test_list_without_token_returns_401(self, client):
        resp = await client.get("/api/v1/books/")
        assert resp.status_code == 401


class TestErrorContract:
    async def test_404_has_unified_error_shape(self, client):
        token = await register_and_login(client)
        resp = await client.get(
            "/api/v1/books/00000000-0000-0000-0000-000000000001",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    async def test_422_has_unified_error_shape(self, client):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/v1/books/",
            json={"title": ""},
            headers=auth_headers(token),
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]


class TestObservability:
    async def test_response_has_x_request_id(self, client):
        resp = await client.get("/")
        assert "x-request-id" in resp.headers

    async def test_x_request_id_differs_per_request(self, client):
        r1 = await client.get("/")
        r2 = await client.get("/")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


class TestBookCRUD:
    async def test_create_returns_201_with_id(self, client):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/v1/books/",
            json=valid_book_payload(),
            headers=auth_headers(token),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["title"] == "The Pragmatic Programmer"

    async def test_get_returns_created_book(self, client):
        token = await register_and_login(client)
        book = await create_book(client, token)
        resp = await client.get(
            f"/api/v1/books/{book['id']}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == book["id"]

    async def test_get_nonexistent_returns_404(self, client):
        token = await register_and_login(client)
        resp = await client.get(
            "/api/v1/books/00000000-0000-0000-0000-000000000001",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_patch_updates_field(self, client):
        token = await register_and_login(client)
        book = await create_book(client, token)
        resp = await client.patch(
            f"/api/v1/books/{book['id']}",
            json={"title": "Updated Title"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    async def test_delete_returns_204(self, client):
        token = await register_and_login(client)
        book = await create_book(client, token)
        resp = await client.delete(
            f"/api/v1/books/{book['id']}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 204

    async def test_get_after_delete_returns_404(self, client):
        token = await register_and_login(client)
        book = await create_book(client, token)
        await client.delete(
            f"/api/v1/books/{book['id']}",
            headers=auth_headers(token),
        )
        resp = await client.get(
            f"/api/v1/books/{book['id']}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404


class TestInvariants:
    async def test_empty_title_returns_422(self, client):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/v1/books/",
            json=valid_book_payload(title=""),
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_missing_author_returns_422(self, client):
        token = await register_and_login(client)
        payload = valid_book_payload()
        payload.pop("author")
        resp = await client.post(
            "/api/v1/books/",
            json=payload,
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_year_too_old_returns_422(self, client):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/v1/books/",
            json=valid_book_payload(year=1799),
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_year_in_future_returns_422(self, client):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/v1/books/",
            json=valid_book_payload(year=9999),
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_invalid_genre_returns_422(self, client):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/v1/books/",
            json=valid_book_payload(genre="not_a_genre"),
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_duplicate_book_returns_409_not_500(self, client):
        token = await register_and_login(client)
        payload = valid_book_payload(title="Unique Title XYZ")
        await client.post(
            "/api/v1/books/",
            json=payload,
            headers=auth_headers(token),
        )
        resp = await client.post(
            "/api/v1/books/",
            json=payload,
            headers=auth_headers(token),
        )
        assert resp.status_code == 409
        assert "error" in resp.json()


class TestBookList:
    async def test_list_returns_created_books(self, client):
        token = await register_and_login(client)
        await create_book(client, token, title="Book Alpha")
        await create_book(client, token, title="Book Beta")
        resp = await client.get("/api/v1/books/", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        titles = [b["title"] for b in body["items"]]
        assert "Book Alpha" in titles
        assert "Book Beta" in titles

    async def test_pagination_limit(self, client):
        token = await register_and_login(client)
        await create_book(client, token, title="Paginate A")
        await create_book(client, token, title="Paginate B")
        resp = await client.get(
            "/api/v1/books/?limit=1&offset=0",
            headers=auth_headers(token),
        )
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["total"] >= 2

    async def test_filter_by_genre(self, client):
        token = await register_and_login(client)
        await create_book(client, token, title="Science Book", genre="science")
        await create_book(client, token, title="Fiction Book", genre="fiction")
        resp = await client.get(
            "/api/v1/books/?genre=science",
            headers=auth_headers(token),
        )
        body = resp.json()
        assert all(b["genre"] == "science" for b in body["items"])

    async def test_sort_by_year_asc(self, client):
        token = await register_and_login(client)
        await create_book(client, token, title="Old Book", year=1900)
        await create_book(client, token, title="New Book", year=2020)
        resp = await client.get(
            "/api/v1/books/?sort=year",
            headers=auth_headers(token),
        )
        body = resp.json()
        years = [b["year"] for b in body["items"]]
        assert years == sorted(years)


class TestBulkImport:
    def _json_file(self, books: list[dict]) -> tuple:
        content = json.dumps(books).encode()
        return ("books.json", content, "application/json")

    def _csv_file(self, books: list[dict]) -> tuple:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=books[0].keys())
        writer.writeheader()
        writer.writerows(books)
        return ("books.csv", buf.getvalue().encode(), "text/csv")

    async def test_json_import_succeeds(self, client):
        token = await register_and_login(client)
        books = [valid_book_payload(title=f"Import Book {i}") for i in range(3)]
        resp = await client.post(
            "/api/v1/books/import",
            files={"file": self._json_file(books)},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["imported"] == 3
        assert body["errors"] == []

    async def test_csv_import_succeeds(self, client):
        token = await register_and_login(client)
        books = [valid_book_payload(title=f"CSV Book {i}") for i in range(2)]
        resp = await client.post(
            "/api/v1/books/import",
            files={"file": self._csv_file(books)},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 2

    async def test_one_invalid_row_imports_nothing(self, client):
        token = await register_and_login(client)
        books = [
            valid_book_payload(title="Good Book 1"),
            valid_book_payload(title="Good Book 2"),
            {"title": "", "author": "X", "genre": "fiction", "year": 2020},
        ]
        resp = await client.post(
            "/api/v1/books/import",
            files={"file": self._json_file(books)},
            headers=auth_headers(token),
        )
        body = resp.json()
        assert body["imported"] == 0
        assert len(body["errors"]) > 0

        list_resp = await client.get("/api/v1/books/", headers=auth_headers(token))
        titles = [b["title"] for b in list_resp.json()["items"]]
        assert "Good Book 1" not in titles

    async def test_duplicate_import_returns_errors(self, client):
        token = await register_and_login(client)
        books = [valid_book_payload(title="Duplicate Import Test")]

        r1 = await client.post(
            "/api/v1/books/import",
            files={"file": self._json_file(books)},
            headers=auth_headers(token),
        )
        assert r1.json()["imported"] == 1

        r2 = await client.post(
            "/api/v1/books/import",
            files={"file": self._json_file(books)},
            headers=auth_headers(token),
        )
        assert r2.json()["imported"] == 0
        assert len(r2.json()["errors"]) > 0

    async def test_valid_row_after_duplicate_is_not_persisted(self, client):
        token = await register_and_login(client)
        await create_book(client, token, title="Already Exists")

        books = [
            valid_book_payload(title="Already Exists"),
            valid_book_payload(title="Brand New Book"),
        ]
        resp = await client.post(
            "/api/v1/books/import",
            files={"file": self._json_file(books)},
            headers=auth_headers(token),
        )
        assert resp.json()["imported"] == 0
        assert len(resp.json()["errors"]) > 0

        list_resp = await client.get("/api/v1/books/", headers=auth_headers(token))
        titles = [b["title"] for b in list_resp.json()["items"]]
        assert "Brand New Book" not in titles


class TestExport:
    async def test_json_export_content_type(self, client):
        token = await register_and_login(client)
        resp = await client.get(
            "/api/v1/books/export?format=json",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

    async def test_csv_export_content_type(self, client):
        token = await register_and_login(client)
        resp = await client.get(
            "/api/v1/books/export?format=csv",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    async def test_json_export_contains_created_book(self, client):
        token = await register_and_login(client)
        await create_book(client, token, title="Exported Book XYZ")
        resp = await client.get(
            "/api/v1/books/export?format=json",
            headers=auth_headers(token),
        )
        books = json.loads(resp.content)
        titles = [b["title"] for b in books]
        assert "Exported Book XYZ" in titles

    async def test_csv_export_has_header_row(self, client):
        token = await register_and_login(client)