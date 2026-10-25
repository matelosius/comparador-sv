"""Pruebas del lector de PriceSmart con muestras reales devueltas por su API."""
import json

import pricesmart
from comparador import interpretar

SIN_PRECIO = json.load(open("fixtures/pricesmart_muestra.json", encoding="utf-8"))["response"]["docs"]
LOS_HEROES = json.load(open("fixtures/pricesmart_6702_muestra.json", encoding="utf-8"))["response"]["docs"]


def test_muestra_sin_campos_de_club_no_trae_precio():
    filas = [pricesmart.normalizar(d, "6701") for d in SIN_PRECIO]
    assert len(filas) == 12 and all(f["precio"] is None for f in filas)


def test_precios_en_centavos_pasan_a_dolares():
    filas = {f["pid"]: f for f in (pricesmart.normalizar(d, "6702") for d in LOS_HEROES)}
    assert filas["494711"]["precio"] == 10.99   # Krusteaz 3 Unidades
    assert filas["388043"]["precio"] == 18.49   # Aceite de oliva 2 L
    assert filas["781060"]["precio"] == 14.49   # Mayonesa Member's Selection 3.78 L


def test_inventario_del_club():
    filas = {f["pid"]: f for f in (pricesmart.normalizar(d, "6702") for d in LOS_HEROES)}
    assert filas["642190"]["en_stock"] is False  # Kraft Mayonesa: out of stock en Los Héroes
    assert filas["388043"]["en_stock"] is True


def test_fraction_digits_si_viene():
    doc = {"pid": "1", "title": "X 1 L", "price_SV_6702": 1234.0, "fractionDigits": 2}
    assert pricesmart.normalizar(doc, "6702")["precio"] == 12.34
    doc["fractionDigits"] = 0
    assert pricesmart.normalizar(doc, "6702")["precio"] == 1234.0


def test_cae_al_precio_pais_si_el_club_no_lo_tiene():
    doc = {"pid": "1", "title": "X 1 L", "price_SV": 500.0}
    assert pricesmart.normalizar(doc, "6702")["precio"] == 5.0


def test_campos_incluyen_sufijo_del_club():
    c = pricesmart.campos("6704").split(",")
    assert {"price_SV_6704", "inventory_SV_6704", "availability_SV_6704", "title", "fractionDigits"} <= set(c)


def test_precio_por_litro_con_datos_reales():
    """Aceite de oliva Member's Selection 2 L a $18.49 y mayonesa 3.78 L a $14.49 (Los Héroes)."""
    filas = {f["pid"]: f for f in (pricesmart.normalizar(d, "6702") for d in LOS_HEROES)}
    aceite = interpretar(filas["388043"]["nombre"]).precio_unitario(filas["388043"]["precio"], "volumen")
    mayo = interpretar(filas["781060"]["nombre"]).precio_unitario(filas["781060"]["precio"], "volumen")
    assert abs(aceite - 9.245) < 0.01 and abs(mayo - 3.833) < 0.01


def test_todos_los_titulos_tienen_tamano_interpretable():
    for d in SIN_PRECIO + LOS_HEROES:
        t = interpretar(d["title"])
        assert t.dimension_principal and not t.ambiguo, (d["title"], t.notas)


if __name__ == "__main__":
    fallos = 0
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            try:
                f(); print("OK   ", n)
            except Exception as e:  # noqa: BLE001
                fallos += 1; print("FALLA", n, repr(e)[:200])
    raise SystemExit(1 if fallos else 0)
