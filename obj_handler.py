import io
import re

class ObjDatHandler:
    """
    Manejador estricto para archivos OBJ.DAT de Argentum Online.
    Preserva estructura, mayúsculas y codificación Windows-1252.
    """
    
    def __init__(self):
        self.header_lines = []  # Líneas antes del [INIT]
        self.init_block = {}    # Pares clave-valor de [INIT]
        self.objects = {}       # Diccionario de diccionarios: {id: {key: val}}
        self.original_order = [] # Lista de IDs en orden de aparición para reconstrucción perfecta
        
    def parse(self, file_content_bytes):
        """
        Lee el contenido binario del archivo y lo estructura.
        """
        try:
            content = file_content_bytes.decode("cp1252")
        except UnicodeDecodeError:
            # Fallback a latin-1 si cp1252 falla (muy raro en Windows)
            content = file_content_bytes.decode("latin-1")
            
        lines = content.splitlines()
        
        current_section = None # None, "HEADER", "INIT", "OBJ"
        current_obj_id = None
        
        # Regex para detectar secciones [OBJxxx] o [INIT]
        regex_section = re.compile(r'^\[([a-zA-Z0-9]+)\]\s*$')
        # Regex para detectar Clave=Valor
        regex_keyval = re.compile(r'^([^=]+)=(.*)$')
        
        for line in lines:
            clean_line = line.strip()
            
            # Detectar sección
            match_sec = regex_section.match(clean_line)
            if match_sec:
                sec_name = match_sec.group(1).upper()
                
                if sec_name == "INIT":
                    current_section = "INIT"
                    continue
                elif sec_name.startswith("OBJ"):
                    current_section = "OBJ"
                    try:
                        current_obj_id = int(sec_name[3:]) # Extraer ID de OBJ123
                        self.objects[current_obj_id] = {}
                        self.original_order.append(current_obj_id)
                    except ValueError:
                        pass # Si hay algo raro como [OBJ_TEST] lo ignoramos
                    continue
                else:
                    # Otra sección desconocida (comentarios o basura)
                    if current_section is None:
                        self.header_lines.append(line)
                    continue

            # Detectar Clave=Valor
            if current_section == "INIT":
                match_kv = regex_keyval.match(clean_line)
                if match_kv:
                    key = match_kv.group(1).strip()
                    val = match_kv.group(2).strip()
                    self.init_block[key] = val
                    
            elif current_section == "OBJ" and current_obj_id is not None:
                match_kv = regex_keyval.match(clean_line)
                if match_kv:
                    # IMPORTANTE: Preservamos el casing de la clave (Name vs name)
                    # El servidor VB6 usa GetValue("INI", "Key") que suele ser case-insensitive en lectura 
                    # pero sensible al escribir. Guardamos tal cual viene.
                    key = match_kv.group(1).strip()
                    val = match_kv.group(2).strip()
                    self.objects[current_obj_id][key] = val
            
            elif current_section is None:
                # Líneas de cabecera (comentarios iniciales)
                self.header_lines.append(line)

    def get_object(self, obj_id):
        return self.objects.get(obj_id, {})

    def update_object(self, obj_id, key, value):
        if obj_id in self.objects:
            self.objects[obj_id][key] = str(value)

    def write(self):
        """
        Reconstruye el archivo binario respetando el formato.
        """
        output = []
        
        # 1. Cabecera (comentarios originales)
        for line in self.header_lines:
            output.append(line)
            
        # 2. Bloque [INIT]
        # Si no hay cabecera, asegurarse que [INIT] sea lo primero visible
        output.append("[INIT]")
        
        # Asegurar que NumObjs esté actualizado
        self.init_block["NumOBJs"] = str(len(self.objects))
        
        for k, v in self.init_block.items():
            output.append(f"{k}={v}")
            
        output.append("") # Línea vacía separadora
        
        # 3. Bloques [OBJxxx]
        # Usamos original_order para mantener el orden de lectura.
        # Si se agregaron nuevos, habría que manejarlos (no implementado aún, asumimos edición).
        for obj_id in self.original_order:
            output.append(f"[OBJ{obj_id}]")
            
            # Orden de las claves: VB6 no estricto, pero idealmente mantener un orden lógico?
            # Por simplicidad y seguridad, escribimos tal cual las tenemos en el dict.
            # Python 3.7+ mantiene orden de inserción.
            obj_data = self.objects[obj_id]
            for k, v in obj_data.items():
                output.append(f"{k}={v}")
                
            output.append("") # Línea vacía entre objetos
            
        # Convertir a bytes cp1252 con saltos de línea Windows CRLF
        full_text = "\r\n".join(output)
        return full_text.encode("cp1252")

