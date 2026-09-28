import flet as ft
import requests
import time
import threading

URL_SERVER = "http://127.0.0.1:8000"

def modulo_login(page: ft.Page, on_login_success):
    estado_login = {"es_primer_inicio": False, "usuario_pendiente": ""}

    tf_usuario = ft.TextField(label="Usuario", prefix_icon=ft.icons.PERSON, width=300, capitalization=ft.TextCapitalization.CHARACTERS, filled=True, bgcolor=ft.colors.with_opacity(0.4, ft.colors.BLACK))
    tf_pin = ft.TextField(label="PIN", password=True, prefix_icon=ft.icons.LOCK, width=300, filled=True, bgcolor=ft.colors.with_opacity(0.4, ft.colors.BLACK))
    btn_login = ft.ElevatedButton("Ingresar", width=300, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE, height=45)
    txt_instruccion = ft.Text("Estación de Servicio\nSanta Cruz", size=24, weight="bold", text_align=ft.TextAlign.CENTER)

    fondo_wallpaper = ft.Image(src="gasolina_wall.png", fit=ft.ImageFit.COVER, expand=True)

    caja_login = ft.Container(
        content=ft.Column([
            ft.Icon(ft.icons.LOCAL_GAS_STATION, size=70, color=ft.colors.BLUE_400), 
            txt_instruccion, ft.Container(height=20), tf_usuario, tf_pin, btn_login
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=30, border_radius=20, bgcolor=ft.colors.with_opacity(0.85, ft.colors.BLACK), visible=False 
    )

    vista_centrada = ft.Container(content=caja_login, alignment=ft.alignment.center, expand=True)
    contenedor = ft.Stack([fondo_wallpaper, vista_centrada], expand=True)

    def mostrar_alerta(mensaje, color):
        page.snack_bar = ft.SnackBar(ft.Text(mensaje, color=color)); page.snack_bar.open = True; page.update()

    def procesar_login(e):
        usuario = tf_usuario.value.upper().strip()
        pin = tf_pin.value
        
        if not usuario or not pin:
            mostrar_alerta("Ingresa usuario y PIN", "red"); return

        if estado_login["es_primer_inicio"] and usuario != estado_login["usuario_pendiente"]:
            estado_login["es_primer_inicio"] = False
            txt_instruccion.value = "Estación de Servicio\nSanta Cruz"
            txt_instruccion.color = ft.colors.WHITE

        btn_login.text = "Conectando..."; page.update()
        try:
            res = requests.post(f"{URL_SERVER}/login", json={"username": usuario, "pin": pin}).json()
            if res.get("exito"):
                page.client_storage.set("usuario_actual", res["username"])
                tf_usuario.value = ""; tf_pin.value = ""
                if estado_login["es_primer_inicio"]:
                    estado_login["es_primer_inicio"] = False
                    txt_instruccion.value = "Estación de Servicio\nSanta Cruz"
                    txt_instruccion.color = ft.colors.WHITE
                    mostrar_alerta("PIN configurado exitosamente", "green")
                on_login_success(res["rol"]) 
            else:
                if res.get("primer_inicio"):
                    estado_login["es_primer_inicio"] = True
                    estado_login["usuario_pendiente"] = usuario
                    txt_instruccion.value = f"¡Bienvenido {usuario}!\nCrea tu nuevo PIN:"
                    txt_instruccion.color = ft.colors.GREEN_400
                    tf_pin.value = ""
                    mostrar_alerta("Crea un PIN numérico seguro", "blue")
                else:
                    mostrar_alerta(res.get("mensaje", "Error"), "red")
        except:
             mostrar_alerta("Error conectando al servidor", "red")
             
        btn_login.text = "Ingresar"; page.update()

    btn_login.on_click = procesar_login

    def animar_splash():
        time.sleep(1.5)
        caja_login.visible = True
        page.update()

    threading.Thread(target=animar_splash).start()
    return contenedor