import streamlit as st
import re
import io
import zipfile
from pathlib import Path
from PIL import Image

# Configuración de página
st.set_page_config(page_title="AO Asset Manager", page_icon="🛡️", layout="wide")

# --- ESTILOS ---
st.markdown("""
<style>
    /* Menú lateral: opciones tipo botón, sin el circulito del radio */
    div[role="radiogroup"] > label > div:first-of-type { display: none !important; }
    div[role="radiogroup"] label {
        padding: 10px 16px; margin-bottom: 4px; border-radius: 8px;
        transition: background-color 0.2s; cursor: pointer;
    }
    div[role="radiogroup"] label:hover { background-color: rgba(255, 75, 75, 0.12); }
    div[role="radiogroup"] label p { font-size: 15px !important; font-weight: 500 !important; margin: 0; }

    /* Cabecera de cada pantalla */
    .hero {
        padding: 22px 26px; border-radius: 14px; margin-bottom: 18px;
        background: linear-gradient(135deg, rgba(255,75,75,0.18), rgba(100,120,255,0.10));
        border: 1px solid rgba(255,255,255,0.08);
    }
    .hero h1 { margin: 0 0 6px 0; font-size: 30px; }
    .hero p { margin: 0; color: #c8c8d0; font-size: 15px; line-height: 1.5; }

    /* Número de paso */
    .step-badge {
        display: inline-flex; align-items: center; justify-content: center;
        width: 34px; height: 34px; border-radius: 50%;
        background: #ff4b4b; color: white; font-weight: 800; font-size: 17px;
        margin-bottom: 8px;
    }
    .big-num { font-size: 34px; font-weight: 800; color: #ff4b4b; line-height: 1.1; }
    .muted { color: #9a9aa5; font-size: 13px; }
</style>
""", unsafe_allow_html=True)


# --- LÓGICA / PARSERS ---

@st.cache_data
def parse_ind_data(content_bytes):
    """
    Parsea un archivo index (Graficos.ini) y devuelve dos sets:
    1. needed_files: Números de archivo (.png) que se requieren (Grh de 1 frame).
    2. used_grhs: Todos los índices GrhXXX que están ocupados.
    """
    needed_files = set()
    used_grhs = set()

    content = content_bytes.decode("utf-8", errors="ignore")

    # Regex para capturar "GrhXXXX ="
    regex_grh = re.compile(r'^\s*Grh(\d+)\s*=\s*(.+)$', re.IGNORECASE)

    for line in content.splitlines():
        line = line.strip()
        match = regex_grh.match(line)
        if not match:
            continue

        grh_id = int(match.group(1))
        used_grhs.add(grh_id)

        # Analizar si apunta a un archivo gráfico
        data_part = match.group(2)
        tokens = data_part.split("-")

        try:
            num_frames = int(tokens[0])
            # Si es de 1 frame, el segundo token es el ID del archivo
            if num_frames == 1 and len(tokens) >= 2:
                file_num = int(tokens[1])
                if file_num > 0:
                    needed_files.add(file_num)
        except ValueError:
            continue

    return needed_files, used_grhs

@st.cache_data
def parse_disk_files(content_bytes):
    """Lee lista_graficos.txt y devuelve set de IDs encontrados."""
    content = content_bytes.decode("utf-8", errors="ignore")
    found_ids = set()
    regex_file = re.compile(r'^(\d+)\.(png|bmp|jpg|jpeg)$', re.IGNORECASE)

    for line in content.splitlines():
        clean_line = line.strip()
        match = regex_file.match(clean_line)
        if match:
            found_ids.add(int(match.group(1)))

    return found_ids

def get_bat_script():
    script = "@echo off\r\necho Generando lista de graficos...\r\ndir /b *.png *.bmp > lista_graficos.txt\r\necho LISTO! Se creo 'lista_graficos.txt'. Ahora subelo a la web.\r\npause\r\n"
    return script.encode('utf-8')


# --- COMPONENTES DE UI ---

def hero(title, description):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{description}</p></div>', unsafe_allow_html=True)

def file_slot(key, label, types, help_text):
    """
    Cargador de archivos que RECUERDA el archivo entre pantallas:
    se sube una sola vez y sirve para todas las herramientas.
    Devuelve los bytes del archivo o None.
    """
    stored = st.session_state.get(key)
    if stored:
        c1, c2 = st.columns([4, 1])
        c1.success(f"✅ **{label}** — {stored['name']}")
        if c2.button("Cambiar", key=f"{key}_change", use_container_width=True):
            del st.session_state[key]
            st.rerun()
        return stored["data"]

    uploaded = st.file_uploader(label, type=types, key=f"{key}_up", help=help_text)
    if uploaded:
        st.session_state[key] = {"name": uploaded.name, "data": uploaded.getvalue()}
        st.rerun()
    return None

def go_to(page):
    st.session_state.nav = page


# --- MENÚ LATERAL ---
PAGES = {
    "inicio": "🏠  Inicio",
    "escaner": "📁  1. Escanear carpeta",
    "diag": "🚑  2. Diagnóstico",
    "nuevo": "➕  3. Números libres",
    "estudio": "🎨  4. Estudio gráfico",
    "editor": "⚔️  5. Editor de objetos",
}
if "nav" not in st.session_state:
    st.session_state.nav = PAGES["inicio"]

st.sidebar.markdown("### 🛡️ AO Asset Manager")
st.sidebar.caption("Herramientas para Arcanus Online")
mode = st.sidebar.radio("Ir a:", list(PAGES.values()), key="nav", label_visibility="collapsed")


# --- INICIO ---
if mode == PAGES["inicio"]:
    hero("🛡️ AO Asset Manager",
         "Revisá y ordená los gráficos y objetos de <b>Arcanus Online</b> sin instalar nada. "
         "Elegí qué querés hacer:")

    st.info("**¿Primera vez?** Empezá por **1. Escanear carpeta**. "
            "Es un paso de 1 minuto que te deja usar el Diagnóstico y los Números libres. "
            "Las herramientas 4 y 5 no lo necesitan.")

    tools = [
        ("escaner", "📁", "1. Escanear carpeta",
         "Genera la lista de gráficos que tenés en tu PC.",
         "Descargás un mini programa (.bat), lo ejecutás en tu carpeta de gráficos y obtenés un `lista_graficos.txt`.",
         "Nada"),
        ("diag", "🚑", "2. Diagnóstico",
         "Detecta gráficos que faltan (el juego se puede cerrar) y archivos que sobran.",
         "Compara tu carpeta contra el índice de gráficos.",
         "`Graficos.ini` + `lista_graficos.txt`"),
        ("nuevo", "➕", "3. Números libres",
         "Te dice qué número usar para agregar un ítem o NPC nuevo sin pisar nada existente.",
         "Busca huecos en un rango y te arma la línea lista para pegar.",
         "`Graficos.ini` + `lista_graficos.txt`"),
        ("estudio", "🎨", "4. Estudio gráfico",
         "Convierte imágenes BMP a PNG y vuelve transparente el fondo negro.",
         "Subís varias imágenes y bajás un ZIP con todo procesado.",
         "Tus imágenes"),
        ("editor", "⚔️", "5. Editor de objetos",
         "Editá ítems de `OBJ.DAT` (nombre, daño, defensa, precio…) con formularios.",
         "Mantiene el formato original del archivo al guardar.",
         "`OBJ.DAT`"),
    ]

    for row in (tools[:3], tools[3:]):
        cols = st.columns(3)
        for col, (pid, icon, title, what, how, needs) in zip(cols, row):
            with col.container(border=True):
                st.markdown(f"#### {icon} {title}")
                st.write(what)
                st.caption(how)
                st.caption(f"**Necesitás:** {needs}")
                st.button("Abrir →", key=f"home_{pid}", on_click=go_to, args=(PAGES[pid],),
                          use_container_width=True)

    with st.expander("❓ Glosario: ¿qué es cada cosa?"):
        st.markdown("""
- **Graficos.ini**: archivo de texto del cliente que lista cada gráfico con líneas tipo `Grh1=1-1-0-0-32-32`.
- **Grh**: el "número de código" de un gráfico. Los ítems y NPCs apuntan a un Grh.
- **Número de archivo (.png)**: el nombre de la imagen en tu carpeta (ej: `15001.png`). Cada Grh de 1 frame apunta a una imagen.
- **Huérfano**: imagen que está en tu carpeta pero ningún Grh usa. Ocupa espacio sin servir.
- **OBJ.DAT**: archivo del servidor con todos los objetos del juego.
""")


# --- 1. ESCANEAR CARPETA ---
elif mode == PAGES["escaner"]:
    hero("📁 1. Escanear carpeta",
         "Por seguridad, una página web <b>no puede ver tus archivos</b>. "
         "Con este mini programa generás una lista con los nombres de tus gráficos "
         "y la subís: <b>las imágenes nunca salen de tu PC</b>.")

    col1, col2, col3 = st.columns(3)

    with col1.container(border=True):
        st.markdown('<div class="step-badge">1</div>', unsafe_allow_html=True)
        st.markdown("**Descargá el escáner**")
        st.caption("Es un archivo `.bat` de pocas líneas. Podés abrirlo con el Bloc de notas para verlo.")
        st.download_button("⬇️ Descargar escáner (.bat)", data=get_bat_script(),
                           file_name="escanear_mis_graficos.bat", mime="text/plain",
                           type="primary", use_container_width=True)

    with col2.container(border=True):
        st.markdown('<div class="step-badge">2</div>', unsafe_allow_html=True)
        st.markdown("**Ejecutalo en tu carpeta**")
        st.caption("Copiá el `.bat` dentro de tu carpeta de gráficos (donde están los .png) y hacé doble clic.")
        st.info("📄 Se crea `lista_graficos.txt`")

    with col3.container(border=True):
        st.markdown('<div class="step-badge">3</div>', unsafe_allow_html=True)
        st.markdown("**Subí la lista**")
        st.caption("Subila acá o directamente en Diagnóstico / Números libres. Se recuerda en todas las pantallas.")

    st.markdown("##### Subir `lista_graficos.txt`")
    lista = file_slot("list_file", "lista_graficos.txt", ["txt"],
                      "El archivo que generó el escáner en tu carpeta de gráficos.")
    if lista:
        ids = parse_disk_files(lista)
        st.metric("Imágenes detectadas", len(ids))
        if not ids:
            st.warning("No se detectaron imágenes. Los nombres deben ser numéricos (ej: `1234.png`).")
        else:
            st.success("¡Listo! Ya podés ir a **2. Diagnóstico** o **3. Números libres**.")
            c1, c2 = st.columns(2)
            c1.button("🚑 Ir a Diagnóstico", on_click=go_to, args=(PAGES["diag"],), use_container_width=True)
            c2.button("➕ Ir a Números libres", on_click=go_to, args=(PAGES["nuevo"],), use_container_width=True)


# --- 2. DIAGNÓSTICO ---
elif mode == PAGES["diag"]:
    hero("🚑 2. Diagnóstico de salud",
         "Compara los gráficos que <b>tu carpeta tiene</b> contra los que <b>el índice pide</b>. "
         "Te avisa qué falta (puede cerrar el juego) y qué sobra (ocupa lugar sin usarse).")

    st.markdown("##### Archivos necesarios")
    c1, c2 = st.columns(2)
    with c1:
        ind = file_slot("ind_file", "Graficos.ini", ["ini", "txt", "ind"],
                        "El índice de gráficos del cliente (texto con líneas Grh1=...).")
    with c2:
        lst = file_slot("list_file", "lista_graficos.txt", ["txt"],
                        "Generado en el paso 1 (Escanear carpeta).")

    if not (ind and lst):
        st.info("👆 Subí los dos archivos para ver el resultado. "
                "Si no tenés `lista_graficos.txt`, andá a **1. Escanear carpeta**.")
    else:
        needed, _ = parse_ind_data(ind)
        disk = parse_disk_files(lst)
        missing = sorted(needed - disk)
        orphans = sorted(disk - needed)

        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Gráficos que pide el índice", len(needed))
        m2.metric("Imágenes en tu carpeta", len(disk))
        m3.metric("Problemas encontrados", len(missing) + len(orphans))

        col_miss, col_clean = st.columns(2)

        with col_miss:
            st.subheader("⛔ Faltantes")
            st.caption("El índice las pide pero no están en tu carpeta. **Es lo urgente**: pueden cerrar el juego.")
            if missing:
                st.error(f"Faltan {len(missing)} archivos")
                text_missing = "\n".join(f"{x}.png" for x in missing)
                st.text_area("Lista:", text_missing, height=200, key="ta_missing")
                st.download_button("⬇️ Descargar lista de faltantes", text_missing, "faltantes.txt")
            else:
                st.success("¡No falta nada! El cliente va a cargar bien.")

        with col_clean:
            st.subheader("🧹 Huérfanos")
            st.caption("Están en tu carpeta pero ningún gráfico los usa. Podés borrarlos para ahorrar espacio (opcional).")
            if orphans:
                st.warning(f"Sobran {len(orphans)} archivos")
                text_orphans = "\n".join(f"{x}.png" for x in orphans)
                st.text_area("Lista:", text_orphans, height=200, key="ta_orphans")
                st.download_button("⬇️ Descargar lista de huérfanos", text_orphans, "huerfanos.txt")
            else:
                st.success("Carpeta optimizada al 100%.")

        st.caption("ℹ️ Solo se revisan gráficos de 1 frame. Las animaciones usan otros Grh y no se verifican acá.")


# --- 3. NÚMEROS LIBRES ---
elif mode == PAGES["nuevo"]:
    hero("➕ 3. Números libres",
         "¿Vas a agregar un ítem o NPC nuevo? Acá encontrás un <b>número de imagen</b> y un "
         "<b>número de Grh</b> que nadie esté usando, así no pisás nada existente.")

    st.markdown("##### Archivos necesarios")
    c1, c2 = st.columns(2)
    with c1:
        ind = file_slot("ind_file", "Graficos.ini", ["ini", "txt", "ind"],
                        "Sirve para saber qué números de Grh ya están ocupados.")
    with c2:
        lst = file_slot("list_file", "lista_graficos.txt", ["txt"],
                        "Sirve para saber qué imágenes (.png) ya existen.")

    st.markdown("##### ¿En qué rango buscar?")
    st.caption("Elegí una zona del índice reservada para tus gráficos nuevos (ej: del 15000 al 20000).")
    rc1, rc2, rc3 = st.columns(3)
    min_val = rc1.number_input("Desde:", value=15000, step=100, min_value=1)
    max_val = rc2.number_input("Hasta:", value=20000, step=100, min_value=1)
    qty = rc3.number_input("¿Cuántos necesitás?", value=1, min_value=1, max_value=200,
                           help="Cantidad de números libres que querés que te liste.")

    if max_val < min_val:
        st.error("El valor de «Hasta» debe ser mayor que «Desde».")
    elif not (ind and lst):
        st.info("👆 Subí los dos archivos para obtener el número recomendado.")
    else:
        full_range = set(range(int(min_val), int(max_val) + 1))
        disk = parse_disk_files(lst)
        _, used_grhs = parse_ind_data(ind)

        free_files = sorted(full_range - disk)
        free_grhs = sorted(full_range - used_grhs)
        free_both = sorted(full_range - disk - used_grhs)

        st.divider()

        st.subheader("⭐ Recomendado")
        if free_both:
            chosen = free_both[:int(qty)]
            st.success(f"Usá el número **{chosen[0]}**: la imagen `{chosen[0]}.png` "
                       f"y `Grh{chosen[0]}` están libres a la vez.")
            st.caption("Así el nombre de la imagen y el Grh coinciden y es más fácil de mantener.")
            lines = "\n".join(f"Grh{n}=1-{n}-0-0-32-32" for n in chosen)
            st.markdown("**Línea(s) para pegar en `Graficos.ini`:**")
            st.code(lines, language="ini")
            st.caption("Formato: `Grh = frames - nº de imagen - X - Y - ancho - alto`. "
                       "Cambiá `32-32` por el ancho y alto reales de tu imagen.")
            if len(chosen) < int(qty):
                st.warning(f"Solo hay {len(chosen)} números libres en este rango (pediste {int(qty)}).")
        else:
            st.error("No hay ningún número libre para ambos en este rango. Probá ampliarlo.")

        with st.expander("Ver por separado (imagen / Grh)"):
            r1, r2 = st.columns(2)
            with r1:
                st.markdown("**🖼️ Imágenes libres (.png)**")
                if free_files:
                    st.write(f"Primera libre: `{free_files[0]}.png` — {len(free_files)} libres en total")
                    st.code(", ".join(str(n) for n in free_files[:int(qty) + 9]))
                else:
                    st.error("Sin espacio en este rango.")
            with r2:
                st.markdown("**🔢 Grh libres**")
                if free_grhs:
                    st.write(f"Primero libre: `Grh{free_grhs[0]}` — {len(free_grhs)} libres en total")
                    st.code(", ".join(str(n) for n in free_grhs[:int(qty) + 9]))
                else:
                    st.error("Sin espacio en este rango.")

# --- 4. ESTUDIO GRÁFICO ---
elif mode == PAGES["estudio"]:
    hero("🎨 4. Estudio gráfico",
         "Convierte imágenes <b>BMP a PNG</b> y vuelve <b>transparente el fondo negro</b>, todo de una vez. "
         "No necesitás ningún otro archivo: las imágenes se procesan en el momento y no se guardan.")

    st.markdown("**Cómo se usa:** ① subí tus imágenes → ② ajustá la tolerancia → ③ tocá *Procesar* → ④ bajá el ZIP.")

    with st.form("procesador_form"):
        uploaded_files = st.file_uploader(
            "① Arrastrá tus imágenes (BMP o PNG)",
            type=["bmp", "png"],
            accept_multiple_files=True
        )

        c1, c2 = st.columns(2)
        tolerance = c1.slider("② Tolerancia de negro (0 = solo negro puro)", 0, 150, 10,
                              help="Todo píxel 'casi negro' hasta este valor se vuelve transparente. Empezá con 10 y subilo si te quedan bordes oscuros.")
        keep_original = c2.checkbox("Mantener nombre original", value=True,
                                    help="Si lo desmarcás, se agrega '_processed' al nombre del archivo.")

        submitted = st.form_submit_button("③ 🔨 Procesar imágenes", type="primary")

    if submitted and not uploaded_files:
        st.warning("Primero subí al menos una imagen.")
        
    if submitted and uploaded_files:
        progress_bar = st.progress(0)
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    # Abrir imagen
                    image = Image.open(uploaded_file).convert("RGBA")
                    datas = image.getdata()
                    new_data = []
                    
                    # Proceso de transparencia
                    # Optimizacion: Si la tolerancia es 0, usar logica simple
                    if tolerance == 0:
                        for item in datas:
                            if item[0] == 0 and item[1] == 0 and item[2] == 0:
                                new_data.append((0, 0, 0, 0))
                            else:
                                new_data.append(item)
                    else:
                        for item in datas:
                            # Si es "casi negro"
                            if item[0] <= tolerance and item[1] <= tolerance and item[2] <= tolerance:
                                new_data.append((0, 0, 0, 0)) # Transparente
                            else:
                                new_data.append(item)
                    
                    image.putdata(new_data)
                    
                    # Guardar en memoria
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    
                    # Definir nombre
                    original_name = Path(uploaded_file.name).stem
                    final_name = f"{original_name}.png" if keep_original else f"{original_name}_processed.png"
                    
                    zip_file.writestr(final_name, img_byte_arr.getvalue())
                    
                except Exception as e:
                    st.error(f"Error con {uploaded_file.name}: {e}")
                
                # Actualizar barra
                progress_bar.progress((i + 1) / len(uploaded_files))
                
        st.success("¡Proceso terminado!")
        st.download_button(
            label="📥 Descargar PACK Procesado (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="graficos_procesados.zip",
            mime="application/zip",
            type="primary"
        )

# --- VISTA 5: EDITOR DE OBJETOS ---
elif mode == PAGES["editor"]:
    hero("⚔️ 5. Editor de objetos",
         "Editá los ítems de tu <b>OBJ.DAT</b> con formularios en vez de a mano. "
         "Al guardar se respeta el formato original del archivo.")
    st.markdown("**Cómo se usa:** ① subí tu `OBJ.DAT` → ② elegí un objeto → ③ cambiá sus datos y tocá *Guardar* → "
                "④ cuando termines, tocá *Descargar OBJ.DAT*.")
    st.caption("⚠️ Los cambios viven solo en esta sesión del navegador. Si recargás la página sin descargar, se pierden.")

    # --- HELPERS ---
    OBJ_TYPES = {
        1: "Usable (Pociones/Comida)", 2: "Arma", 3: "Armadura", 4: "Árboles", 5: "Oro", 
        6: "Puerta", 7: "Contenedor", 8: "Cartel", 9: "Llave", 10: "Foro", 
        11: "Poción", 12: "Libro", 13: "Bebida", 14: "Comida", 15: "Casco", 
        16: "Escudo", 17: "Instrumento", 18: "Yunque", 19: "Fragua", 20: "Herr. Trabajo",
        22: "Gema", 23: "Flores", 24: "Teleport", 26: "Item Mágico", 27: "Arco",
        31: "Barco", 32: "Munición (Flechas)", 34: "Mueble"
    }

    try:
        from obj_handler import ObjDatHandler
    except ImportError:
        st.error("Falta `obj_handler.py`.")
        st.stop()

    if "obj_data" not in st.session_state:
        st.session_state.obj_data = None
    if "obj_handler" not in st.session_state:
        st.session_state.obj_handler = None

    # --- SIDEBAR ACTIONS ---
    with st.sidebar:
        st.divider()
        st.subheader("Acciones rápidas")
        st.caption("Disponibles al cargar tu OBJ.DAT." if not st.session_state.obj_data else "Atajos para el editor de objetos.")
        if st.session_state.obj_data:
            objs = st.session_state.obj_data
            
            # 1. Buscar Libre
            if st.button("🔍 Buscar ID libre", help="Muestra el primer ID de objeto sin usar."):
                existing_ids = sorted(objs.keys())
                # Buscar el primer hueco
                free_id = 1
                for oid in existing_ids:
                    if oid == free_id:
                        free_id += 1
                    else:
                        break
                st.info(f"ID Disponible: {free_id}")
            
            # 2. Crear Nuevo
            if st.button("✨ Crear nuevo objeto", help="Agrega un objeto vacío con el primer ID libre. Después buscalo en el selector y completá sus datos."):
                existing_ids = sorted(objs.keys())
                free_id = 1
                for oid in existing_ids:
                    if oid == free_id:
                        free_id += 1
                    else:
                        break
                
                # Crear template básico
                st.session_state.obj_handler.objects[free_id] = {
                    "Name": "Nuevo Objeto",
                    "GrhIndex": "0",
                    "ObjType": "1"
                }
                st.session_state.obj_handler.original_order.append(free_id)
                st.session_state.obj_data = st.session_state.obj_handler.objects # Refrescar puntero
                st.success(f"Creado objeto ID {free_id}")
                st.rerun()

    # --- MAIN UI ---
    if st.session_state.obj_data is None:
        uploaded_obj = st.file_uploader("① Subí tu OBJ.DAT", type=["dat", "txt"])
    else:
        uploaded_obj = None
        info_c, reset_c = st.columns([4, 1])
        info_c.success(f"✅ OBJ.DAT cargado ({len(st.session_state.obj_data)} objetos)")
        if reset_c.button("Cargar otro archivo", use_container_width=True):
            st.session_state.obj_data = None
            st.session_state.obj_handler = None
            st.rerun()

    if uploaded_obj and st.session_state.obj_data is None:
        handler = ObjDatHandler()
        try:
            handler.parse(uploaded_obj.getvalue())
            st.session_state.obj_handler = handler
            st.session_state.obj_data = handler.objects
            st.success(f"¡Data cargada! ({len(handler.objects)} objetos)")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if st.session_state.obj_data:
        handler = st.session_state.obj_handler
        objs = st.session_state.obj_data
        
        # --- SELECTOR ---
        col_search, col_save = st.columns([3, 1])
        with col_search:
            # Opción formateada: "ID - Nombre (Tipo)"
            opts = sorted(objs.keys())
            
            def format_func(oid):
                o = objs[oid]
                otype = int(o.get("ObjType", 0))
                dtype = OBJ_TYPES.get(otype, "Desconocido")
                return f"{oid} - {o.get('Name', 'Sin Nombre')} [{dtype}]"

            selected_id = st.selectbox("② Elegí el objeto a editar (escribí para buscar por ID o nombre)", opts, format_func=format_func)
            current_obj = objs[selected_id]

        with col_save:
            st.write("") # Spacer
            st.write("")
            st.download_button(
                "💾 Descargar OBJ.DAT",
                data=handler.write(),
                file_name="OBJ.DAT",
                mime="application/octet-stream",
                type="primary",
                use_container_width=True,
                help="Baja el archivo con todos tus cambios guardados."
            )

        # --- EDITOR FORM ---
        st.divider()
        st.subheader(f"Editando: {current_obj.get('Name', '')}")
        
        with st.form(f"form_obj_{selected_id}"):
            # Organizamos en Tabs para no saturar
            tab_gen, tab_cmb, tab_req, tab_val, tab_extra, tab_cps = st.tabs(
                ["📝 General", "⚔️ Combate/Def", "⚒️ Crafting/Res", "💰 Valores", "⚙️ Otros/Props", "🚫 Clases"]
            )
            
            with tab_gen:
                c1, c2 = st.columns([2, 1])
                new_name = c1.text_input("Nombre (Name)", current_obj.get("Name", ""))
                new_grh = c2.number_input("Gráfico (GrhIndex)", value=int(current_obj.get("GrhIndex", 0)))
                
                c3, c4 = st.columns(2)
                curr_type = int(current_obj.get("ObjType", 1))
                type_help = OBJ_TYPES.get(curr_type, "Desconocido")
                new_type = c3.number_input(f"Tipo (ObjType) - Actual: {type_help}", value=curr_type, min_value=1)
                new_subtype = c4.number_input("Subtipo (Subtipo)", value=int(current_obj.get("Subtipo", 0)))
                
                c5, c6, c7 = st.columns(3)
                new_anim = c5.number_input("Animación (Anim)", value=int(current_obj.get("Anim", 0)))
                new_skin = c6.number_input("Ropaje/Cuerpo (NumRopaje)", value=int(current_obj.get("NumRopaje", 0)))
                new_hechizo = c7.number_input("Hechizo Index (HechizoIndex)", value=int(current_obj.get("HechizoIndex", 0)))
                
                st.divider()
                st.caption("Texto / Carteles")
                new_texto = st.text_input("Texto (Lectura/Cartel)", current_obj.get("Texto", ""))

            with tab_cmb:
                st.caption("Armas, Escudos, Cascos, Anillos, Barcos, Flechas")
                c1, c2 = st.columns(2)
                new_minhit = c1.number_input("Daño Mín (MinHIT)", value=int(current_obj.get("MinHIT", 0)))
                new_maxhit = c2.number_input("Daño Máx (MaxHIT)", value=int(current_obj.get("MaxHIT", 0)))
                
                c3, c4 = st.columns(2)
                new_mindef = c3.number_input("Defensa Mín (MinDef/DefensaMagicaMin)", value=int(current_obj.get("MINDEF", current_obj.get("DefensaMagicaMin", 0))))
                new_maxdef = c4.number_input("Defensa Máx (MaxDef/DefensaMagicaMax)", value=int(current_obj.get("MAXDEF", current_obj.get("DefensaMagicaMax", 0))))
                
                c5, c6 = st.columns(2)
                new_apunala = c5.number_input("Apuñala (Apuñala)", value=int(current_obj.get("Apuñala", 0)))
                # Proyectil / Municiones unificado visualmente, separado al guardar
                new_proyectil = c6.number_input("Proyectil/Munición ID (solo Arco o Munición)", value=int(current_obj.get("Proyectil", current_obj.get("Municiones", 0))))

                new_envenena = st.number_input("Envenena (0 = no, 1 = sí)", value=int(current_obj.get("Envenena", 0)))
                
                st.caption("Pociones / Modificadores")
                p1, p2, p3 = st.columns(3)
                new_tipo_pocion = p1.number_input("Tipo Poción", value=int(current_obj.get("TipoPocion", 0)))
                new_min_mod = p2.number_input("Mín Modif.", value=int(current_obj.get("MinModificador", 0)))
                new_max_mod = p3.number_input("Máx Modif.", value=int(current_obj.get("MaxModificador", 0)))

            with tab_req:
                st.caption("Requisitos de uso")
                r1, r2, r3 = st.columns(3)
                new_newbie = r1.checkbox("Es Newbie?", value=bool(int(current_obj.get("Newbie", 0))))
                new_no_cae = r2.checkbox("No Cae?", value=bool(int(current_obj.get("NoSeCae", 0))))
                new_agarrable = r3.checkbox("Agarrable?", value=bool(int(current_obj.get("Agarrable", 0))))
                
                r4, r5, r6 = st.columns(3)
                new_raza_enana = r4.checkbox("Solo Enanos?", value=bool(int(current_obj.get("RazaEnana", 0))))
                new_mujer = r5.checkbox("Solo Mujer?", value=bool(int(current_obj.get("Mujer", 0))))
                new_hombre = r6.checkbox("Solo Hombre?", value=bool(int(current_obj.get("Hombre", 0))))

                st.divider()
                st.caption("Skills Requeridos")
                s1, s2, s3 = st.columns(3)
                new_sk_herreria = s1.number_input("Herrería", value=int(current_obj.get("SkHerreria", 0)))
                new_sk_carpinteria = s2.number_input("Carpintería", value=int(current_obj.get("SkCarpinteria", 0)))
                new_min_skill = s3.number_input("Min Skill (General)", value=int(current_obj.get("MinSkill", 0)))

            with tab_val:
                v1, v2, v3 = st.columns(3)
                new_valor = v1.number_input("Valor Oro", value=int(current_obj.get("Valor", 0)))
                new_crucial = v2.number_input("Crucial (0/1)", value=int(current_obj.get("Crucial", 0)))
                new_arcanus = v3.number_input("Valor Arcanus", value=int(current_obj.get("ValorArcanus", 0)))

            with tab_extra:
                st.caption("Recursos (Lingotes/Madera/Minerales)")
                e1, e2, e3 = st.columns(3)
                new_lingh = e1.number_input("Ling. Hierro", value=int(current_obj.get("LingH", 0)))
                new_lingp = e2.number_input("Ling. Plata", value=int(current_obj.get("LingP", 0)))
                new_lingo = e3.number_input("Ling. Oro", value=int(current_obj.get("LingO", 0)))
                
                e4, e5 = st.columns(2)
                new_made = e4.number_input("Madera", value=int(current_obj.get("Madera", 0)))
                new_ling_idx = e5.number_input("Index Lingote (Ref)", value=int(current_obj.get("LingoteIndex", 0)))
                
                st.divider()
                st.caption("Puertas y Llaves")
                k1, k2, k3 = st.columns(3)
                new_cerrada = k1.number_input("Cerrada (0/1)", value=int(current_obj.get("abierta", 0))) # Ojo la clave en loadobj es 'abierta' o 'Cerrada'? LoadObj: ObjData(Object).Cerrada = val(Leer.GetValue(..., "abierta")). Asumimos clave 'abierta'.
                new_llave = k2.number_input("Llave ID", value=int(current_obj.get("Llave", 0)))
                new_clave = k3.number_input("Clave Numérica", value=int(current_obj.get("Clave", 0)))
                
                k4, k5 = st.columns(2)
                new_idx_abierta = k4.number_input("Index Grh Abierta", value=int(current_obj.get("IndexAbierta", 0)))
                new_idx_cerrada = k5.number_input("Index Grh Cerrada", value=int(current_obj.get("IndexCerrada", 0)))

            with tab_cps:
                st.caption("Clases Prohibidas (CP1...CP20)")
                st.write("Marca las clases que **NO** pueden usar este ítem.")
                
                # Generar checkbox dinámicos CP1 a CP15 (Standard AO)
                cps_data = {}
                cols = st.columns(4)
                for i in range(1, 16):
                    key = f"CP{i}"
                    val = current_obj.get(key, "0")
                    is_banned = (val != "0")
                    # Checkbox
                    with cols[(i-1)%4]:
                        checked = st.checkbox(f"Clase {i}", value=is_banned, key=f"cp_{selected_id}_{i}")
                        cps_data[key] = "1" if checked else "0"

            if st.form_submit_button("✅ Guardar Cambios en Objeto"):
                # Actualizar Dict
                current_obj.update({
                    "Name": new_name,
                    "GrhIndex": str(new_grh),
                    "ObjType": str(new_type),
                    "Subtipo": str(new_subtype),
                    "Anim": str(new_anim),
                    "NumRopaje": str(new_skin),
                    "HechizoIndex": str(new_hechizo),
                    "Texto": new_texto,
                    
                    "MinHIT": str(new_minhit),
                    "MaxHIT": str(new_maxhit),
                    "MINDEF": str(new_mindef),
                    "MAXDEF": str(new_maxdef),
                    "Apuñala": str(new_apunala),
                    "Envenena": str(new_envenena),
                    # "Paraliza": str(new_paraliza), # No estaba en loadobj pero suele estar
                    
                    "TipoPocion": str(new_tipo_pocion),
                    "MinModificador": str(new_min_mod),
                    "MaxModificador": str(new_max_mod),
                    
                    "Newbie": "1" if new_newbie else "0",
                    "NoSeCae": "1" if new_no_cae else "0",
                    "Agarrable": "1" if new_agarrable else "0", # Ojo con logica inversa en algunos server
                    "RazaEnana": "1" if new_raza_enana else "0",
                    "Mujer": "1" if new_mujer else "0",
                    "Hombre": "1" if new_hombre else "0",
                    
                    "SkHerreria": str(new_sk_herreria),
                    "SkCarpinteria": str(new_sk_carpinteria),
                    "MinSkill": str(new_min_skill),
                    
                    "Valor": str(new_valor),
                    "ValorArcanus": str(new_arcanus),
                    "Crucial": str(new_crucial),
                    
                    "LingH": str(new_lingh),
                    "LingP": str(new_lingp),
                    "LingO": str(new_lingo),
                    "Madera": str(new_made),
                    "LingoteIndex": str(new_ling_idx),
                    
                    "abierta": str(new_cerrada), # VB6 loadobj lee "abierta", lo guarda en .Cerrada. Si es 1 = Cerrada. Confuso, mantenemos clave FILE.
                    "Llave": str(new_llave),
                    "Clave": str(new_clave),
                    "IndexAbierta": str(new_idx_abierta),
                    "IndexCerrada": str(new_idx_cerrada),
                })
                
                # CPx
                current_obj.update(cps_data)

                # Casos especiales
                if new_type == 2: current_obj["Proyectil"] = str(new_proyectil)
                elif new_type == 32: current_obj["Municiones"] = str(new_proyectil)
                
                handler.objects[selected_id] = current_obj
                st.success(f"Objeto {selected_id} actualizado completamente.")
                st.rerun()
