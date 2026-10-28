"""Package Ciccio's generated work products into one easy-to-share ZIP and HTML index."""
from html import escape
from pathlib import Path
from urllib.parse import quote
import zipfile


def package_artifacts(output_dir="ciccio_output"):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in root.glob("*.md") if p.is_file())
    index = root / "index.html"
    zip_path = root / "ciccio-work-products.zip"

    links = []
    for path in files:
        name = path.name
        links.append(
            '<li><a href="' + escape(quote(name)) + '">' + escape(name) + '</a></li>'
        )
    if not links:
        body = "<p>In questo ciclo non sono stati creati deliverable Markdown.</p>"
    else:
        body = "<p>File prodotti in questo ciclo:</p><ul>" + "".join(links) + "</ul>"

    index.write_text(
        "<!doctype html><html lang=\"it\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Prodotti di lavoro Ciccio</title>"
        "<style>body{font:16px system-ui;max-width:760px;margin:3rem auto;padding:0 1rem;"
        "line-height:1.6}a{overflow-wrap:anywhere}</style></head><body>"
        "<h1>Prodotti di lavoro Ciccio</h1>"
        "<p>Materiali generati automaticamente. Verifica contenuti e fonti prima di condividerli o venderli.</p>"
        + body + "</body></html>",
        encoding="utf-8",
    )

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(index, arcname="index.html")
        for path in files:
            bundle.write(path, arcname=path.name)
    with zipfile.ZipFile(zip_path, "r") as bundle:
        bad = bundle.testzip()
        if bad:
            raise OSError("Archivio Ciccio non valido: " + bad)
    return {"index": index, "zip": zip_path, "files": len(files)}


if __name__ == "__main__":
    result = package_artifacts()
    print("Pacchetto Ciccio creato: " + str(result["zip"]) + " ("
          + str(result["files"]) + " file Markdown)")
