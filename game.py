# file: game.py
"""
Juego-simulador didáctico de un puesto de limonada para Bachillerato.
Contiene toda la lógica del juego y una API REST (Flask) para que el frontend
consuma los datos.

Conceptos contables modelados:
- Balance (Activo / Pasivo + Patrimonio Neto)
- Cuenta de resultados (Ingresos - Gastos)
- Flujo de efectivo (cobros y pagos)
- Diferencia entre beneficio contable y caja
- Inventarios (ingredientes y limonada preparada)

Autor: Código didáctico (en español)
"""

from dataclasses import dataclass, asdict
from flask import Flask, jsonify, request, send_from_directory
import random
import math
import threading

# ---------------------- CONSTANTES DE COSTES ----------------------
COSTE_LIMON = 0.50      # coste por limón (€)
COSTE_AZUCAR = 0.10     # coste por ración de azúcar (€) (p. ej. por cucharada)
COSTE_VASO = 0.08       # coste por vaso desechable (€)
COSTE_PUBLICIDAD_BASE = 5.0  # coste por campaña diaria de publicidad (€)

# Recursos necesarios por 1 vaso de limonada
INGREDIENTES_POR_VASO = {
    "limon": 1,
    "azucar": 1,
    "vaso": 1
}

# Días por defecto del juego
DIAS_TOTALES = 7

# ---------------------- DATACLASS PARA EL ESTADO ----------------------
@dataclass
class EstadoFinanciero:
    """
    Guarda el estado interno del juego; es la "fuente de la verdad".
    """
    dia: int = 1
    dias_totales: int = DIAS_TOTALES

    # Caja / efectivo
    caja: float = 100.0      # capital inicial en euros

    # Inventario de ingredientes (unidades físicas)
    inventario_limones: int = 0
    inventario_azucar: int = 0
    inventario_vasos: int = 0

    # Inventario de limonada preparada (unidades) y su coste acumulado (euros)
    inventario_limonada: int = 0
    coste_inventario_limonada: float = 0.0  # coste total de la limonada preparada no vendida

    # Parámetros de la tienda
    precio_venta: float = 1.0  # precio por vaso fijado por el alumno

    # Producción acumulada en el día (si se produce varias veces, se acumula)
    producidas_hoy: int = 0

    # Contabilidad acumulada (para la cuenta de resultados)
    ingresos_acumulados: float = 0.0
    coste_ventas_acumulado: float = 0.0
    gastos_operativos_acumulado: float = 0.0

    # Flujo de caja acumulado (historia)
    cobros_acumulados: float = 0.0
    pagos_acumulados: float = 0.0

    # Capital aportado inicialmente (patrimonio)
    capital_inicial: float = 100.0

    # Beneficios acumulados (resultado acumulado)
    beneficios_acumulados: float = 0.0

    # Pasivo simple (por si hay préstamos en el futuro)
    deuda: float = 0.0

    # Ultimas operaciones del día (para mostrar al alumno)
    resumen_ultimo_dia: str = ""

    # Parámetros adicionales: nivel de inversión en calidad (mejora la demanda)
    nivel_calidad: int = 0  # 0 = normal, +1 +2 etc. (por compra de mejoras - opcional)

    # Registro histórico simple (lista de dict por día)
    historial: list = None

    def __post_init__(self):
        if self.historial is None:
            self.historial = []

# ---------------------- CLASE PRINCIPAL DEL JUEGO ----------------------
class LemonadeGame:
    """
    Clase principal que contiene la lógica del juego y cálculos contables.
    """

    def __init__(self):
        self.estado = EstadoFinanciero()
        # Semejanza pedagógica: caja y capital inicial iguales al empezar
        self.estado.caja = self.estado.capital_inicial
        # Mensaje inicial explicativo para alumnos
        self.estado.resumen_ultimo_dia = (
            "Bienvenido. Decide precio, compras y producción. Cada día simulas ventas."
        )
        # bloquear redeploy / concurrencia básica (simple)
        self.lock = threading.Lock()
        # generar clima inicial
        self._generar_clima()

    # ---------------------- UTILIDADES ----------------------
    def _precio_ingredientes_por_vaso(self) -> float:
        """Devuelve el coste de ingredientes para 1 vaso (suma)."""
        return COSTE_LIMON * INGREDIENTES_POR_VASO["limon"] + \
               COSTE_AZUCAR * INGREDIENTES_POR_VASO["azucar"] + \
               COSTE_VASO * INGREDIENTES_POR_VASO["vaso"]

    def _generar_clima(self):
        """Genera un clima simple que afecta a la demanda: Caluroso/Templado/Frío."""
        self.clima = random.choices(["Caluroso", "Templado", "Frío"], weights=[0.35, 0.50, 0.15])[0]
        # demanda base según clima (clientes potenciales)
        if self.clima == "Caluroso":
            self.demanda_base = random.randint(60, 110)
        elif self.clima == "Templado":
            self.demanda_base = random.randint(30, 70)
        else:
            self.demanda_base = random.randint(5, 35)

    # ---------------------- ACCIONES DEL JUGADOR ----------------------
    def comprar_ingredientes(self, limones: int = 0, azucar: int = 0, vasos: int = 0) -> dict:
        """
        Compra ingredientes: paga al contado (caja disminuye) y aumenta inventario.
        Devuelve dict con resultado y mensaje.
        """
        with self.lock:
            limones = max(0, int(limones))
            azucar = max(0, int(azucar))
            vasos = max(0, int(vasos))
            coste_total = limones * COSTE_LIMON + azucar * COSTE_AZUCAR + vasos * COSTE_VASO

            if coste_total > self.estado.caja + 1e-9:
                return {"ok": False, "mensaje": "No hay suficiente caja para esa compra."}

            # Pago inmediato (flujo de caja)
            self.estado.caja -= coste_total
            self.estado.pagos_acumulados += coste_total
            # Aumenta inventarios físicos
            self.estado.inventario_limones += limones
            self.estado.inventario_azucar += azucar
            self.estado.inventario_vasos += vasos

            mensaje = f"Compraste {limones} limones, {azucar} azúcar, {vasos} vasos. Gastaste {coste_total:.2f} €."
            # registrar gasto operativo si quieres (aquí lo consideramos compra, no gasto operativo)
            # devolvemos también el estado de caja
            return {"ok": True, "mensaje": mensaje, "coste": round(coste_total,2), "caja": round(self.estado.caja,2)}

    def fijar_precio(self, precio: float) -> dict:
        """Fija el precio de venta por vaso."""
        with self.lock:
            try:
                p = float(precio)
                if p <= 0:
                    return {"ok": False, "mensaje": "El precio debe ser mayor que 0."}
                self.estado.precio_venta = round(p, 2)
                return {"ok": True, "mensaje": f"Precio fijado a {self.estado.precio_venta:.2f} €."}
            except Exception:
                return {"ok": False, "mensaje": "Precio inválido."}

    def producir(self, cantidad: int) -> dict:
        """
        Produce 'cantidad' vasos de limonada:
         - consume ingredientes del inventario
         - aumenta inventario_limonada
         - calcula y acumula el coste asociado a esas unidades (para contabilizar coste de ventas cuando se vendan)
        Se ACUMULA si se llama varias veces el mismo día.
        """
        with self.lock:
            cantidad = max(0, int(cantidad))
            # máxima producción posible según ingredientes disponibles
            max_posible = min(
                self.estado.inventario_limones // INGREDIENTES_POR_VASO["limon"],
                self.estado.inventario_azucar // INGREDIENTES_POR_VASO["azucar"],
                self.estado.inventario_vasos // INGREDIENTES_POR_VASO["vaso"]
            )
            a_producir = min(cantidad, max_posible)
            if a_producir <= 0:
                return {"ok": False, "mensaje": "No hay ingredientes suficientes para producir."}

            # consumir ingredientes
            self.estado.inventario_limones -= a_producir * INGREDIENTES_POR_VASO["limon"]
            self.estado.inventario_azucar -= a_producir * INGREDIENTES_POR_VASO["azucar"]
            self.estado.inventario_vasos -= a_producir * INGREDIENTES_POR_VASO["vaso"]

            # aumentar inventario de limonada preparada
            coste_unitario = self._precio_ingredientes_por_vaso()
            coste_total_nueva = coste_unitario * a_producir
            self.estado.inventario_limonada += a_producir
            self.estado.coste_inventario_limonada += coste_total_nueva

            # producidas hoy (acumulativo)
            self.estado.producidas_hoy += a_producir

            mensaje = f"Producidas {a_producir} unidades. Coste añadido {coste_total_nueva:.2f} €."
            return {"ok": True, "mensaje": mensaje, "producidas_hoy": self.estado.producidas_hoy}

    def campaña_publicidad(self, gasto: float) -> dict:
        """
        Gasta en publicidad: reduce caja y aumenta una variable que hará crecer la demanda.
        Esta función es un ejemplo de gasto operativo.
        """
        with self.lock:
            gasto = max(0.0, float(gasto))
            if gasto > self.estado.caja + 1e-9:
                return {"ok": False, "mensaje": "No hay caja suficiente para la campaña."}
            self.estado.caja -= gasto
            self.estado.pagos_acumulados += gasto
            self.estado.gastos_operativos_acumulado += gasto
            # traducimos gasto en publicidad a aumento de 'nivel_calidad' temporal
            aumento = int(gasto // COSTE_PUBLICIDAD_BASE)
            self.estado.nivel_calidad += aumento
            mensaje = f"Campaña realizada. Gasto {gasto:.2f} €. Aumento de visibilidad: +{aumento}."
            return {"ok": True, "mensaje": mensaje}

    # ---------------------- SIMULACIÓN DEL DÍA ----------------------
    def _calcular_demanda(self) -> int:
        """
        Calcula la demanda real atendiendo a:
         - demanda base por clima
         - sensibilidad al precio (precios altos reducen demanda)
         - efecto de la calidad/marketing (nivel_calidad)
        """
        precio = self.estado.precio_venta
        demanda = self.demanda_base

        # penalización por precio relativo al coste (si el precio es muy alto, baja demanda)
        coste_base = self._precio_ingredientes_por_vaso()
        # sensibilidad simple: cuanto mayor sea ratio precio/coste, mayor probabilidad de reducir demanda
        ratio = precio / (coste_base + 1e-6)
        if ratio > 3.0:
            demanda = int(demanda * 0.3)
        elif ratio > 2.0:
            demanda = int(demanda * 0.6)
        elif ratio > 1.5:
            demanda = int(demanda * 0.8)
        # precio bajo puede aumentar un poco la demanda
        elif ratio < 0.8:
            demanda = int(demanda * 1.15)

        # efecto de la calidad (marketing / inversiones)
        demanda += self.estado.nivel_calidad * 8

        # ruido aleatorio pequeño
        demanda = max(0, int(demanda + random.randint(-5, 5)))
        return demanda

    def simular_dia(self, gastar_publicidad: float = 0.0) -> dict:
        """
        Simula el día:
         - opcionalmente se puede gastar en publicidad antes de las ventas
         - calcula demanda, ventas, ingresos, coste de ventas, beneficio del día
         - actualiza caja (cobros) y contabilidad acumulada
         - vacía producidas_hoy (pero inventario_limonada se reduce según ventas)
         - genera resumen del día para mostrar en UI
        """
        with self.lock:
            # aplicar publicidad si se pide
            if gastar_publicidad and gastar_publicidad > 0:
                pub = self.campaña_publicidad(gastar_publicidad)
                # la campaña_publicidad ya actualiza caja y gastos_operativos

            # calcular demanda y ventas
            demanda = self._calcular_demanda()
            ventas_posibles = min(self.estado.inventario_limonada, demanda)
            unidades_vendidas = ventas_posibles

            ingresos = unidades_vendidas * self.estado.precio_venta

            # coste de ventas: calculamos coste por unidad de limonada en inventario (media ponderada)
            coste_total_inventario = self.estado.coste_inventario_limonada
            inventario_total = self.estado.inventario_limonada
            coste_por_unidad = 0.0
            coste_ventas = 0.0
            if inventario_total > 0:
                # si vendemos N, restamos proporcionalmente del coste del inventario
                coste_por_unidad = coste_total_inventario / inventario_total
                coste_ventas = coste_por_unidad * unidades_vendidas
            else:
                coste_ventas = 0.0

            # actualizar inventario físico y coste del inventario remanente
            self.estado.inventario_limonada -= unidades_vendidas
            # reducimos el coste acumulado proporcionalmente
            self.estado.coste_inventario_limonada -= coste_ventas
            # evitar negativos por redondeo
            self.estado.coste_inventario_limonada = max(0.0, round(self.estado.coste_inventario_limonada, 4))

            # actualizar caja y flujos
            self.estado.caja += ingresos
            self.estado.cobros_acumulados += ingresos

            # actualizar cuenta de resultados acumulada
            self.estado.ingresos_acumulados += ingresos
            self.estado.coste_ventas_acumulado += coste_ventas

            # gastos operativos (ya actualizados vía campaña_publicidad si se usó)
            gasto_operativo_hoy = 0.0  # por ahora no hay otros gastos diarios automáticos
            self.estado.gastos_operativos_acumulado += gasto_operativo_hoy

            # beneficio del día (simplificado)
            beneficio_dia = ingresos - coste_ventas - gasto_operativo_hoy

            # actualizar beneficios acumulados y patrimonio
            self.estado.beneficios_acumulados += beneficio_dia

            # registro del día (historial)
            resumen = {
                "dia": self.estado.dia,
                "clima": self.clima,
                "demanda": demanda,
                "vendido": unidades_vendidas,
                "ingresos": round(ingresos,2),
                "coste_ventas": round(coste_ventas,2),
                "beneficio_dia": round(beneficio_dia,2),
                "caja": round(self.estado.caja,2)
            }
            self.estado.historial.append(resumen)

            # texto resumen para UI
            texto_resumen = (
                f"Día {self.estado.dia}: clima {self.clima}. "
                f"Demanda estimada {demanda}. Vendiste {unidades_vendidas} vasos. "
                f"Ingresos {ingresos:.2f} €. Coste ventas {coste_ventas:.2f} €. "
                f"Caja final {self.estado.caja:.2f} €."
            )
            self.estado.resumen_ultimo_dia = texto_resumen

            # preparar siguiente día
            self.estado.dia += 1
            self.estado.producidas_hoy = 0
            # regenerar clima para el día siguiente (si no se ha acabado)
            if self.estado.dia <= self.estado.dias_totales:
                self._generar_clima()

            # devolver resumen del día
            return {"ok": True, "resumen": resumen, "mensaje": texto_resumen}

    # ---------------------- CÁLCULOS CONTABLES PARA FRONTEND ----------------------
    def calcular_balance(self) -> dict:
        """
        Calcula un balance simplificado:
         ACTIVO:
           - caja (efectivo)
           - existencias: valor de ingredientes + valor de limonada preparada
           - inmovilizado: (0 por ahora)
         PASIVO:
           - deuda
         PATRIMONIO NETO:
           - capital inicial + beneficios acumulados - deuda
        """
        # valor existencias ingredientes
        valor_limones = self.estado.inventario_limones * COSTE_LIMON
        valor_azucar = self.estado.inventario_azucar * COSTE_AZUCAR
        valor_vasos = self.estado.inventario_vasos * COSTE_VASO
        valor_ingredientes = valor_limones + valor_azucar + valor_vasos

        # valor limonada preparada = coste_inventario_limonada
        valor_limonada_preparada = round(self.estado.coste_inventario_limonada, 2)

        activo = {
            "caja": round(self.estado.caja, 2),
            "existencias_ingredientes": round(valor_ingredientes, 2),
            "existencias_limonada": valor_limonada_preparada,
            "inmovilizado": 0.0
        }
        total_activo = round(sum(activo.values()), 2)
        pasivo = {
            "deuda": round(self.estado.deuda, 2)
        }
        patrimonio = {
            "capital_inicial": round(self.estado.capital_inicial, 2),
            "beneficios_acumulados": round(self.estado.beneficios_acumulados, 2)
        }
        total_pasivo_patrimonio = round(pasivo["deuda"] + patrimonio["capital_inicial"] + patrimonio["beneficios_acumulados"], 2)
        return {
            "activo": activo,
            "total_activo": total_activo,
            "pasivo": pasivo,
            "patrimonio": patrimonio,
            "total_pasivo_patrimonio": total_pasivo_patrimonio,
            "explicacion_activo": "El ACTIVO muestra lo que tiene la empresa (caja y existencias).",
            "explicacion_pasivo": "El PASIVO y PATRIMONIO muestran cómo se ha financiado (deudas y aportaciones/beneficios)."
        }

    def calcular_cuenta_resultados(self) -> dict:
        """
        Devuelve la cuenta de resultados acumulada (ingresos y gastos).
        """
        ingresos = round(self.estado.ingresos_acumulados, 2)
        coste_ventas = round(self.estado.coste_ventas_acumulado, 2)
        gastos = round(self.estado.gastos_operativos_acumulado, 2)
        beneficio = round(ingresos - coste_ventas - gastos, 2)
        return {
            "ingresos": ingresos,
            "coste_ventas": coste_ventas,
            "gastos_operativos": gastos,
            "beneficio": beneficio,
            "explicacion": "Aquí ves cuánto has vendido (ingresos) y cuánto te ha costado vender (coste de ventas)."
        }

    def calcular_flujo_efectivo(self) -> dict:
        """
        Flujo de caja simple: cobros menos pagos.
        """
        cobros = round(self.estado.cobros_acumulados, 2)
        pagos = round(self.estado.pagos_acumulados, 2)
        saldo_caja = round(self.estado.caja, 2)
        return {
            "cobros": cobros,
            "pagos": pagos,
            "saldo_caja": saldo_caja,
            "explicacion": "La caja muestra cuánto dinero tienes ahora mismo (cobros y pagos reales)."
        }

    def get_estado_publico(self) -> dict:
        """
        Devuelve todo lo necesario para el frontend:
        - estado básico (dia, inventarios, caja, precio)
        - estados financieros calculados (balance, cuenta de resultados, flujo de efectivo)
        - resumen del último día y el historial
        """
        with self.lock:
            balance = self.calcular_balance()
            cuenta = self.calcular_cuenta_resultados()
            flujo = self.calcular_flujo_efectivo()
            publico = {
                "dia": self.estado.dia,
                "dias_totales": self.estado.dias_totales,
                "caja": round(self.estado.caja, 2),
                "inventario_limones": self.estado.inventario_limones,
                "inventario_azucar": self.estado.inventario_azucar,
                "inventario_vasos": self.estado.inventario_vasos,
                "inventario_limonada": self.estado.inventario_limonada,
                "producidas_hoy": self.estado.producidas_hoy,
                "precio_venta": round(self.estado.precio_venta, 2),
                "clima": self.clima,
                "demanda_base": self.demanda_base,
                "resumen_ultimo_dia": self.estado.resumen_ultimo_dia,
                "historial": self.estado.historial[-10:],  # últimos 10 días
                "balance": balance,
                "cuenta_resultados": cuenta,
                "flujo_efectivo": flujo
            }
            return publico

    def reset(self) -> dict:
        """Reinicia el juego al estado inicial (útil para demos)."""
        with self.lock:
            self.estado = EstadoFinanciero()
            self.estado.caja = self.estado.capital_inicial
            self.estado.resumen_ultimo_dia = "Juego reiniciado. Buenas prácticas: comienza comprando ingredientes."
            self.estado.historial = []
            self.estado.nivel_calidad = 0
            self._generar_clima()
            return self.get_estado_publico()

# ---------------------- FLASK: API REST DENTRO DE game.py ----------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
juego = LemonadeGame()

@app.route("/")
def index():
    # servir index.html desde templates para pruebas locales o Render
    try:
        return send_from_directory("templates", "index.html")
    except Exception:
        return jsonify({"ok": False, "mensaje": "Falta el frontend. Sube templates/index.html"}), 404

@app.route("/api/state", methods=["GET"])
def api_state():
    """Devuelve el estado completo para el frontend."""
    return jsonify(juego.get_estado_publico())

@app.route("/api/buy", methods=["POST"])
def api_buy():
    data = request.get_json() or {}
    lim = int(data.get("limones", 0))
    az = int(data.get("azucar", 0))
    vas = int(data.get("vasos", 0))
    res = juego.comprar_ingredientes(lim, az, vas)
    return jsonify(res)

@app.route("/api/produce", methods=["POST"])
def api_produce():
    data = request.get_json() or {}
    qty = int(data.get("cantidad", 0))
    res = juego.producir(qty)
    return jsonify(res)

@app.route("/api/set_price", methods=["POST"])
def api_set_price():
    data = request.get_json() or {}
    precio = float(data.get("precio", juego.estado.precio_venta))
    res = juego.fijar_precio(precio)
    return jsonify(res)

@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    data = request.get_json() or {}
    gasto_pub = float(data.get("gasto_publicidad", 0.0))
    res = juego.simular_dia(gasto_pub)
    # además devolver nuevo estado público
    estado = juego.get_estado_publico()
    return jsonify({"ok": True, "resultado_simulacion": res, "estado": estado})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    estado = juego.reset()
    return jsonify({"ok": True, "estado": estado})

# Endpoint para servir estáticos si usas la estructura propuesta
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# ---------------------- EJECUTABLE COMO SERVIDOR ----------------------
if __name__ == "__main__":
    # para pruebas locales: python game.py
    app.run(host="0.0.0.0", port=5000, debug=True)
