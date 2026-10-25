# Comparador SV

Compara precios por kg, litro o unidad. Hoy incluye PriceSmart El Salvador (club Los Héroes).
Se actualiza solo cada día a las 6:00 a. m. con GitHub Actions y se publica con GitHub Pages.

## Poner en marcha (una sola vez)
1. Crea una cuenta gratuita en github.com y un repositorio nuevo (público), por ejemplo `comparador-sv`.
2. Sube todo el contenido de esta carpeta (botón "Add file" → "Upload files"), incluida la carpeta oculta `.github`.
3. En el repositorio: Settings → Pages → "Deploy from a branch" → rama `main`, carpeta `/docs` → Save.
4. En la pestaña Actions, abre "Actualizar precios" → "Run workflow". La primera corrida real descarga todo PriceSmart.
5. Tu página queda en `https://TU-USUARIO.github.io/comparador-sv/`.

## Archivos
- `comparador.py` motor de unidades (g, kg, lb, oz, ml, L, packs, "3 Unidades / 411 g"…)
- `pricesmart.py` lector de PriceSmart; `build.py` + `plantilla.html` generan `docs/index.html`
- `test_*.py` pruebas; `fixtures/` respuestas reales de ejemplo; `demo.py` demo con precios de AhorroSV
- Para otro club: cambia `--club 6702` en `.github/workflows/actualizar.yml` (6701 Santa Elena, 6703 San Miguel, 6704 Santa Ana).
