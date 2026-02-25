from collections import Counter
from statistics import mean, median

from flask import Flask, jsonify
from fetcher import fetch_produtos
from models import Produto
from pydantic import ValidationError
import time

import os
import platform
from datetime import datetime, timedelta
import socket

app = Flask(__name__)
start_time = time.time()
request_count = 0

def processar_produtos(produtos, status_code, is_fallback):
    if produtos is None:
        return jsonify({
            "error": "Serviço indisponível",
            "meta": {
                "resilience": {
                    "fallback_ativado": is_fallback
                }
            }
        }), status_code

    integridade = {
        "erros_por_campo": {},
        "lista_erros_detectados": set(),
        "source_url": "https://dummyjson.com/products",
        "acoes_tomadas": {
            "aceitos": 0,
            "descartados": 0
        }
    }

    validos = []

    for item in produtos:
        try:
            produto_validado = Produto(**item)
            validos.append(produto_validado)
            integridade["acoes_tomadas"]["aceitos"] += 1
        except ValidationError as e:
            integridade["acoes_tomadas"]["descartados"] += 1

            for erro in e.errors():
                campo = erro["loc"][0]
                tipo = erro["type"]
                valor = item.get(campo, "ausente")

                if campo not in integridade["erros_por_campo"]:
                    integridade["erros_por_campo"][campo] = {
                        "quantidade": 0,
                        "exemplos": []
                    }

                integridade["erros_por_campo"][campo]["quantidade"] += 1
                integridade["erros_por_campo"][campo]["exemplos"].append(str(valor))
                integridade["lista_erros_detectados"].add(tipo)

    integridade["lista_erros_detectados"] = list(integridade["lista_erros_detectados"])

    precos = [p.price for p in validos]
    media_preco = mean(precos) if precos else 0
    mediana_preco = median(precos) if precos else 0

    categorias = [p.category for p in validos]
    contagem_por_categoria = dict(Counter(categorias))

    response = {
        "data": {
            "total_registros": len(produtos),
            "validos": len(validos),
            "invalidos": integridade["acoes_tomadas"]["descartados"],
            "media_preco": media_preco,
            "mediana_preco": mediana_preco,
            "contagem_por_categoria": contagem_por_categoria
        },
        "meta": {
            "integrity_report": integridade,
            "resilience": {
                "fallback_ativado": is_fallback
            }
        }
    }

    return jsonify(response), status_code

@app.before_request
def before_request():
    global request_count
    request_count += 1

@app.route("/status")
def status():
    global request_count
    current_time = time.time()
    uptime = current_time - start_time
    
    # Formatar uptime
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv('FLASK_ENV', 'development'),
        
        "api": {
            "name": "Client_Middleware",
            "version": "1.0.0",
            "uptime": f"{hours}h {minutes}m {seconds}s",
            "uptime_seconds": uptime,
            "started_at": datetime.fromtimestamp(start_time).isoformat(),
            "total_requests": request_count
        },
        
        "system": {
            "hostname": socket.gethostname(),
            "python_version": platform.python_version(),
            "platform": platform.platform()
        },
    })

@app.route("/data/summary")
def produtos_summary():
    produtos, status_code, is_fallback = fetch_produtos(simular_erro=False)
    return processar_produtos(produtos, status_code, is_fallback)


@app.route("/data/summary-test")
def produtos_summary_test():
    produtos, status_code, is_fallback = fetch_produtos(simular_erro=True)
    return processar_produtos(produtos, status_code, is_fallback)

if __name__ == "__main__":
    app.run(debug=True)