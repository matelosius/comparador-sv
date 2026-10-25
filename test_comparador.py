"""Pruebas con presentaciones reales vistas en AhorroSV (oct 2026)."""
try:
    import pytest
except ImportError:  # corre también sin pytest: python3 test_comparador.py
    class _Mark:
        @staticmethod
        def parametrize(nombres, casos):
            def deco(fn):
                fn._casos = casos
                return fn
            return deco

    class pytest:  # noqa: N801
        mark = _Mark()

from comparador import Oferta, comparar, interpretar


def aprox(a, b, tol=0.01):
    return abs(a - b) <= tol * max(abs(b), 1e-9)


# ---------------------------------------------------------------- medidas simples
@pytest.mark.parametrize("nombre, campo, esperado", [
    ("Aceite de Oliva Great Value Extra Virgen - 2.98 L", "volumen_ml", 2980),
    ("Aceite Great Value de oliva extra virgen - 754 ml", "volumen_ml", 754),
    ("Aceite Orisol Light Con Oliva - 3450 ml", "volumen_ml", 3450),
    ("Detergente Líquido Swift Original 9 L", "volumen_ml", 9000),
    ("Endulzante La Gretta Monk Fruit - 400 g", "masa_g", 400),
    ("Leche Pinito Dos Pinos en polvo vitaminada bolsa - 2200 g", "masa_g", 2200),
    ("Alimento Para Perro Dogstar Adulto 0.454 kg", "masa_g", 454),
    ("Protector Labial Kyss Fresa Vogue 4.8 g", "masa_g", 4.8),
    ("Super UV Sérum Garnier Protector Solar FPS50+ - 40ml", "volumen_ml", 40),
    ("Protector solar Nivea babies & kids FPS 50 - 200 ml", "volumen_ml", 200),
    ("Guindas Cherry Circus Bote 1.05 kg", "masa_g", 1050),
    ("Gaseosa Pepsi Mega Doble - 2500 ml", "volumen_ml", 2500),
])
def test_medidas_simples(nombre, campo, esperado):
    assert aprox(getattr(interpretar(nombre), campo), esperado)


def test_separador_decimal_y_miles():
    assert aprox(interpretar("Arroz 1,000 g").masa_g, 1000)
    assert aprox(interpretar("Frijoles 2,5 kg").masa_g, 2500)


def test_libra_precio_indicado_por_libra():
    t = interpretar("Puyazo de Res Don Cristobal - Precio Indicado Por Libra (454 g)")
    assert aprox(t.masa_g, 454)
    t = interpretar("Carne molida precio indicado por libra")
    assert aprox(t.masa_g, 453.592)


def test_libras_y_galones():
    assert aprox(interpretar("Azúcar 5 lb").masa_g, 2267.96)
    assert aprox(interpretar("Aceite 1 galón").volumen_ml, 3785.41)


# ---------------------------------------------------------------- onzas
def test_oz_peso_vs_fluida():
    assert aprox(interpretar("Cereal Kellogg's 12 oz").masa_g, 340.19)
    assert aprox(interpretar("Cereal 12 oz").masa_g, 340.19)
    assert aprox(interpretar("Jugo de naranja 12 oz").volumen_ml, 354.88)
    assert aprox(interpretar("Soda 12 fl oz").volumen_ml, 354.88)
    # la bandera explícita manda
    assert aprox(interpretar("Producto raro 8 oz", es_liquido=True).volumen_ml, 236.59)
    assert interpretar("Cereal 12 oz").ambiguo  # sin bandera se avisa


# ---------------------------------------------------------------- multiplicadores y packs
def test_multiplicadores_explicitos():
    assert aprox(interpretar("Cerveza 6 x 355 ml").volumen_ml, 2130)
    assert aprox(interpretar("Cerveza 355 ml x 6").volumen_ml, 2130)
    assert aprox(interpretar("Yogurt 12x120g").masa_g, 1440)
    assert aprox(interpretar("FOSFORO ZAZ 10 X 100 UNIDADES").unidades, 1000)


def test_pack_con_medida_por_envase():
    t = interpretar("Néctar Petit 12 Pack Surtido - 330 ml")
    assert aprox(t.volumen_ml, 3960)  # 330 ml cada uno
    assert t.ambiguo


def test_pack_con_medida_total():
    t = interpretar("Barras De Granola Great Value Almendras 6 PACK - 210 g")
    assert aprox(t.masa_g, 210)
    assert t.ambiguo
    t = interpretar("Mezcla Cocoa Mix 15 Pack - 300 g")
    assert aprox(t.masa_g, 300)
    t = interpretar("Sal de Ajo MAGGI® De La Huerta 12 Sobres - 60 g")
    assert aprox(t.masa_g, 60)


# ---------------------------------------------------------------- conteos
def test_panales_ignoran_rango_de_talla():
    t = interpretar("Pañales Pampers Swaddlers 360 Talla 3 7-13 kg - 70 Uds")
    assert t.masa_g is None and t.unidades == 70
    assert t.dimension_principal == "unidad"
    t = interpretar("Pañales Pampers Swaddlers 360 Talla 6 16+ kg - 44 Uds")
    assert t.masa_g is None and t.unidades == 44


def test_conteos_varios():
    assert interpretar("Papel Higiénico Rosal Morado, Triple Hoja - 32 Rollos").unidades == 32
    assert interpretar("Calzoncillo de Entrenamiento Pull-Ups Niña Talla 5T/6T - 48 Unidades").unidades == 48
    assert interpretar("Ropa Interior Desechable Goodnites Niña Talla L - 11 Unidades").unidades == 11
    assert interpretar("Huevos una docena").unidades == 12
    assert interpretar("Huevos media docena").unidades == 6


def test_pastillas_se_comparan_por_unidad():
    t = interpretar("S-Sudagrip Caramelos 6.5 Mg 100U")
    assert t.unidades == 100
    assert t.dimension_principal == "unidad"


def test_rango_de_piezas_no_cuenta():
    t = interpretar("Banano Hortifruti Por Libra - 2 a 4 Unidades, precio Indicado Por Libra (454 g)")
    assert aprox(t.masa_g, 454) and t.unidades is None


def test_sin_tamano():
    t = interpretar("Refrigeradora Oster OSMBG93PBV 3.3 pies cúbicos inoxidable")
    assert t.dimension_principal is None
    t = interpretar("Celular Poco C81 Pro 256gb")
    assert t.dimension_principal is None  # 256 GB no es peso


def test_lavadas_no_son_litros():
    t = interpretar("Detergente Líquido Tide Original 64 Lavadas - 2.48 L")
    assert aprox(t.volumen_ml, 2480)


# ---------------------------------------------------------------- comparación
def test_mismo_aceite_dos_tamanos_da_mismo_precio_por_litro():
    """Datos reales de AhorroSV: Great Value aceite de oliva, 2.98 L ($19.77) vs 754 ml ($5.00)."""
    res = comparar([
        Oferta("La Despensa de Don Juan", "Aceite de Oliva Great Value Extra Virgen - 2.98 L", 19.77),
        Oferta("Walmart", "Aceite Great Value de oliva extra virgen - 754 ml", 5.00),
    ])
    assert res[0].etiqueta == "$/L"
    assert aprox(res[0].precio_unitario, 6.634, 0.01)
    assert aprox(res[1].precio_unitario, 6.631, 0.01)


def test_ordena_y_calcula_porcentaje():
    res = comparar([
        Oferta("A", "Leche 1 L", 2.00),
        Oferta("B", "Leche 2 L", 3.00),
        Oferta("C", "Leche 500 ml", 1.50),
    ])
    assert [r.oferta.tienda for r in res] == ["B", "A", "C"]
    assert res[0].sobre_el_mejor_pct == 0
    assert aprox(res[1].sobre_el_mejor_pct, 33.33, 0.01)


def test_pricesmart_avisa_membresia():
    res = comparar([
        Oferta("PriceSmart", "Aceite Kirkland 3 L", 15.00),
        Oferta("Walmart", "Aceite 1 L", 6.00),
    ])
    ps = next(r for r in res if r.oferta.tienda == "PriceSmart")
    assert any("membresía" in a for a in ps.advertencias)


def test_producto_incomparable_va_al_final():
    res = comparar([
        Oferta("A", "Aceite 1 L", 5.00),
        Oferta("B", "Aceite en presentación especial", 4.00),
    ])
    assert res[-1].oferta.tienda == "B"
    assert res[-1].precio_unitario is None
    assert res[-1].advertencias


def test_dimension_comun_cuando_una_tiene_ambas():
    # Una tienda lista peso + unidades, la otra sólo unidades: se compara por unidad
    res = comparar([
        Oferta("A", "Galletas 12 unidades - 300 g", 3.00),
        Oferta("B", "Galletas 24 unidades", 5.00),
    ])
    assert res[0].dimension == "unidad"
    assert res[0].oferta.tienda == "B"


# ---------------------------------------------------------------- formato PriceSmart (títulos reales)
def test_pricesmart_n_unidades_barra_es_por_unidad():
    t = interpretar("Krusteaz Mezcla para Pasteles y Muffins Sabor Rollo de Canela con Toppings 3 Unidades / 411 g / 14.5 oz")
    assert aprox(t.masa_g, 1233, 0.005) and t.unidades == 3 and not t.ambiguo
    t = interpretar("Bertolli Salsa para Pasta 3 Unidades / 680 g / 24 oz")
    assert aprox(t.masa_g, 2040) and not t.ambiguo
    t = interpretar("Kraft Mayonesa de Huevos de Gallina Libres 2 Unidades / 887 mL / 30 oz")
    assert aprox(t.volumen_ml, 1774)


def test_pricesmart_equivalencias_oz_no_son_ambiguas():
    for nombre, campo, esperado in [
        ("Kraft Mayonesa Real 3.78 L / 1 gal", "volumen_ml", 3780),
        ("Member's Selection Mayonesa Cremosa con Sabor Natural 3.78 L / 128 oz", "volumen_ml", 3780),
        ("Member's Selection Aceite de Coco Virgen Orgánico 1.65 L / 56 oz", "volumen_ml", 1650),
        ("Krusteaz Mezcla en Polvo para Preparar Pancakes 4.53 kg / 10 lb", "masa_g", 4530),
        ("Badia Sazonador Completo - Combinación de Hierbas y Especias 793.8 g / 1.75 lb", "masa_g", 793.8),
        ("Badia Ajo Granulado 680 g / 24 oz ", "masa_g", 680),
    ]:
        t = interpretar(nombre)
        assert aprox(getattr(t, campo), esperado, 0.01), nombre
        assert not t.ambiguo, nombre


if __name__ == "__main__":
    import sys
    import traceback

    fallos = total = 0
    for nombre, fn in sorted(globals().items()):
        if not nombre.startswith("test_") or not callable(fn):
            continue
        casos = getattr(fn, "_casos", [()])
        for caso in casos:
            total += 1
            try:
                fn(*caso)
            except Exception:
                fallos += 1
                print(f"FALLA {nombre}{caso}")
                traceback.print_exc(limit=2)
    print(f"{total - fallos}/{total} pruebas OK")
    sys.exit(1 if fallos else 0)
