from app import app


EXPECTED = [
    ("/", 200),
    ("/api/health", 200),
    ("/api/templates", 200),
    ("/api/templates/mca", 200),
    ("/api/templates/unknown", 404),
    ("/api/quick-templates", 200),
    ("/api/rest-options", 200),
    ("/api/search-keywords", 200),
    ("/server/app.py", 404),
    ("/server/nasukeru.db", 404),
    ("/.gitignore", 404),
]


def main():
    client = app.test_client()
    failures = []
    for path, expected_status in EXPECTED:
        response = client.get(path)
        status = response.status_code
        print(f"{status:3} {path}")
        if status != expected_status:
            failures.append((path, expected_status, status))
    if failures:
        details = ", ".join(
            f"{path}: expected {expected}, got {actual}"
            for path, expected, actual in failures
        )
        raise SystemExit(f"Smoke test failed: {details}")


if __name__ == "__main__":
    main()
