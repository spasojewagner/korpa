import json
from pathlib import Path

from korpa_api.main import app


def export(destination: Path = Path("apps/web/src/api/openapi.json")) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = dict(app.openapi())
    document["paths"] = {
        path: value for path, value in document["paths"].items() if path != "/graphql"
    }
    destination.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    export()
