from flask import Flask, jsonify
from fetcher import fetch_produtos
from models import Produto
from pydantic import ValidationError

app = Flask(__name__)

@app.route("/status")
def status():
    return jsonify({"status": "ok"})

@app.route("/data/summary")
def produtos_summary():
    produtos = fetch_produtos(simular_erro=True)

    integridade = {
        "erros_por_campo": {},
        "tipos_de_erro": {},
        "acoes_tomadas": {
            "aceitos": 0,
            "descartados": 0
        }
    }

    validos = []
    invalidos = 0

    for item in produtos:
        try:
            Produto(**item)
            integridade["acoes_tomadas"]["aceitos"] += 1
        except ValidationError as e:
            integridade["acoes_tomadas"]["descartados"] += 1

            for erro in e.errors():
                campo = erro["loc"][0]
                tipo = erro["type"]

                integridade["erros_por_campo"][campo] = (
                    integridade["erros_por_campo"].get(campo, 0) + 1
                )

                integridade["tipos_de_erro"][tipo] = (
                    integridade["tipos_de_erro"].get(tipo, 0) + 1
                )

    return jsonify({
        "total_produtos": len(produtos),
        "integridade": integridade
    })

if __name__ == "__main__":
    app.run(debug=True)