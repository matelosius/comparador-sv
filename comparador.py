"""Motor de normalización de presentaciones para un comparador de precios (El Salvador).

Idea central: cada producto trae su tamaño escrito en el nombre ("2.98 L", "6 x 355 ml",
"12 Pack - 330 ml", "Precio indicado por libra (454 g)", "12 oz"...). Este módulo lo
interpreta y lo lleva a una base común para poder comparar:

    masa     -> gramos   (precio por kg)
    volumen  -> mililitros (precio por L)
    unidad   -> piezas   (precio por unidad)

Cuando la presentación es ambigua (p. ej. "12 Pack - 330 ml": ¿330 ml en total o por
envase?) se aplica una heurística, se marca `ambiguo=True` y se explica en `notas`.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

# --------------------------------------------------------------------------- constantes
G_POR_LB = 453.592
G_POR_OZ = 28.3495
ML_POR_FLOZ = 29.5735
ML_POR_GAL = 3785.41

# unidad escrita -> (dimensión, factor a la base: g o ml)
_UNIDADES_MEDIDA: dict[str, tuple[str, float]] = {
    "mg": ("masa", 0.001),
    "g": ("masa", 1.0), "gr": ("masa", 1.0), "grs": ("masa", 1.0), "gs": ("masa", 1.0),
    "gramo": ("masa", 1.0), "gramos": ("masa", 1.0),
    "kg": ("masa", 1000.0), "kgs": ("masa", 1000.0), "kilo": ("masa", 1000.0),
    "kilos": ("masa", 1000.0), "kilogramo": ("masa", 1000.0), "kilogramos": ("masa", 1000.0),
    "lb": ("masa", G_POR_LB), "lbs": ("masa", G_POR_LB),
    "libra": ("masa", G_POR_LB), "libras": ("masa", G_POR_LB),
    "oz": ("oz", G_POR_OZ), "onza": ("oz", G_POR_OZ), "onzas": ("oz", G_POR_OZ),
    "floz": ("volumen", ML_POR_FLOZ),
    "ml": ("volumen", 1.0), "cl": ("volumen", 10.0),
    "l": ("volumen", 1000.0), "lt": ("volumen", 1000.0), "lts": ("volumen", 1000.0),
    "litro": ("volumen", 1000.0), "litros": ("volumen", 1000.0),
    "gal": ("volumen", ML_POR_GAL), "galon": ("volumen", ML_POR_GAL),
    "galones": ("volumen", ML_POR_GAL),
}

# Conteos "puros" (cada pieza es el artículo) y agrupadores (envases dentro de un paquete).
_CONTEOS = ("unidades", "unidad", "unids", "unid", "unds", "und", "uds", "ud", "un", "u",
            "pzas", "pza", "piezas", "pieza", "rollos", "rollo", "hojas", "hoja",
            "tabletas", "tableta", "pastillas", "pastilla", "capsulas", "capsula",
            "panales", "panal", "pares", "par")
_AGRUPADORES = ("sobres", "sobre", "latas", "lata", "botellas", "botella", "bolsitas",
                "bolsita", "cajas", "caja", "cajitas", "cajita")

# Palabras que sugieren que "oz" son onzas fluidas (líquido) y no de peso.
_PISTAS_LIQUIDO = ("bebida", "jugo", "nectar", "agua", "aceite", "shampoo", "champu",
                   "acondicionador", "gaseosa", "refresco", "leche liquida", "detergente liquido",
                   "suavizante", "enjuague", "locion", "crema liquida", "vinagre", "salsa liquida",
                   "cerveza", "vino", "licor", "te listo", "energizante", "limpiador")

TIENDAS_CON_MEMBRESIA = {"pricesmart"}

ETIQUETAS = {"masa": "$/kg", "volumen": "$/L", "unidad": "$/un"}


def _norm(texto: str) -> str:
    """Minúsculas, sin acentos, y con 'fl oz' / 'onza fluida' unificado como 'floz'."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"fl\.?\s*oz\.?", "floz", t)
    t = re.sub(r"onzas?\s+fluidas?", "floz", t)
    return t


def _alt(palabras) -> str:
    return "|".join(re.escape(p) for p in sorted(palabras, key=len, reverse=True))


_NUM = r"\d+(?:[.,]\d+)?"
_MED = _alt(_UNIDADES_MEDIDA)
_CNT = _alt(_CONTEOS + _AGRUPADORES)
_FIN = r"(?![a-z0-9])"
_INI = r"(?<![\w.])"

_RE_MEDIDA = re.compile(_INI + "(" + _NUM + r")\s*(" + _MED + ")" + _FIN)
_RE_MULTI_MEDIDA = re.compile(_INI + r"(\d+)\s*[x×]\s*(" + _NUM + r")\s*(" + _MED + ")" + _FIN)
_RE_MULTI_MEDIDA_INV = re.compile(_INI + "(" + _NUM + r")\s*(" + _MED + r")\s*[x×]\s*(\d+)(?![\w.])")
_RE_MULTI_CONTEO = re.compile(_INI + r"(\d+)\s*[x×]\s*(\d+)\s*(" + _CNT + ")" + _FIN)
_RE_CONTEO = re.compile(_INI + r"(\d+)\s*(" + _CNT + ")" + _FIN)
_RE_PACK_N = re.compile(_INI + r"(\d+)\s*(?:pack|pk|paquetes?)" + _FIN)
_RE_PACK_DE = re.compile(r"(?:pack|pk|paquete)\s*(?:de\s*)?(\d+)(?![\w.])")
_RE_N_UNIDADES_BARRA = re.compile(_INI + r"\d+\s*unidades?\s*/")
_RE_DOCENA = re.compile(_INI + r"(?:(\d+)\s*)?docenas?" + _FIN)
_RE_MEDIA_DOCENA = re.compile(r"media\s+docena")

# Tallas de pañales / rangos de edad-peso: "7-13 kg", "16+ kg" NO son el contenido del paquete.
_SEP_RANGO = r"(?:\s+a\s+|-|–)"  # "7-13" o "2 a 4"; un " - " con espacios NO es rango
_RE_RANGO_PESO = re.compile(_INI + _NUM + _SEP_RANGO + _NUM + r"\s*(?:kg|kgs|lb|lbs)" + _FIN)
_RE_MAS_PESO = re.compile(_INI + r"\d+\s*\+\s*(?:kg|kgs|lb|lbs)" + _FIN)
# "2 a 4 unidades" (cantidad aproximada por pieza vendida por peso)
_RE_RANGO_CONTEO = re.compile(_INI + r"\d+" + _SEP_RANGO + r"\d+\s*(?:" + _CNT + ")" + _FIN)


def _num(s: str) -> float:
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", s):  # 1,000 -> miles
        return float(s.replace(",", ""))
    return float(s.replace(",", "."))


# --------------------------------------------------------------------------- tamaño
@dataclass
class Tamano:
    texto: str
    masa_g: Optional[float] = None
    volumen_ml: Optional[float] = None
    unidades: Optional[float] = None
    ambiguo: bool = False
    notas: list[str] = field(default_factory=list)

    @property
    def dimensiones(self) -> dict[str, float]:
        d: dict[str, float] = {}
        if self.masa_g:
            d["masa"] = self.masa_g
        if self.volumen_ml:
            d["volumen"] = self.volumen_ml
        if self.unidades:
            d["unidad"] = self.unidades
        return d

    @property
    def dimension_principal(self) -> Optional[str]:
        """La dimensión que mejor describe el producto."""
        medida = "masa" if self.masa_g else ("volumen" if self.volumen_ml else None)
        if medida:
            total = self.masa_g or self.volumen_ml or 0
            # 100 pastillas de 6.5 mg: comparar por pastilla, no por kg
            if self.unidades and total / self.unidades < 1:
                return "unidad"
            return medida
        return "unidad" if self.unidades else None

    def precio_unitario(self, precio: float, dimension: Optional[str] = None) -> Optional[float]:
        """$/kg, $/L o $/unidad según la dimensión. None si el producto no la tiene."""
        dim = dimension or self.dimension_principal
        cantidad = self.dimensiones.get(dim) if dim else None
        if not cantidad:
            return None
        if dim == "masa":
            return precio / (cantidad / 1000)
        if dim == "volumen":
            return precio / (cantidad / 1000)
        return precio / cantidad


def interpretar(nombre: str, es_liquido: Optional[bool] = None) -> Tamano:
    """Extrae el tamaño total de un nombre de producto.

    es_liquido: sólo importa para 'oz' (onza de peso vs. onza fluida). Si es None se
    deduce por palabras del nombre y se marca como ambiguo.
    """
    t = _norm(nombre)
    r = Tamano(texto=nombre)

    # 1) quitar rangos que no son contenido
    t, n1 = _RE_RANGO_PESO.subn(" ", t)
    t, n2 = _RE_MAS_PESO.subn(" ", t)
    if n1 or n2:
        r.notas.append("Ignoré un rango de peso del usuario (talla), no es el contenido.")
    t, n3 = _RE_RANGO_CONTEO.subn(" ", t)
    if n3:
        r.notas.append("Ignoré un rango aproximado de piezas ('2 a 4 unidades').")

    def a_base(valor: float, unidad: str) -> tuple[str, float]:
        dim, factor = _UNIDADES_MEDIDA[unidad]
        if dim == "oz":
            if es_liquido is None:
                liquido = any(p in t for p in _PISTAS_LIQUIDO)
                r.ambiguo = True
                r.notas.append(
                    "'oz' interpretado como " + ("onzas fluidas (líquido)." if liquido else "onzas de peso.")
                    + " Indica es_liquido=True/False para confirmar."
                )
            else:
                liquido = es_liquido
            if liquido:
                return "volumen", valor * ML_POR_FLOZ
            return "masa", valor * G_POR_OZ
        return dim, valor * factor

    def poner(dim: str, cantidad: float) -> None:
        if dim == "masa":
            r.masa_g = cantidad
        else:
            r.volumen_ml = cantidad

    # 2) multiplicadores explícitos: "6 x 355 ml", "355 ml x 6", "10 x 100 unidades"
    m = _RE_MULTI_MEDIDA.search(t)
    if m:
        n, valor, unidad = int(m.group(1)), _num(m.group(2)), m.group(3)
        dim, base = a_base(valor, unidad)
        poner(dim, n * base)
        r.unidades = float(n)
        r.notas.append(f"{n} x {valor:g} {unidad} = total {n * base:g} {'g' if dim == 'masa' else 'ml'}.")
        return r
    m = _RE_MULTI_MEDIDA_INV.search(t)
    if m:
        valor, unidad, n = _num(m.group(1)), m.group(2), int(m.group(3))
        dim, base = a_base(valor, unidad)
        poner(dim, n * base)
        r.unidades = float(n)
        r.notas.append(f"{valor:g} {unidad} x {n} = total {n * base:g} {'g' if dim == 'masa' else 'ml'}.")
        return r
    m = _RE_MULTI_CONTEO.search(t)
    if m:
        r.unidades = float(int(m.group(1)) * int(m.group(2)))
        r.notas.append(f"{m.group(1)} x {m.group(2)} = {r.unidades:g} unidades.")
        return r

    # 3) medida(s) simples
    medidas = []
    onzas = []  # 'oz' sueltas: sólo cuentan si no hay otra medida (suelen ser equivalencias)
    for mm in _RE_MEDIDA.finditer(t):
        valor, unidad = _num(mm.group(1)), mm.group(2)
        if _UNIDADES_MEDIDA[unidad][0] == "oz":
            onzas.append(valor)
            continue
        dim, base = a_base(valor, unidad)
        medidas.append((dim, base))
    if not medidas and onzas:
        medidas.append(a_base(onzas[0], "oz"))
    medida_dim = medida_total = None
    if medidas:
        medida_dim, medida_total = medidas[0]
        for dim, base in medidas[1:]:
            if dim != medida_dim or abs(base - medida_total) / medida_total > 0.03:
                r.ambiguo = True
                r.notas.append("El nombre trae varias medidas distintas; usé la primera.")
                break

    # 4) conteo / pack
    cantidad_conteo: Optional[float] = None
    mc = _RE_PACK_N.search(t) or _RE_PACK_DE.search(t)
    if mc:
        cantidad_conteo = float(mc.group(1))
    else:
        mc = _RE_CONTEO.search(t)
        if mc:
            cantidad_conteo = float(mc.group(1))
    if cantidad_conteo is None:
        if _RE_MEDIA_DOCENA.search(t):
            cantidad_conteo = 6.0
        else:
            md = _RE_DOCENA.search(t)
            if md:
                cantidad_conteo = float(md.group(1) or 1) * 12

    # 5) "precio indicado por libra" sin número
    if medida_dim is None and cantidad_conteo is None and re.search(r"por\s+libra", t):
        r.masa_g = G_POR_LB
        r.notas.append("Precio indicado por libra: 1 lb = 453.6 g.")
        return r

    # 6) combinar medida y conteo
    if medida_dim and cantidad_conteo and cantidad_conteo > 1 and _RE_N_UNIDADES_BARRA.search(t):
        # Convención "3 Unidades / 411 g / 14.5 oz" (PriceSmart): la medida es POR unidad.
        medida_total *= cantidad_conteo
        r.notas.append(
            f"'{cantidad_conteo:g} Unidades / medida': la medida es por unidad (total {medida_total:g})."
        )
    elif medida_dim and cantidad_conteo and cantidad_conteo > 1:
        por_pieza = medida_total / cantidad_conteo
        umbral = 100.0 if medida_dim == "volumen" else 5.0
        r.ambiguo = True
        if por_pieza < umbral:
            medida_total *= cantidad_conteo
            r.notas.append(
                f"'{cantidad_conteo:g}' piezas y una medida: interpreté la medida como POR PIEZA "
                f"(total {medida_total:g}). Si es el total del paquete, el precio unitario sale distinto."
            )
        else:
            r.notas.append(
                f"'{cantidad_conteo:g}' piezas y una medida: interpreté la medida como TOTAL del paquete."
            )
    if medida_dim:
        poner(medida_dim, medida_total)
    if cantidad_conteo:
        r.unidades = cantidad_conteo
    if not r.dimensiones:
        r.notas.append("No encontré medida ni cantidad en el nombre.")
    return r


# --------------------------------------------------------------------------- comparación
@dataclass
class Oferta:
    tienda: str
    nombre: str
    precio: float
    es_liquido: Optional[bool] = None


@dataclass
class Resultado:
    oferta: Oferta
    tamano: Tamano
    dimension: Optional[str]
    precio_unitario: Optional[float]
    sobre_el_mejor_pct: Optional[float] = None
    advertencias: list[str] = field(default_factory=list)

    @property
    def etiqueta(self) -> str:
        return ETIQUETAS.get(self.dimension or "", "")


def comparar(ofertas: list[Oferta], dimension: Optional[str] = None) -> list[Resultado]:
    """Ordena las ofertas de la más barata a la más cara por precio unitario.

    Si no se indica `dimension`, usa una que TODAS las ofertas tengan (preferida: la más
    común). Las que no se puedan comparar quedan al final con una advertencia.
    """
    tamanos = [interpretar(o.nombre, o.es_liquido) for o in ofertas]

    if dimension is None:
        comunes = None
        for t in tamanos:
            ds = set(t.dimensiones)
            comunes = ds if comunes is None else comunes & ds
        principales = [t.dimension_principal for t in tamanos if t.dimension_principal]
        if comunes:
            dimension = max(comunes, key=lambda d: principales.count(d))
        elif principales:
            dimension = max(set(principales), key=principales.count)

    resultados: list[Resultado] = []
    for o, t in zip(ofertas, tamanos):
        pu = t.precio_unitario(o.precio, dimension) if dimension else None
        res = Resultado(o, t, dimension, pu)
        if pu is None:
            res.advertencias.append("No se pudo comparar: la presentación no tiene la dimensión usada.")
        if t.ambiguo:
            res.advertencias.append("Presentación ambigua: " + " ".join(t.notas))
        if o.tienda.strip().lower() in TIENDAS_CON_MEMBRESIA:
            res.advertencias.append("Requiere membresía: el precio sólo aplica a socios.")
        resultados.append(res)

    con_precio = sorted((r for r in resultados if r.precio_unitario is not None),
                        key=lambda r: r.precio_unitario)
    sin_precio = [r for r in resultados if r.precio_unitario is None]
    if con_precio:
        mejor = con_precio[0].precio_unitario
        for r in con_precio:
            r.sobre_el_mejor_pct = (r.precio_unitario / mejor - 1) * 100 if mejor else None
    return con_precio + sin_precio
