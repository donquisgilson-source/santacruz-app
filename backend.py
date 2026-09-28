from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client, Client
import datetime
import os
from matriz import TABLA_LITROS

app = FastAPI(title="Backend Santa Cruz")

try:
    from config_local import SUPABASE_URL, SUPABASE_KEY
except ImportError:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- DETECTOR DE ERRORES DE RENDER ---
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("🚨 ERROR CRÍTICO: No se encontraron SUPABASE_URL o SUPABASE_KEY en Render. Revisa tus Environment Variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class ReporteTanques(BaseModel):
    usuario: str; status: str
    t1_cm: int; t2_cm: int; t3_cm: int; t4_cm: int; t5_cm: int; t6_cm: int

class UsuarioLogin(BaseModel):
    username: str; pin: str

class NuevoUsuario(BaseModel):
    username: str

class ConfigUpdate(BaseModel):
    fondo_muerto: int; precio_litro: float

class RolUpdate(BaseModel):
    username: str; rol: str

@app.post("/login")
def login_usuario(datos: UsuarioLogin):
    usuario_mayus = datos.username.upper().strip()
    res = supabase.table("usuarios").select("*").eq("username", usuario_mayus).execute()
    
    if len(res.data) > 0:
        user_db = res.data[0]
        # Detectamos si es el Primer Inicio (No tiene PIN guardado)
        if not user_db.get("pin"):
            if datos.pin: # Si nos mandó un PIN, lo guardamos como el definitivo
                supabase.table("usuarios").update({"pin": datos.pin}).eq("username", usuario_mayus).execute()
                return {"exito": True, "rol": user_db["rol"], "username": usuario_mayus, "mensaje": "PIN creado exitosamente."}
            else:
                return {"exito": False, "mensaje": "Debes crear un PIN nuevo.", "primer_inicio": True}
                
        # Si ya tiene PIN, validamos normalmente
        if user_db["pin"] == datos.pin:
            return {"exito": True, "rol": user_db["rol"], "username": usuario_mayus}
        return {"exito": False, "mensaje": "PIN incorrecto"}
    else:
        return {"exito": False, "mensaje": "Usuario no registrado. Contacta al administrador."}

@app.post("/usuarios/crear")
def crear_usuario(datos: NuevoUsuario):
    usuario_mayus = datos.username.upper().strip()
    res = supabase.table("usuarios").select("*").eq("username", usuario_mayus).execute()
    if len(res.data) > 0:
        return {"exito": False, "mensaje": "El usuario ya existe."}
    
    # Se crea el usuario SIN PIN. Lo pondrá él mismo en su primer login.
    nuevo_user = {"username": usuario_mayus, "rol": "operario"}
    supabase.table("usuarios").insert(nuevo_user).execute()
    return {"exito": True, "mensaje": f"Usuario {usuario_mayus} creado."}

def generar_texto_wp(config, estado):
    fecha_str = datetime.datetime.now().strftime("%d/%m/%Y")
    hora_str = datetime.datetime.now().strftime("%I %p").lower()
    return f"""Fecha del Reporte:*{fecha_str}
*Hora del Reporte:*{hora_str}
* *Estado: {config['estado_geo']}
* Nombre de la Estación: {config['nombre_estacion']} Cod {config['codigo_estacion']}
* Modalidad: {config['modalidad']}
* Municipio {config['municipio']}
* Status {estado['status']}

* Inventarios
T1 ✅        {estado['t1_cm']}cm  -  {estado['t1_lt']}  ltrs
T2 ✅        {estado['t2_cm']}cm - {estado['t2_lt']} ltrs
T3 ✅        {estado['t3_cm']}cm -        {estado['t3_lt']} ltrs
T4 ✅        {estado['t4_cm']}cm -    {estado['t4_lt']} ltrs
T5 ✅        {estado['t5_cm']}cm    {estado['t5_lt']} ltrs
T6 ✅        {estado['t6_cm']}cm   {estado['t6_lt']} ltrs

*✅Total: * {estado['total_bruto']}

*Cerrado {estado['total_neto']} ltrs disponible para la venta*"""

@app.post("/cargar_datos")
def cargar_datos(reporte: ReporteTanques):
    t1_lt = TABLA_LITROS.get(reporte.t1_cm, 0); t2_lt = TABLA_LITROS.get(reporte.t2_cm, 0)
    t3_lt = TABLA_LITROS.get(reporte.t3_cm, 0); t4_lt = TABLA_LITROS.get(reporte.t4_cm, 0)
    t5_lt = TABLA_LITROS.get(reporte.t5_cm, 0); t6_lt = TABLA_LITROS.get(reporte.t6_cm, 0)
    total_bruto = t1_lt + t2_lt + t3_lt + t4_lt + t5_lt + t6_lt

    config = supabase.table("configuracion").select("*").eq("id", 1).execute().data[0]
    total_neto = total_bruto - config["fondo_muerto"]
    ventas_usd = total_neto * float(config["precio_litro"])

    datos_estado = {
        "status": reporte.status, "t1_cm": reporte.t1_cm, "t1_lt": t1_lt, "t2_cm": reporte.t2_cm, "t2_lt": t2_lt,
        "t3_cm": reporte.t3_cm, "t3_lt": t3_lt, "t4_cm": reporte.t4_cm, "t4_lt": t4_lt,
        "t5_cm": reporte.t5_cm, "t5_lt": t5_lt, "t6_cm": reporte.t6_cm, "t6_lt": t6_lt,
        "total_bruto": total_bruto, "total_neto": total_neto,
        "actualizado_por": reporte.usuario, "ultima_actualizacion": datetime.datetime.now().isoformat()
    }
    
    supabase.table("estado_estacion").update(datos_estado).eq("id", 1).execute()
    supabase.table("historial_reportes").insert({
        "status": reporte.status, "litros_disponibles": total_neto, "ventas_estimadas_usd": ventas_usd,
        "texto_reporte": generar_texto_wp(config, datos_estado), "generado_por": reporte.usuario
    }).execute()
    return {"exito": True}

@app.get("/panel_admin")
def obtener_panel_admin():
    estado = supabase.table("estado_estacion").select("*").eq("id", 1).execute().data[0]
    config = supabase.table("configuracion").select("*").eq("id", 1).execute().data[0]
    historial = supabase.table("historial_reportes").select("*").order("fecha", desc=True).limit(2).execute().data
    
    ventas_usd = estado["total_neto"] * float(config["precio_litro"])
    
    alerta = None
    if estado["total_neto"] < 0: alerta = "⚠️ ALERTA: BALANCE NEGATIVO."
    elif len(historial) == 2 and estado["status"] == "Abriendo Estación":
        diferencia = historial[0]["litros_disponibles"] - historial[1]["litros_disponibles"]
        if diferencia != 0: alerta = f"🚨 DESCUADRE DE APERTURA: {diferencia:,} Ltrs respecto al cierre."

    return {
        "estado": estado, "litros_disponibles": estado["total_neto"], "facturacion_usd": ventas_usd,
        "status_actual": estado["status"], "actualizado_por": estado["actualizado_por"],
        "reporte_whatsapp": generar_texto_wp(config, estado), "alerta": alerta
    }

@app.get("/historial")
def obtener_historial(): return supabase.table("historial_reportes").select("*").order("fecha", desc=True).limit(50).execute().data
@app.get("/configuracion")
def obtener_config(): return supabase.table("configuracion").select("*").eq("id", 1).execute().data[0]
@app.put("/configuracion")
def actualizar_config(datos: ConfigUpdate): supabase.table("configuracion").update({"fondo_muerto": datos.fondo_muerto, "precio_litro": datos.precio_litro}).eq("id", 1).execute(); return {"exito": True}
@app.get("/usuarios")
def obtener_usuarios(): return supabase.table("usuarios").select("username, rol").execute().data
@app.put("/usuarios/rol")
def actualizar_rol(datos: RolUpdate): supabase.table("usuarios").update({"rol": datos.rol}).eq("username", datos.username).execute(); return {"exito": True}