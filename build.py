"""Une los datos de todas las tiendas (data/*.json) y genera la página docs/index.html.

Para cada producto interpreta su tamaño (comparador.py) y calcula $/kg, $/L y $/unidad.
Para agregar una tienda nueva basta con dejar su archivo en data/ con el mismo formato.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os

from comparador import interpretar


def describir(t) -> str:
    partes = []
    if t.masa_g:
        partes.append(f"{t.masa_g / 1000:.3g} kg" if t.masa_g >= 1000 else f"{t.masa_g:.3g} g")
    if t.volumen_ml:
        partes.append(f"{t.volumen_ml / 1000:.3g} L" if t.volumen_ml >= 1000 else f"{t.volumen_ml:.3g} ml")
    if t.unidades:
        partes.append(f"{t.unidades:.0f} un")
    return " · ".join(partes)


def construir(carpeta_datos: str = "data") -> dict:
    productos, tiendas, actualizados = [], set(), []
    for archivo in sorted(glob.glob(os.path.join(carpeta_datos, "*.json"))):
        with open(archivo, encoding="utf-8") as f:
            d = json.load(f)
        actualizados.append(d.get("actualizado", ""))
        for p in d["productos"]:
            if not p.get("precio"):
                continue
            t = interpretar(p["nombre"])
            pu = {}
            for dim in t.dimensiones:
                v = t.precio_unitario(p["precio"], dim)
                if v is not None:
                    pu[dim] = round(v, 4)
            tiendas.add(p["tienda"])
            productos.append({
                "t": p["tienda"] + (f" · {p['club']}" if p.get("club") else ""),
                "n": p["nombre"],
                "p": p["precio"],
                "pu": pu,
                "dp": t.dimension_principal,
                "tam": describir(t),
                "amb": t.ambiguo,
                "nota": " ".join(t.notas) if t.ambiguo else "",
                "stock": p.get("en_stock"),
                "mem": bool(p.get("requiere_membresia")),
                "url": p.get("url"),
            })
    return {
        "actualizado": max(actualizados) if actualizados else "",
        "tiendas": sorted(tiendas),
        "productos": productos,
    }


def main() -> None:
    datos = construir()
    with open("plantilla.html", encoding="utf-8") as f:
        html = f.read()
    blob = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("/*DATOS*/null", blob)
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"docs/index.html: {len(datos['productos'])} productos de {', '.join(datos['tiendas'])}")


if __name__ == "__main__":
    main()
