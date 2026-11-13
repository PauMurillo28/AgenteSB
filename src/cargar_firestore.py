"""Carga (o recarga) base_conocimiento.md en Firestore. Se corre una vez desde la raíz:
   PowerShell:  $env:FIREBASE_CREDENTIALS_FILE="C:\\ruta\\fuera\\del\\proyecto\\clave.json"
                python src\\cargar_firestore.py
Cada tema queda como un documento de la colección 'base_conocimiento'."""
import datetime
import os
import pathlib
import re
import unicodedata

MD = pathlib.Path(__file__).parent / "base_conocimiento.md"


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:80]


def parsear(texto: str) -> list:
    filas, seccion, orden = [], "General", 0
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("# "):
            continue
        if linea.startswith("## "):
            seccion = linea[3:].strip()
            continue
        if linea.startswith("- ") and ": " in linea:
            tema, contenido = linea[2:].split(": ", 1)
        elif linea.startswith("|"):
            c = [x.strip() for x in linea.strip("|").split("|")]
            if len(c) < 4 or c[0] in ("Sede", "---") or set(c[0]) <= {"-"}:
                continue
            tema = c[0]
            contenido = f"Dirección: {c[1]}. Horario: {c[2]}. Servicios: {c[3]}."
        elif not linea.startswith("-"):
            tema, contenido = "Red Salud Andina", linea
        else:
            continue
        orden += 1
        filas.append({"seccion": seccion, "tema": tema, "contenido": contenido,
                      "orden": orden, "activo": True})
    return filas


if __name__ == "__main__":
    filas = parsear(MD.read_text(encoding="utf-8"))
    print(f"{len(filas)} documentos a cargar")
    import firebase_admin
    from firebase_admin import credentials, firestore

    firebase_admin.initialize_app(credentials.Certificate(os.environ["FIREBASE_CREDENTIALS_FILE"]))
    db = firestore.client()
    lote = db.batch()
    for f in filas:
        f["actualizado"] = datetime.datetime.now(datetime.timezone.utc)
        lote.set(db.collection("base_conocimiento").document(slug(f["seccion"] + " " + f["tema"])), f)
    lote.commit()
    print("Listo. Revise la colección 'base_conocimiento' en la consola de Firebase.")
