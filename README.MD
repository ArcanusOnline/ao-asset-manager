# 🛡️ AO Asset Manager

Herramienta web para revisar y ordenar los gráficos de **Arcanus Online**.
Reemplaza los viejos scripts de consola por una pantalla fácil de usar.

## ¿Qué hace?

- **📁 Escanea tus gráficos:** te da un archivo `.bat` chiquito. Lo ejecutás en tu carpeta de gráficos y genera `lista_graficos.txt`. Subís ese archivo y listo, no hace falta subir las imágenes.
- **🚑 Revisa el cliente:** compara tus archivos con `Graficos.ind` y te avisa:
  - **Qué gráficos faltan** (pueden hacer que el juego se cierre).
  - **Qué archivos sobran** (ocupan lugar y el juego no los usa).
- **➕ Busca números libres:** te dice qué números de archivo (`.png`) y de `Grh` están libres para agregar ítems o NPCs nuevos. Podés elegir el rango (ej: del 15.000 al 20.000).

## Cómo usarla

1. Abrí la app: **https://ao-asset-manager.streamlit.app/** (o corréla en tu PC).
2. Descargá el escáner `.bat` y ejecutalo dentro de tu carpeta de gráficos.
3. Subí el `lista_graficos.txt` que se generó.
4. Mirá los resultados en cada pestaña.

## Correrla en tu PC

Necesitás [Python 3.8 o más nuevo](https://www.python.org/downloads/).

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre sola en el navegador (`http://localhost:8501`).

---

> _Hecho para la comunidad de Arcanus Online._