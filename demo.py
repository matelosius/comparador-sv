"""Demo: compara productos con precios reales vistos en AhorroSV el 25-oct-2026.

Ejecutar:  python3 demo.py
"""
from comparador import Oferta, comparar

GRUPOS = {
    "Aceite de oliva Great Value (dos tamaños distintos)": [
        Oferta("La Despensa de Don Juan", "Aceite de Oliva Great Value Extra Virgen - 2.98 L", 19.77),
        Oferta("Maxi Despensa", "Aceite de Oliva Great Value Extra Virgen - 2.98 L", 35.80),
        Oferta("Walmart", "Aceite de Oliva Great Value Extra Virgen - 2.98 L", 36.06),
        Oferta("Walmart", "Aceite Great Value de oliva extra virgen - 754 ml", 5.00),
        Oferta("Maxi Despensa", "Aceite Great Value de oliva extra virgen - 754 ml", 8.70),
        Oferta("La Despensa de Don Juan", "Aceite Great Value de oliva extra virgen - 754 ml", 8.75),
    ],
    "Pañales Huggies Dermacare (por unidad, no por kg)": [
        Oferta("Walmart", "Pañales Huggies Dermacare Etapa 1/P - 68 Unidades", 20.00),
        Oferta("Maxi Despensa", "Pañales Huggies Dermacare Etapa 1/P - 68 Unidades", 23.40),
        Oferta("Súper Selectos", "Pañales Huggies Dermacare Etapa 1/P - 68 Unidades", 25.45),
        Oferta("La Despensa de Don Juan", "Pañales Huggies Dermacare Etapa 1/P - 68 Unidades", 31.50),
        Oferta("Walmart", "Pañales Pampers Swaddlers 360 Talla 3 7-13 kg - 70 Uds", 20.00),
    ],
    "Néctar Petit 12 pack (330 ml por envase)": [
        Oferta("Maxi Despensa", "Néctar Petit 12 Pack Surtido - 330 ml", 5.90),
        Oferta("La Despensa de Don Juan", "Néctar Petit 12 Pack Surtido - 330 ml", 6.70),
        Oferta("Walmart", "Néctar Petit 12 Pack Surtido - 330 ml", 8.00),
        Oferta("Walmart", "Gaseosa Pepsi Mega Doble - 2500 ml", 3.85),
    ],
    "Carne por libra vs. por peso": [
        Oferta("Maxi Despensa", "Puyazo de Res Don Cristobal - Precio Indicado Por Libra (454 g)", 4.50),
        Oferta("Walmart", "Puyazo de Res Don Cristobal - Precio Indicado Por Libra (454 g)", 6.95),
        Oferta("Súper Selectos", "Puyazo de Res Don Cristobal - Precio Indicado Por Libra (454 g)", 10.75),
    ],
}


def imprimir(titulo: str, ofertas: list[Oferta]) -> None:
    print(f"\n== {titulo}")
    for r in comparar(ofertas):
        if r.precio_unitario is None:
            print(f"   {r.oferta.tienda:<26} ${r.oferta.precio:>7.2f}   (no comparable)  {r.oferta.nombre}")
            continue
        extra = f"+{r.sobre_el_mejor_pct:.0f}%" if r.sobre_el_mejor_pct else "mejor"
        print(f"   {r.oferta.tienda:<26} ${r.oferta.precio:>7.2f}  =  ${r.precio_unitario:>7.2f} {r.etiqueta:<5} {extra:>6}"
              f"   {r.oferta.nombre[:60]}")
        for a in r.advertencias:
            print(f"       ! {a}")


if __name__ == "__main__":
    for titulo, ofertas in GRUPOS.items():
        imprimir(titulo, ofertas)
