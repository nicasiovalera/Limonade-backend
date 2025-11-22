# file: game.py
import random
from dataclasses import dataclass, asdict

COST_LEMON = 0.5
COST_SUGAR = 0.2
COST_CUP = 0.1
TOTAL_DAYS = 7

@dataclass
class GameState:
    day: int = 1
    total_days: int = TOTAL_DAYS
    money: float = 50.0
    lemons: int = 0
    sugar: int = 0
    cups: int = 0
    weather: str = "Templado"
    demand: int = 0
    price: float = 1.0
    produced: int = 0
    message: str = "Bienvenido al Puesto de Limonadas!"
    running: bool = True

    def to_dict(self):
        return asdict(self)

class Game:
    def __init__(self):
        self.state = GameState()
        self.generate_weather()

    def reset(self):
        self.state = GameState()
        self.generate_weather()
        return self.state.to_dict()

    def generate_weather(self):
        w = random.choices(["Caluroso", "Templado", "Frío"], weights=[0.35, 0.45, 0.20])[0]
        self.state.weather = w
        if w == "Caluroso":
            self.state.demand = random.randint(60, 100)
        elif w == "Templado":
            self.state.demand = random.randint(40, 70)
        else:
            self.state.demand = random.randint(10, 40)

    def buy(self, lemons: int, sugar: int, cups: int):
        lemons = max(0, int(lemons))
        sugar = max(0, int(sugar))
        cups = max(0, int(cups))
        total = lemons * COST_LEMON + sugar * COST_SUGAR + cups * COST_CUP
        if total > self.state.money + 1e-9:
            self.state.message = "No tienes dinero suficiente para esa compra."
            return False
        self.state.money -= total
        self.state.lemons += lemons
        self.state.sugar += sugar
        self.state.cups += cups
        self.state.message = f"Compraste {lemons} limones, {sugar} azúcar, {cups} vasos. Gastaste ${total:.2f}."
        return True

    def set_price(self, price: float):
        try:
            p = float(price)
            if p <= 0:
                self.state.message = "El precio debe ser mayor que 0."
                return False
            self.state.price = round(p, 2)
            self.state.message = f"Precio fijado: ${self.state.price:.2f} por vaso."
            return True
        except Exception:
            self.state.message = "Precio inválido."
            return False

    def produce(self, qty: int):
        qty = max(0, int(qty))
        max_possible = min(self.state.lemons, self.state.sugar, self.state.cups)
        produce = min(qty, max_possible)
        self.state.lemons -= produce
        self.state.sugar -= produce
        self.state.cups -= produce
        self.state.produced = produce
        if produce == 0:
            self.state.message = "No se pudo producir (falta inventario o cantidad 0)."
            return False
        self.state.message = f"Produjiste {produce} limonadas."
        return True

    def adjust_demand_by_price(self):
        p = self.state.price
        penalty = 0.0
        if p > 2.0:
            penalty = 0.5
        elif p > 1.5:
            penalty = 0.3
        elif p > 1.0:
            penalty = 0.15
        bonus = 0.2 if p < 0.5 else 0.0
        adjusted = int(self.state.demand * (1 - penalty + bonus))
        return max(0, adjusted)

    def simulate_day(self):
        if not self.state.running:
            self.state.message = "El juego ya terminó."
            return self.state.to_dict()
        if self.state.produced <= 0:
            self.state.message = "No produjiste limonadas hoy; no hay ventas."
            sales = 0
        else:
            demand = self.adjust_demand_by_price()
            sales = min(self.state.produced, demand)
            revenue = sales * self.state.price
            self.state.money += revenue
            self.state.message = f"Vendiste {sales} limonadas a ${self.state.price:.2f} (Ingresos ${revenue:.2f})."

        self.state.produced = 0
        self.state.day += 1
        if self.state.day <= self.state.total_days:
            self.generate_weather()
        else:
            self.state.running = False
            self.state.message = f"Fin del juego. Capital final: ${self.state.money:.2f}"
        return self.state.to_dict()

    def get_state(self):
        return self.state.to_dict()

GAME = Game()
