"""Lector de precios de PriceSmart El Salvador.

Usa el mismo servicio de búsqueda público (Bloomreach Discovery) que usa el sitio
pricesmart.com/es-sv para mostrar sus categorías. No necesita iniciar sesión ni cuenta.
Sólo librería estándar de Python.

Uso:
    python3 pricesmart.py                       # club 6701 (Santa Elena), todas las categorías
    python3 pricesmart.py --club 6704           # otro club
    python3 pricesmart.py --categorias G10D03009 --salida salida.json   # prueba rápida

Buenas maneras: hace pocas peticiones, con pausa entre ellas, una vez al día.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://core.dxpapi.com/api/v1/core/"
SITIO = "https://www.pricesmart.com/es-sv"
# Datos públicos que el propio sitio entrega a cada visitante (ver su configuración).
ACCOUNT_ID = "7024"
AUTH_KEY = "ev7libhybjg5h1d1"
DOMAIN_KEY = "pricesmart_bloomreach_io_es"
VIEW_ID = "SV"
PAIS = "SV"
CLUBES = {"6701": "Santa Elena", "6702": "Los Héroes", "6703": "San Miguel", "6704": "Santa Ana"}
CATEGORIAS_SEMILLA = ["G10D03"]  # Alimentos; se usa si no se pueden descubrir las demás
PAUSA_SEG = 1.0
FILAS = 100


def campos(club: str) -> str:
    """Campos a pedir. El precio y el inventario dependen del club (sufijo _SV_<club>)."""
    sufijo = f"{PAIS}_{club}"
    nombres = ["pid", "title", "brand", "slug", "skuid", "currency", "fractionDigits", "thumb_image",
               f"price_{PAIS}", f"price_{sufijo}", f"availability_{sufijo}", f"inventory_{sufijo}"]
    return ",".join(nombres)


class ErrorAPI(RuntimeError):
    """Error de cliente (4xx) devuelto por la API: no tiene sentido reintentar."""


def pedir(params: dict, intentos: int = 3) -> dict:
    base = {
        "account_id": ACCOUNT_ID,
        "auth_key": AUTH_KEY,
        "domain_key": DOMAIN_KEY,
        "view_id": VIEW_ID,
        "request_id": str(random.randint(10**12, 10**13 - 1)),
        "_br_uid_2": "uid=" + str(random.randint(10**12, 10**13 - 1)),
        "url": SITIO,
        "request_type": "search",
    }
    base.update(params)
    url = API + "?" + urllib.parse.urlencode(base)
    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "comparador-precios-sv/0.1 (proyecto personal; 1 consulta diaria)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "replace")[:300].replace("\n", " ")
            if 400 <= e.code < 500 and e.code != 429:
                raise ErrorAPI(f"HTTP {e.code} con parámetros {sorted(params)}: {cuerpo}") from None
            ultimo = f"HTTP {e.code}: {cuerpo}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            ultimo = e
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"Falló la consulta a PriceSmart tras {intentos} intentos: {ultimo}")


def _raices(respuesta: dict) -> list[str]:
    cats = respuesta.get("facet_counts", {}).get("facet_fields", {}).get("category", [])
    return [c["cat_id"] for c in cats if not c.get("parent")]


def categorias_de_archivo(ruta: str = "categorias.txt") -> list[str]:
    """Lista manual opcional: un ID de categoría por línea (# para comentarios)."""
    try:
        with open(ruta, encoding="utf-8") as f:
            return [l.split("#")[0].strip() for l in f if l.split("#")[0].strip()]
    except FileNotFoundError:
        return []


def descubrir_categorias(maximo: int = 80) -> list[str]:
    """Departamentos (categorías de primer nivel). Dos intentos: facetas de una búsqueda
    general y, si falla, un barrido de los códigos G10D01..G10D<maximo>."""
    try:
        r = pedir({"search_type": "keyword", "q": "*", "rows": "1", "start": "0", "fl": "pid"})
        raices = _raices(r)
        if len(raices) > 1:
            return raices
        print("  aviso: la búsqueda general no devolvió varios departamentos; hago el barrido",
              file=sys.stderr)
    except ErrorAPI as e:
        print(f"  aviso: búsqueda general no disponible ({e}); hago el barrido", file=sys.stderr)

    encontradas: list[str] = []
    for n in range(1, maximo + 1):
        cid = f"G10D{n:02d}"
        try:
            r = pedir({"search_type": "category", "q": cid, "rows": "1", "start": "0", "fl": "pid"})
        except ErrorAPI:
            continue
        if r.get("response", {}).get("numFound", 0) > 0 and cid in r.get("category_map", {}):
            encontradas.append(cid)
        time.sleep(0.3)
    if not encontradas:
        print("  aviso: el barrido no encontró nada; uso la categoría semilla", file=sys.stderr)
    return encontradas or list(CATEGORIAS_SEMILLA)


def productos_de_categoria(cat: str, club: str, max_paginas: int = 60) -> list[dict]:
    docs: list[dict] = []
    inicio = 0
    for _ in range(max_paginas):
        r = pedir({"search_type": "category", "q": cat, "rows": str(FILAS),
                   "start": str(inicio), "fl": campos(club)})
        resp = r.get("response", {})
        lote = resp.get("docs", [])
        docs.extend(lote)
        total = resp.get("numFound", 0)
        inicio += len(lote)
        if not lote or inicio >= total:
            break
        time.sleep(PAUSA_SEG)
    return docs


def _primero(doc: dict, claves: list[str]):
    for k in claves:
        v = doc.get(k)
        if v not in (None, "", 0, 0.0):
            return v
    return None


def _a_dolares(valor, doc: dict) -> float | None:
    """La API entrega los precios en centavos (1099.0 = $10.99). fractionDigits indica cuántos."""
    if valor is None:
        return None
    try:
        digitos = int(doc.get("fractionDigits", 2))
    except (TypeError, ValueError):
        digitos = 2
    return round(float(valor) / (10 ** digitos), 2)


def normalizar(doc: dict, club: str) -> dict:
    """Convierte un documento de la API en una fila simple."""
    sufijo = f"{PAIS}_{club}"
    precio = _a_dolares(_primero(doc, [f"price_{sufijo}", f"price_{PAIS}", "price"]), doc)
    inventario = doc.get(f"inventory_{sufijo}")
    disponible = str(doc.get(f"availability_{sufijo}", "")).lower() == "true"
    return {
        "tienda": "PriceSmart",
        "club": CLUBES.get(club, club),
        "pid": doc.get("pid"),
        "nombre": (doc.get("title") or "").strip(),
        "marca": doc.get("brand"),
        "precio": precio,
        "moneda": doc.get("currency") or "USD",
        "slug": doc.get("slug"),
        "imagen": doc.get("thumb_image"),
        "en_stock": (inventario == "in stock") if inventario else None,
        "vendido_en_club": disponible,
        "requiere_membresia": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--club", default="6702", choices=sorted(CLUBES))
    ap.add_argument("--categorias", nargs="*", help="IDs de categoría (por defecto: se descubren)")
    ap.add_argument("--salida", default="data/pricesmart.json")
    ap.add_argument("--desde-archivo", help="Procesa una respuesta guardada (sin conectarse)")
    args = ap.parse_args()

    vistos: dict[str, dict] = {}
    if args.desde_archivo:
        with open(args.desde_archivo, encoding="utf-8") as f:
            for d in json.load(f)["response"]["docs"]:
                fila = normalizar(d, args.club)
                vistos[fila["pid"]] = fila
    else:
        cats = args.categorias or categorias_de_archivo() or descubrir_categorias()
        print(f"Club {args.club} ({CLUBES[args.club]}); categorías: {', '.join(cats)}")
        for cat in cats:
            docs = productos_de_categoria(cat, args.club)
            print(f"  {cat}: {len(docs)} productos")
            for d in docs:
                fila = normalizar(d, args.club)
                if fila["pid"] and fila["pid"] not in vistos:
                    vistos[fila["pid"]] = fila
            time.sleep(PAUSA_SEG)

    filas = list(vistos.values())
    con_precio = [f for f in filas if f["precio"]]
    print(f"Total únicos: {len(filas)}; con precio: {len(con_precio)}")
    if filas and not con_precio:
        raise SystemExit("Ningún producto trae precio: revisar los nombres de campos del club.")

    import os
    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump({"actualizado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   "tienda": "PriceSmart", "club": CLUBES[args.club], "productos": filas},
                  f, ensure_ascii=False, indent=1)
    print(f"Guardado en {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
