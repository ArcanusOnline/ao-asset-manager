import streamlit as st
import re
import io
import zipfile
from pathlib import Path
from PIL import Image

# Configuración de página
st.set_page_config(page_title="AO Asset Manager", page_icon="🛡️", layout="wide")

# --- CSS PRO V4: SIMETRÍA PERFECTA ---
st.markdown("""
<style>
    /* === 1. MENÚ LATERAL === */
    div[role="radiogroup"] > label > div:first-of-type { display: none !important; }
    div[role="radiogroup"] label {
        padding: 12px 20px; margin-bottom: 4px; border-radius: 8px; border: none;
        transition: background-color 0.2s; cursor: pointer;
    }
    div[role="radiogroup"] label:hover { background-color: rgba(150, 150, 150, 0.1); }
    div[role="radiogroup"] label p { font-size: 15px !important; font-weight: 500 !important; margin: 0; }
    hr { margin: 15px 0; border-color: #333; }

    /* === 2. TARJETAS DEL PASO 1 (PIXEL PERFECT) === */
    
    /* CAJA SUPERIOR (TEXTO) - IDÉNTICA PARA LOS 3 */
    .card-top {
        background-color: #262730;
        border: 1px solid #464b5c;
        border-bottom: none; /* Se une con la parte de abajo */
        border-radius: 10px 10px 0 0;
        padding: 20px;
        text-align: center;
        height: 220px; /* ALTURA FIJA PARA ALINEACIÓN PERFECTA */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .s-num { font-size: 40px; font-weight: 800; color: #ff4b4b; margin-bottom: 5px; line-height: 1; }
    .s-title { font-size: 22px; font-weight: 700; color: #fff; margin-bottom: 10px; }
    .s-text { font-size: 14px; color: #b0b0b0; line-height: 1.4; }

    /* CAJA INFERIOR (ACCIÓN) - BASE */
    .card-bottom {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 50px;
        width: 100%;
        border-radius: 0 0 10px 10px;
        font-weight: 600;
        font-size: 14px;
        border: 1px solid #464b5c;
        border-top: none;
    }

    /* ESTILOS ESPECÍFICOS PARA LOS "BOTONES FALSOS" (Col 2 y 3) */
    .fake-btn-blue { background-color: rgba(33, 150, 243, 0.1); color: #64B5F6; border-top: 1px solid #464b5c; }
    .fake-btn-green { background-color: rgba(76, 175, 80, 0.1); color: #81C784; border-top: 1px solid #464b5c; }

    /* === HACK CRÍTICO: FORZAR AL BOTÓN DE STREAMLIT (Col 1) A SER IGUAL === */
    /* Apuntamos al botón dentro de la primera columna */
    [data-testid="column"]:nth-of-type(1) .stDownloadButton button {
        width: 100%;
        height: 50px;
        border-radius: 0 0 10px 10px !important;
        border: 1px solid #464b5c !important;
        border-top: none !important;
        margin: 0 !important;
        background-color: #ff4b4b; /* Color rojo del botón */
        color: white;
    }
    /* Quitamos el hover default feo y ponemos uno sutil */
    [data-testid="column"]:nth-of-type(1) .stDownloadButton button:hover {
        border-color: #ff4b4b !important;
        background-color: #ff2b2b !important;
        color: white !important;
    }
    
    /* Eliminar el espacio vacío que deja Streamlit entre el HTML y el botón */
    [data-testid="column"]:nth-of-type(1) .stMarkdown { margin-bottom: -15px !important; }

</style>
""", unsafe_allow_html=True)

# --- CABECERA ---
st.title("🛡️ Panel de Control - Arcanus Online")
st.markdown("---")

# --- LÓGICA ---
# --- LÓGICA / PARSERS ---

@st.cache_data
def parse_ind_data(file_content):
    """
    Parsea un archivo index (Graficos.ini/ind) y devuelve dos sets:
    1. needed_files: Números de archivo (.png) que se requieren (Grh de 1 frame).
    2. used_grhs: Todos los índices GrhXXX que están ocupados.
    """
    needed_files = set()
    used_grhs = set()
    
    # Reset del puntero por si acaso
    file_content.seek(0)
    content = file_content.getvalue().decode("utf-8", errors="ignore")
    
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
def parse_disk_files(file_content):
    """Lee lista_graficos.txt y devuelve set de IDs encontrados."""
    file_content.seek(0)
    content = file_content.getvalue().decode("utf-8", errors="ignore")
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

# --- MENÚ LATERAL ---
st.sidebar.subheader("Navegación")
opciones = {
    "Paso 1": "📁  Conectar Carpeta",
    "Diagnóstico": "🚑  Diagnóstico de Salud", 
    "Asistente": "➕  Nuevo Gráfico",
    "Procesador": "🎨  Estudio Gráfico",
    "Editor": "⚔️  Editor de Objetos"
}
mode = st.sidebar.radio("Ir a:", list(opciones.values()), label_visibility="collapsed")

# --- VISTA 1: CONEXIÓN ---
if mode == opciones["Paso 1"]:
    st.header("Paso 1: Conexión Local")
    st.caption("Por seguridad, la web no ve tus archivos. Sigue estos 3 pasos para conectarla.")
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    # --- TARJETA 1 (Descargar) ---
    with col1:
        st.markdown("""
        <div class="card-top">
            <div class="s-num">1</div>
            <div class="s-title">Descargar</div>
            <div class="s-text">Baja el "Escáner" (.bat).<br>Es un archivo seguro de 1kb.</div>
        </div>
        """, unsafe_allow_html=True)
        # El botón nativo de Streamlit, hackeado por CSS para parecer el footer
        st.download_button(
            label="⬇️ DESCARGAR .BAT",
            data=get_bat_script(),
            file_name="escanear_mis_graficos.bat",
            mime="text/plain",
            use_container_width=True
        )

    # --- TARJETA 2 (Ejecutar) ---
    with col2:
        st.markdown("""
        <div class="card-top">
            <div class="s-num">2</div>
            <div class="s-title">Ejecutar</div>
            <div class="s-text">Pégalo en tu carpeta <b>GRAFICOS</b><br>y dale doble clic.</div>
        </div>
        <div class="card-bottom fake-btn-blue">
            📄 Se creará: lista_graficos.txt
        </div>
        """, unsafe_allow_html=True)

    # --- TARJETA 3 (Subir) ---
    with col3:
        st.markdown("""
        <div class="card-top">
            <div class="s-num">3</div>
            <div class="s-title">Subir</div>
            <div class="s-text">Ve a las otras secciones<br>y sube ese archivo de texto.</div>
        </div>
        <div class="card-bottom fake-btn-green">
            ✅ ¡Ya puedes navegar!
        </div>
        """, unsafe_allow_html=True)

# --- VISTA 2: DIAGNÓSTICO ---
elif mode == opciones["Diagnóstico"]:
    st.header("🚑 Diagnóstico de Salud")
    st.write("Detecta errores críticos y limpia tu carpeta.")
    
    with st.expander("📂 Cargar Archivos (Clic para desplegar)", expanded=True):
        c1, c2 = st.columns(2)
        ind_file = c1.file_uploader("1. Graficos.ini / .txt", type=["ini", "txt"], key="diag_ind")
        list_file = c2.file_uploader("2. lista_graficos.txt", type=["txt"], key="diag_list")

    if ind_file and list_file:
        needed, _ = parse_ind_data(ind_file) 
        disk = parse_disk_files(list_file)        
        missing = sorted(needed - disk)     
        orphans = sorted(disk - needed)     
        
        st.divider()
        col_miss, col_clean = st.columns(2)
        
        with col_miss:
            st.error(f"⛔ Faltan {len(missing)} archivos")
            if missing:
                text_missing = "\n".join(f"{x}.png" for x in missing)
                st.text_area("Ver lista:", text_missing, height=200)
                st.download_button("⬇️ Descargar Reporte Faltantes", text_missing, "faltantes.txt")
            else:
                st.caption("¡No falta nada! El cliente cargará perfecto.")

        with col_clean:
            st.warning(f"🧹 Sobran {len(orphans)} archivos")
            if orphans:
                text_orphans = "\n".join(f"{x}.png" for x in orphans)
                with st.expander("Ver lista de basura"):
                    st.text_area("", text_orphans, height=150, label_visibility="collapsed")
                st.download_button("⬇️ Descargar Reporte Huérfanos", text_orphans, "huerfanos.txt")
            else:
                st.caption("Carpeta optimizada al 100%.")

# --- VISTA 3: ASISTENTE ---
elif mode == opciones["Asistente"]:
    st.header("➕ Agregar Nuevo Gráfico")
    st.write("Encuentra IDs libres para nuevos ítems.")

    with st.expander("📂 Cargar Archivos", expanded=True):
        c1, c2 = st.columns(2)
        ind_file = c1.file_uploader("Graficos.ini (Para código)", type=["ini", "txt", "ind"], key="assist_ind")
        list_file = c2.file_uploader("lista_graficos.txt (Para imagen)", type=["txt"], key="assist_list")

    st.markdown("##### Rango de Búsqueda")
    rc1, rc2 = st.columns(2)
    min_val = rc1.number_input("Desde:", value=15000, step=100)
    max_val = rc2.number_input("Hasta:", value=20000, step=100)
    
    full_range = set(range(min_val, max_val + 1))
    
    if list_file or ind_file:
        st.divider()
        res1, res2 = st.columns(2)

        with res1:
            st.subheader("Para la Imagen (.png)")
            if list_file:
                disk = parse_disk_files(list_file)
                free = sorted(list(full_range - disk))
                if free:
                    st.success(f"Disponible: **{free[0]}.png**")
                    st.caption(f"Y otros {len(free)-1} libres...")
                else:
                    st.error("Sin espacio en disco.")
            else:
                st.info("Sube la lista.txt")
        
        with res2:
            st.subheader("Para el Código (Grh)")
            if ind_file:
                _, used_grhs = parse_ind_data(ind_file)
                
                free_grhs = sorted(list(full_range - used_grhs))
                if free_grhs:
                    st.success(f"Disponible: **Grh{free_grhs[0]}**")
                    st.caption(f"Y otros {len(free_grhs)-1} libres...")
                    
                    st.markdown("---")
                    st.markdown("**Generador Rápido:**")
                    frames = st.number_input("Frames:", 1, 10, 1, key="gen_frames")
                    if frames == 1 and list_file:
                        # Sugerir mapeo directo si hay slots libres
                        st.code(f"Grh{free_grhs[0]}=1-{free_grhs[0]}-0-0-0-0", language="ini")
                else:
                    st.error("Sin espacio en índice.")
            else:
                st.info("Sube Graficos.ini")
    else:
        st.info("Carga tus archivos arriba para empezar a buscar.")

# --- VISTA 4: PROCESADOR DE IMÁGENES ---
elif mode == opciones.get("Procesador", ""): # Usamos .get por si no se ha definido aún en el diccionario
    st.header("🎨 Estudio Gráfico")
    st.write("Convierte BMPs a PNG y elimina fondos negros automáticamente.")
    
    with st.form("procesador_form"):
        uploaded_files = st.file_uploader(
            "Arrastra tus imágenes (BMP o PNG)", 
            type=["bmp", "png"], 
            accept_multiple_files=True
        )
        
        c1, c2 = st.columns(2)
        tolerance = c1.slider("Tolerancia de Negro (0 = Negro Puro)", 0, 150, 10, help="Sube esto si quedan bordes oscuros feos.")
        keep_original = c2.checkbox("Mantener nombre original", value=True, help="Si no, se agrega '_processed' al nombre.")
        
        submitted = st.form_submit_button("🔨 Procesar Imágenes")
        
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
elif mode == opciones.get("Editor", ""):
    st.header("⚔️ Editor de Objetos (OBJ.DAT)")
    st.markdown("Herramienta avanzada para manipular `OBJ.DAT` respetando el formato original.")

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
        st.subheader("Acciones Rápidas")
        if st.session_state.obj_data:
            objs = st.session_state.obj_data
            
            # 1. Buscar Libre
            if st.button("🔍 Buscar ID Libre"):
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
            if st.button("✨ Crear Nuevo Objeto"):
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
    uploaded_obj = st.file_uploader("Sube tu OBJ.DAT", type=["dat", "txt"])

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

            selected_id = st.selectbox("Seleccionar Objeto", opts, format_func=format_func)
            current_obj = objs[selected_id]

        with col_save:
            st.write("") # Spacer
            if st.button("💾 Descargar OBJ.DAT", type="primary"):
                st.download_button(
                    "📥 Click para bajar",
                    data=handler.write(),
                    file_name="OBJ.DAT",
                    mime="application/octet-stream"
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
                new_proyectil = c6.number_input("Proyectil/Munición ID", value=int(current_obj.get("Proyectil", current_obj.get("Municiones", 0))))

                c7, c8 = st.columns(2)
                new_envenena = c7.number_input("Envenena (0/1)", value=int(current_obj.get("Envenena", 0)))
                new_paraliza = c8.number_input("Paraliza (0/1) [Si aplica]", value=int(current_obj.get("Paraliza", 0)))
                
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