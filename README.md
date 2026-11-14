# Marketnus · Content Intelligence

Tablero en Streamlit para decidir **qué contenido publicar** en Marketnus: keywords de Google y YouTube con su oportunidad (estilo SEMrush), tendencias, competencia (Coursera, Udemy, Platzi), hashtags para TikTok e Instagram, calendario alineado con los 13 cursos y un Copy Lab para revisar textos antes de publicar.

Todo con fuentes **gratis**: Google Trends, el autocompletado de Google y YouTube, y TikTok Creative Center (cuando responde). No necesita claves de API.

## Pestañas

| Pestaña | Qué hace |
|---|---|
| Esta semana | Curso de la semana, mejor oportunidad y 6 piezas listas para producir |
| Keywords | Tabla filtrable con demanda, tendencia de 12 meses, momentum, dificultad (KD), encaje y oportunidad; matriz demanda vs. dificultad; brief SEO por keyword |
| Tendencias | Interés semanal por tema, estacionalidad, mapa por país y búsquedas en ascenso |
| Competencia | Fichas de Coursera, Udemy y Platzi con fuentes, share of search, qué busca la gente de cada marca y matriz de cobertura de temas |
| Redes | Sets de hashtags, horarios, búsquedas en YouTube y qué formato funciona en cada red |
| Calendario | Plan semanal (video corto, carrusel, YouTube/blog, LinkedIn) por cada curso que se publica |
| Copy Lab | Puntúa captions, títulos de YouTube y títulos + meta de blog |
| Datos y fuentes | Estado de cada fuente, fórmulas y carga de CSV de Google Trends |

## Publicarlo (igual que el tablero de LCS)

1. En GitHub, crea un repositorio público nuevo: `marketnus-content-intelligence`.
2. **Add file → Upload files** y arrastra *todo el contenido* de esta carpeta (incluidas `.github`, `.streamlit`, `config`, `data`, `pipeline`). Si el navegador no sube las carpetas que empiezan con punto, créalas con **Add file → Create new file** escribiendo la ruta completa, por ejemplo `.github/workflows/weekly-update.yml`, y pega el contenido.
3. **Commit changes**.
4. En **Settings → Actions → General → Workflow permissions**, marca **Read and write permissions** y guarda (así el robot puede guardar los datos cada semana).
5. En la pestaña **Actions**, abre «Actualización semanal (cada lunes)» y pulsa **Run workflow**. Tarda entre 10 y 30 minutos; al terminar aparece `data/latest.json`.
6. En [share.streamlit.io](https://share.streamlit.io): **Create app** → repo `skad4/marketnus-content-intelligence`, rama `main`, archivo `app.py` → **Deploy**.

Desde ahí el pipeline corre solo cada lunes y Streamlit Cloud se actualiza cuando llegan datos nuevos.

## Antes de la primera corrida

Hasta que corra el pipeline, la demanda y la dificultad son una **estimación inicial** y la app lo dice arriba. Cuando llega Google Trends, la columna «Fuente» cambia a «Google Trends» y aparecen las tendencias, el momentum y el mapa.

## Cómo editarlo

- **Agregar keywords:** `config/keywords.csv` (una fila por keyword: tema, curso, estimación inicial de demanda y dificultad). El pipeline se dispara solo al guardar.
- **Cursos que faltan (hay 9 de 13):** `config/courses.json`. El campo `semana` define el orden de publicación y el calendario se extiende solo.
- **Competencia:** `config/competitors.json` (cada dato con su enlace de fuente).
- **Hashtags y horarios:** `config/social.json`.
- **Pesos de la oportunidad:** al inicio de `scoring.py`.

## Correrlo en tu computadora

```
pip install -r requirements.txt
streamlit run app.py
```

Para probar el pipeline localmente: `python -m pipeline.run_weekly` (con `QUICK_RUN=1` solo baja 2 lotes de Google Trends).

## Límites honestos

- Google Trends da interés **relativo**, no volumen de búsquedas. La keyword ancla («marketing digital») permite comparar todos los lotes en una misma escala.
- Google limita las consultas a Trends. Si un lote falla, se conservan los datos de la semana anterior para esas keywords.
- TikTok e Instagram no publican sus búsquedas. Se usa el autocompletado de YouTube como señal de búsqueda en video y TikTok Creative Center cuando responde.
- La dificultad (KD) y la cobertura de la competencia son estimaciones explicadas en la app; para volúmenes exactos puedes exportar Google Keyword Planner y sumarlo a `config/keywords.csv`.

Developer: Ed Trigueros
