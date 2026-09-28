import flet as ft
import requests
import datetime
from auth import modulo_login 

def main(page: ft.Page):
    # --- 1. CONFIGURACIÓN GLOBAL ---
    page.title = "Santa Cruz Est."
    page.window_icon = "icono_gas.png" 
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 800
    page.window_resizable = False
    page.padding = 0 

    URL_SERVER = "http://127.0.0.1:8000"
    datos_historial = []; datos_consumos = []; datos_estado_actual = {}

    # --- 2. LÓGICA INTERNA ---
    def enviar_reporte(e, modo_edicion=False):
        estatus_val = dd_edit_status.value if modo_edicion else dd_status.value
        campos_cm = [tf_edit_t1, tf_edit_t2, tf_edit_t3, tf_edit_t4, tf_edit_t5, tf_edit_t6] if modo_edicion else [tf_t1, tf_t2, tf_t3, tf_t4, tf_t5, tf_t6]
        
        if not estatus_val: mostrar_alerta("Error: Debes seleccionar el Estatus.", "red"); return
        for i, tf in enumerate(campos_cm):
            if tf.value == "": mostrar_alerta(f"Error: Tanque {i+1} vacío. Pon 0 si no hay lectura.", "red"); return
            if int(tf.value) > 240: mostrar_alerta(f"Error: Tanque {i+1} no puede medir más de 240cm.", "red"); return

        usuario = page.client_storage.get("usuario_actual")
        datos = {
            "usuario": f"{usuario} (EDICIÓN)" if modo_edicion else usuario, "status": estatus_val,
            "t1_cm": int(campos_cm[0].value), "t2_cm": int(campos_cm[1].value), "t3_cm": int(campos_cm[2].value), 
            "t4_cm": int(campos_cm[3].value), "t5_cm": int(campos_cm[4].value), "t6_cm": int(campos_cm[5].value)
        }
        
        try:
            requests.post(f"{URL_SERVER}/cargar_datos", json=datos)
            mostrar_alerta("¡Datos guardados con éxito!", "green")
            if modo_edicion: modal_editar.open = False
            else: dd_status.value = None
            for tf in campos_cm: tf.value = ""
            if vista_dashboard.visible: cargar_datos_admin()
        except: mostrar_alerta("Error al enviar", "red")
        page.update()

    def cargar_datos_admin():
        nonlocal datos_estado_actual
        try:
            data = requests.get(f"{URL_SERVER}/panel_admin").json()
            datos_estado_actual = data["estado"]
            txt_litros.value = f"{data['litros_disponibles']:,.0f} Ltrs"; txt_usd.value = f"${data['facturacion_usd']:,.2f} USD"
            txt_estatus.value = data['status_actual']; txt_actualizado.value = f"Por: {data['actualizado_por']}"
            txt_reporte.value = data['reporte_whatsapp']
            
            if data["alerta"]:
                banner_alerta.content = ft.Text(data["alerta"], color=ft.colors.WHITE, weight="bold")
                banner_alerta.bgcolor = ft.colors.RED_800; banner_alerta.visible = True
            else: banner_alerta.visible = False
            page.update()
        except: pass

    def abrir_modal_edicion(e):
        dd_edit_status.value = datos_estado_actual["status"]
        tf_edit_t1.value = str(datos_estado_actual["t1_cm"]); tf_edit_t2.value = str(datos_estado_actual["t2_cm"])
        tf_edit_t3.value = str(datos_estado_actual["t3_cm"]); tf_edit_t4.value = str(datos_estado_actual["t4_cm"])
        tf_edit_t5.value = str(datos_estado_actual["t5_cm"]); tf_edit_t6.value = str(datos_estado_actual["t6_cm"])
        page.dialog = modal_editar; modal_editar.open = True; page.update()

    def crear_tanque_visual(nombre, litros_actuales, capacidad_max, alto=100, ancho=40):
        pct = min(litros_actuales / capacidad_max, 1.0)
        color = ft.colors.GREEN_500 if pct > 0.25 else ft.colors.RED_500
        return ft.Column([
            ft.Text(nombre, size=12, weight="bold"),
            ft.Container(width=ancho, height=alto, bgcolor=ft.colors.GREY_800, border_radius=5, alignment=ft.alignment.bottom_center, content=ft.Container(width=ancho, height=int(alto * pct), bgcolor=color, border_radius=5)),
            ft.Text(f"{int(pct*100)}%", size=10)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

    def cargar_graficas():
        try:
            estado = requests.get(f"{URL_SERVER}/panel_admin").json()["estado"]
            fila_tanques.controls.clear()
            cap = 36198
            fila_tanques.controls.extend([crear_tanque_visual(f"T{i+1}", estado[f"t{i+1}_lt"], cap) for i in range(6)])
            tanque_total.content = crear_tanque_visual("CAPACIDAD TOTAL", estado["total_bruto"], cap * 6, alto=120, ancho=300)
            page.update()
        except: pass

    def cargar_consumos():
        nonlocal datos_consumos
        try:
            historial = requests.get(f"{URL_SERVER}/historial").json()
            datos_consumos = []
            for i in range(len(historial) - 1):
                act = historial[i]; ant = historial[i+1]; dif = act['litros_disponibles'] - ant['litros_disponibles']
                f_leg = datetime.datetime.fromisoformat(act['fecha'].replace('Z', '+00:00')).strftime("%d/%m/%Y %I:%M %p")
                datos_consumos.append({"fecha_legible": f_leg, "status_actual": act['status'], "status_anterior": ant['status'], "diferencia": dif, "generado_por": act['generado_por']})
            render_consumos(datos_consumos)
        except: pass

    def render_consumos(lista):
        lista_consumos.controls.clear()
        for item in lista:
            dif = item["diferencia"]
            color, texto = (ft.colors.RED_400, f"🔽 {abs(dif):,.0f} Ltrs") if dif < 0 else (ft.colors.GREEN_400, f"🔼 {abs(dif):,.0f} Ltrs") if dif > 0 else (ft.colors.GREY_400, "➖ 0 Ltrs")
            lista_consumos.controls.append(ft.Card(content=ft.Container(padding=10, content=ft.Column([
                ft.Row([ft.Text(item['fecha_legible'], weight="bold", size=12), ft.Text(f"Por: {item['generado_por']}", size=12, italic=True)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(f"De: {item['status_anterior']} ➔ {item['status_actual']}", size=12, color=ft.colors.WHITE70),
                ft.Text(texto, size=16, weight="bold", color=color),
            ]))))
        page.update()

    def filtrar_consumos(e): render_consumos([item for item in datos_consumos if tf_buscar_consumos.value.lower() in item['fecha_legible'].lower() or tf_buscar_consumos.value.lower() in item['status_actual'].lower()])

    def cargar_historial():
        nonlocal datos_historial
        try:
            datos_historial = requests.get(f"{URL_SERVER}/historial").json()
            for item in datos_historial: item['fecha_legible'] = datetime.datetime.fromisoformat(item['fecha'].replace('Z', '+00:00')).strftime("%d/%m/%Y %I:%M %p")
            render_historial(datos_historial)
        except: pass

    def render_historial(lista):
        lista_historial.controls.clear()
        for item in lista:
            lista_historial.controls.append(ft.Card(content=ft.Container(padding=10, content=ft.Column([
                ft.Row([ft.Text(item['fecha_legible'], weight="bold", size=12), ft.Text(f"Por: {item['generado_por']}", size=12, italic=True)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(item['status'], color=ft.colors.AMBER_400),
                ft.Text(f"{item['litros_disponibles']:,} Ltrs", size=16, weight="bold"),
                ft.TextButton("Copiar WhatsApp", icon=ft.icons.COPY, on_click=lambda e, txt=item['texto_reporte']: page.set_clipboard(txt) or mostrar_alerta("¡Copiado!", "green"))
            ]))))
        page.update()

    def filtrar_historial(e): render_historial([item for item in datos_historial if tf_buscar_historial.value.lower() in item['fecha_legible'].lower() or tf_buscar_historial.value.lower() in item['status'].lower()])

    def cargar_ajustes():
        try:
            conf = requests.get(f"{URL_SERVER}/configuracion").json()
            tf_fondo.value = str(conf["fondo_muerto"]); tf_precio.value = str(conf["precio_litro"])
            dd_usuarios.options = [ft.dropdown.Option(u["username"]) for u in requests.get(f"{URL_SERVER}/usuarios").json()]
            page.update()
        except: pass

    def guardar_config(e):
        try:
            requests.put(f"{URL_SERVER}/configuracion", json={"fondo_muerto": int(tf_fondo.value), "precio_litro": float(tf_precio.value)})
            mostrar_alerta("Configuración guardada", "green")
        except: mostrar_alerta("Error al guardar", "red")

    def guardar_rol(e):
        if dd_usuarios.value and dd_rol.value:
            try:
                requests.put(f"{URL_SERVER}/usuarios/rol", json={"username": dd_usuarios.value, "rol": dd_rol.value})
                mostrar_alerta(f"Permisos actualizados", "green")
            except: mostrar_alerta("Error al actualizar", "red")

    # CREAR NUEVO USUARIO
    def crear_nuevo_usuario(e):
        usr = tf_nuevo_usuario.value.upper().strip()
        if not usr: return
        try:
            res = requests.post(f"{URL_SERVER}/usuarios/crear", json={"username": usr}).json()
            if res.get("exito"):
                mostrar_alerta(res["mensaje"], "green")
                modal_nuevo_user.open = False
                tf_nuevo_usuario.value = ""
                cargar_ajustes() 
            else:
                mostrar_alerta(res["mensaje"], "red")
        except: mostrar_alerta("Error de servidor", "red")
        page.update()

    def cerrar_sesion(e):
        page.client_storage.remove("usuario_actual")
        page.client_storage.remove("rol_usuario")
        contenedor_app.visible = False; vista_auth.visible = True; page.update()

    def cambiar_pestana_admin(nombre):
        if type(nombre) != str: nombre = nombre.control.text
        rol = page.client_storage.get("rol_usuario")
        
        for v in [vista_cargar, vista_dashboard, vista_graficas, vista_historial, vista_ajustes, vista_consumos]: v.visible = False
        
        # Filtro de Seguridad por Roles
        if nombre == "Cargar": dd_status.value = None; vista_cargar.visible = True
        elif nombre == "Gráficas": vista_graficas.visible = True
        elif rol == "admin":
            if nombre == "Dashboard": vista_dashboard.visible = True
            elif nombre == "Historial": vista_historial.visible = True
            elif nombre == "Ajustes": vista_ajustes.visible = True
            elif nombre == "Consumos": vista_consumos.visible = True
            else: vista_cargar.visible = True
        else:
            vista_cargar.visible = True
            nombre = "Cargar"

        # Lógica del menú superior
        if rol == "admin":
            btn_nav_dash.visible = (nombre != "Dashboard")
            btn_nav_cargar.visible = (nombre != "Cargar")
            btn_nav_graf.visible = (nombre != "Gráficas")
            menu_admin.visible = nombre in ["Cargar", "Dashboard", "Gráficas"]
        else:
            btn_nav_dash.visible = False
            btn_nav_cargar.visible = (nombre != "Cargar")
            btn_nav_graf.visible = (nombre != "Gráficas")
            menu_admin.visible = True 
        
        if vista_dashboard.visible: cargar_datos_admin()
        if vista_historial.visible: cargar_historial()
        if vista_ajustes.visible: cargar_ajustes()
        if vista_graficas.visible: cargar_graficas()
        if vista_consumos.visible: cargar_consumos()
        page.update()

    def mostrar_alerta(mensaje, color): page.snack_bar = ft.SnackBar(ft.Text(mensaje, color=color)); page.snack_bar.open = True; page.update()

    # --- 3. COMPONENTES VISUALES ---
    op_status = [ft.dropdown.Option("Abriendo Estación"), ft.dropdown.Option("Cerrado por Fin de Jornada"), ft.dropdown.Option("Cerrado Sin Combustible"), ft.dropdown.Option("Recepción de Cisterna")]
    
    btn_nav_dash = ft.ElevatedButton("Dashboard", icon=ft.icons.DASHBOARD, on_click=cambiar_pestana_admin, expand=1)
    btn_nav_cargar = ft.ElevatedButton("Cargar", icon=ft.icons.ADD_BOX, on_click=cambiar_pestana_admin, expand=1)
    btn_nav_graf = ft.ElevatedButton("Gráficas", icon=ft.icons.BAR_CHART, on_click=cambiar_pestana_admin, expand=1)
    menu_admin = ft.Container(content=ft.Row([btn_nav_dash, btn_nav_cargar, btn_nav_graf], spacing=5), visible=False, padding=ft.padding.only(bottom=15))

    btn_ajustes_dash = ft.IconButton(ft.icons.SETTINGS, on_click=lambda _: cambiar_pestana_admin("Ajustes"), icon_color=ft.colors.WHITE70, visible=False)

    # VISTA CARGAR
    dd_status = ft.Dropdown(options=op_status, label="Seleccione el Estatus...", width=320)
    ancho_tf = 150
    tf_t1 = ft.TextField(label="T1 (cm)", width=ancho_tf, keyboard_type=ft.KeyboardType.NUMBER); tf_t2 = ft.TextField(label="T2 (cm)", width=ancho_tf, keyboard_type=ft.KeyboardType.NUMBER)
    tf_t3 = ft.TextField(label="T3 (cm)", width=ancho_tf, keyboard_type=ft.KeyboardType.NUMBER); tf_t4 = ft.TextField(label="T4 (cm)", width=ancho_tf, keyboard_type=ft.KeyboardType.NUMBER)
    tf_t5 = ft.TextField(label="T5 (cm)", width=ancho_tf, keyboard_type=ft.KeyboardType.NUMBER); tf_t6 = ft.TextField(label="T6 (cm)", width=ancho_tf, keyboard_type=ft.KeyboardType.NUMBER)
    btn_enviar = ft.ElevatedButton("Enviar Reporte", on_click=enviar_reporte, width=320, bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE, height=50)
    vista_cargar = ft.Column([ft.Row([ft.Text("Módulo de Medición", size=18, weight="bold"), ft.IconButton(ft.icons.LOGOUT, on_click=cerrar_sesion, icon_color=ft.colors.RED_400)]), ft.Divider(), dd_status, ft.Row([tf_t1, tf_t2], spacing=20, alignment=ft.MainAxisAlignment.CENTER), ft.Row([tf_t3, tf_t4], spacing=20, alignment=ft.MainAxisAlignment.CENTER), ft.Row([tf_t5, tf_t6], spacing=20, alignment=ft.MainAxisAlignment.CENTER), ft.Container(height=10), btn_enviar], visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # MODALES ADMIN
    dd_edit_status = ft.Dropdown(options=op_status, label="Corregir Estatus", width=320)
    tf_edit_t1 = ft.TextField(label="T1 (cm)", width=130, keyboard_type=ft.KeyboardType.NUMBER); tf_edit_t2 = ft.TextField(label="T2 (cm)", width=130, keyboard_type=ft.KeyboardType.NUMBER)
    tf_edit_t3 = ft.TextField(label="T3 (cm)", width=130, keyboard_type=ft.KeyboardType.NUMBER); tf_edit_t4 = ft.TextField(label="T4 (cm)", width=130, keyboard_type=ft.KeyboardType.NUMBER)
    tf_edit_t5 = ft.TextField(label="T5 (cm)", width=130, keyboard_type=ft.KeyboardType.NUMBER); tf_edit_t6 = ft.TextField(label="T6 (cm)", width=130, keyboard_type=ft.KeyboardType.NUMBER)
    modal_editar = ft.AlertDialog(title=ft.Text("Corregir Reporte", size=16), content=ft.Column([dd_edit_status, ft.Row([tf_edit_t1, tf_edit_t2]), ft.Row([tf_edit_t3, tf_edit_t4]), ft.Row([tf_edit_t5, tf_edit_t6])], height=280), actions=[ft.TextButton("Cancelar", on_click=lambda e: setattr(modal_editar, 'open', False) or page.update()), ft.ElevatedButton("Sobrescribir", on_click=lambda e: enviar_reporte(e, modo_edicion=True), bgcolor=ft.colors.RED_700, color=ft.colors.WHITE)])

    tf_nuevo_usuario = ft.TextField(label="Nombre de Usuario", capitalization=ft.TextCapitalization.CHARACTERS, width=280)
    modal_nuevo_user = ft.AlertDialog(title=ft.Text("Nuevo Usuario", size=16), content=tf_nuevo_usuario, actions=[ft.TextButton("Cancelar", on_click=lambda e: setattr(modal_nuevo_user, 'open', False) or page.update()), ft.ElevatedButton("Crear", on_click=crear_nuevo_usuario, bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE)])

    # VISTA DASHBOARD 
    banner_alerta = ft.Container(padding=10, border_radius=5, visible=False)
    txt_estatus = ft.Text("ESTATUS", size=22, weight="bold", color=ft.colors.AMBER_400)
    txt_litros = ft.Text("0 Ltrs", size=40, weight="bold", color=ft.colors.GREEN_400)
    txt_usd = ft.Text("$0.00 USD", size=22, color=ft.colors.WHITE70)
    txt_actualizado = ft.Text("Última actualización: -", size=12, italic=True)
    txt_reporte = ft.TextField(multiline=True, read_only=True, height=200, text_size=12, width=320)
    vista_dashboard = ft.Column([
        ft.Row([ft.Text("Panel", size=18, weight="bold"), ft.Row([btn_ajustes_dash, ft.IconButton(ft.icons.LOGOUT, on_click=cerrar_sesion, icon_color=ft.colors.RED_400)])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
        ft.Divider(), banner_alerta, txt_estatus, ft.Text("Disponible para Venta:", size=14), txt_litros, txt_usd, txt_actualizado, 
        ft.Row([ft.ElevatedButton("Copiar Reporte", on_click=lambda e: page.set_clipboard(txt_reporte.value) or mostrar_alerta("Copiado", "green"), icon=ft.icons.COPY, bgcolor=ft.colors.GREEN_800, color=ft.colors.WHITE), ft.IconButton(ft.icons.EDIT, on_click=abrir_modal_edicion, icon_color=ft.colors.ORANGE_400, tooltip="Editar Reporte")], alignment=ft.MainAxisAlignment.CENTER, spacing=10), 
        ft.Container(height=5), txt_reporte, ft.Divider(),
        ft.ElevatedButton("Ver Historial de Reportes", icon=ft.icons.HISTORY, on_click=lambda _: cambiar_pestana_admin("Historial"), width=320, height=45)
    ], visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # VISTA GRÁFICAS 
    fila_tanques = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
    tanque_total = ft.Container()
    vista_graficas = ft.Column([
        ft.Row([ft.Text("Análisis e Inventario", size=18, weight="bold"), ft.IconButton(ft.icons.LOGOUT, on_click=cerrar_sesion, icon_color=ft.colors.RED_400)]), 
        ft.Divider(), ft.ElevatedButton("Historial de Consumos", icon=ft.icons.SHOW_CHART, on_click=lambda _: cambiar_pestana_admin("Consumos"), width=320, height=45, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE),
        ft.Container(height=10), ft.Text("Tanques Individuales", size=12, color=ft.colors.WHITE70),
        ft.Container(content=fila_tanques, padding=15, bgcolor=ft.colors.BLACK26, border_radius=10),
        ft.Container(height=10), ft.Text("Inventario Bruto Total", size=12, color=ft.colors.WHITE70),
        ft.Container(content=tanque_total, padding=15, bgcolor=ft.colors.BLACK26, border_radius=10),
    ], visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # VISTAS SECUNDARIAS
    tf_buscar_consumos = ft.TextField(hint_text="Buscar por fecha...", prefix_icon=ft.icons.SEARCH, on_change=filtrar_consumos, height=45, text_size=13)
    lista_consumos = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=550)
    vista_consumos = ft.Column([ft.Row([ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: cambiar_pestana_admin("Gráficas")), ft.Text("Historial de Consumos", size=18, weight="bold")]), ft.Divider(), tf_buscar_consumos, lista_consumos], visible=False)

    tf_buscar_historial = ft.TextField(hint_text="Buscar fecha...", prefix_icon=ft.icons.SEARCH, on_change=filtrar_historial, height=45, text_size=13)
    lista_historial = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=550)
    vista_historial = ft.Column([ft.Row([ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: cambiar_pestana_admin("Dashboard")), ft.Text("Auditoría de Reportes", size=18, weight="bold")]), ft.Divider(), tf_buscar_historial, lista_historial], visible=False)

    tf_fondo = ft.TextField(label="Fondo Muerto (Litros)", keyboard_type=ft.KeyboardType.NUMBER, width=320); tf_precio = ft.TextField(label="Precio por Litro ($)", keyboard_type=ft.KeyboardType.NUMBER, width=320)
    dd_usuarios = ft.Dropdown(label="Seleccionar Usuario", width=320); dd_rol = ft.Dropdown(options=[ft.dropdown.Option("operario"), ft.dropdown.Option("admin")], label="Asignar Rol", width=320)
    vista_ajustes = ft.Column([
        ft.Row([ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: cambiar_pestana_admin("Dashboard")), ft.Text("Administración", size=18, weight="bold")]), 
        ft.Divider(), ft.Text("Configuración", weight="bold", color=ft.colors.BLUE_400), tf_fondo, tf_precio, ft.ElevatedButton("Guardar Configuración", icon=ft.icons.SAVE, on_click=guardar_config, width=320), 
        ft.Container(height=20), 
        ft.Row([ft.Text("Usuarios", weight="bold", color=ft.colors.BLUE_400), ft.IconButton(icon=ft.icons.PERSON_ADD, icon_color=ft.colors.GREEN_400, on_click=lambda e: setattr(page, 'dialog', modal_nuevo_user) or setattr(modal_nuevo_user, 'open', True) or page.update())], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=320),
        dd_usuarios, dd_rol, ft.ElevatedButton("Actualizar Permisos", icon=ft.icons.SECURITY, on_click=guardar_rol, width=320)
    ], visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # --- 4. PUENTE ENTRE ARCHIVOS ---
    contenedor_app = ft.Container(padding=20, visible=False, expand=True, content=ft.Column([menu_admin, vista_cargar, vista_dashboard, vista_graficas, vista_consumos, vista_historial, vista_ajustes], scroll=ft.ScrollMode.AUTO))

    def al_loguearse(rol):
        page.client_storage.set("rol_usuario", rol)
        vista_auth.visible = False; contenedor_app.visible = True
        if rol == "admin": btn_ajustes_dash.visible = True; cambiar_pestana_admin("Dashboard")
        else: btn_ajustes_dash.visible = False; cambiar_pestana_admin("Cargar")
        page.update()

    vista_auth = modulo_login(page, al_loguearse)
    page.add(vista_auth, contenedor_app)

ft.app(target=main, assets_dir="assets")