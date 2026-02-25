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
    produtos = fetch_produtos(simular_erro=True)

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
    invalidos = 0

    for item in produtos:
        try:
            # Guardando o produto validado no array validos
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

    # Cálculo de média e mediana dos preços dos produtos válidos
    #Media - Soma tudo e divide pela quantidade.
    #Mediana - Ordena e pega o valor do meio.
    precos = [p.price for p in validos]
    if precos:
        media_preco = mean(precos)
        mediana_preco = median(precos)
    else:
        media_preco = 0
        mediana_preco = 0

    # Contagem de produtos por categoria
    categorias = [p.category for p in validos]
    contagem_por_categoria = dict(Counter(categorias))

    #JSON padronizado com o campo meta.integrity_report
    return jsonify({
    "data": {
        "total_registros": len(produtos),
        "validos": len(validos),
        "invalidos": integridade["acoes_tomadas"]["descartados"],
        "media_preco": media_preco,
        "mediana_preco": mediana_preco,
        "contagem_por_categoria": contagem_por_categoria
    },
    "meta": {
        "integrity_report": integridade
    }
})

if __name__ == "__main__":
    app.run(debug=True)