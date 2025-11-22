# file: app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from game import GAME

app = Flask(__name__)
CORS(app)

@app.route("/health")
def health():
    return jsonify({"ok": True, "msg": "alive"})

@app.route("/state", methods=["GET"])
def state():
    return jsonify(GAME.get_state())

@app.route("/reset", methods=["POST"])
def reset():
    return jsonify(GAME.reset())

@app.route("/buy", methods=["POST"])
def buy():
    data = request.get_json() or {}
    lemons = data.get("lemons", 0)
    sugar = data.get("sugar", 0)
    cups = data.get("cups", 0)
    ok = GAME.buy(lemons, sugar, cups)
    return jsonify({"ok": ok, "state": GAME.get_state()})

@app.route("/set_price", methods=["POST"])
def set_price():
    data = request.get_json() or {}
    price = data.get("price", GAME.get_state().get("price", 1.0))
    ok = GAME.set_price(price)
    return jsonify({"ok": ok, "state": GAME.get_state()})

@app.route("/produce", methods=["POST"])
def produce():
    data = request.get_json() or {}
    qty = data.get("qty", 0)
    ok = GAME.produce(qty)
    return jsonify({"ok": ok, "state": GAME.get_state()})

@app.route("/simulate", methods=["POST"])
def simulate():
    state = GAME.simulate_day()
    return jsonify({"ok": True, "state": state})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
