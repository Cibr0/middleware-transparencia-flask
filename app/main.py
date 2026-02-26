from collections import Counter
from statistics import mean, median
import fetcher

from flask import Flask, jsonify, request, url_for
from models import Produto
from pydantic import ValidationError
import time

import os
import platform
from datetime import datetime, timedelta
import socket
from typing import List
from cache import cache
from fetcher import CIRCUIT_OPEN, failure_count 

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
        "dependencies": {
            "cache": cache.stats(),
            "circuit_breaker": {
                "open": fetcher.CIRCUIT_OPEN,
                "failure_count": fetcher.failure_count
            },
            "last_fetch": {
                "timestamp": fetcher.LAST_FETCH_TIMESTAMP,
                "status_code": fetcher.LAST_FETCH_STATUS,
                "fallback_used": fetcher.LAST_FETCH_FALLBACK
            }
        }
    })

@app.route("/data/summary")
def produtos_summary():
    produtos, status_code, is_fallback = fetcher.fetch_produtos(simular_erro=False)
    return processar_produtos(produtos, status_code, is_fallback)


@app.route("/data/summary-test")
def produtos_summary_test():
    produtos, status_code, is_fallback = fetcher.fetch_produtos(simular_erro=True)
    return processar_produtos(produtos, status_code, is_fallback)

@app.route("/data/products", methods=["GET"])
def list_products():

    errors = []

    page_str = request.args.get("page", "1")
    try:
        page = int(page_str)
        if page < 1:
            errors.append("page deve ser ≥ 1")
    except ValueError:
        errors.append(f"page inválido: '{page_str}' (deve ser um número inteiro)")

    limit_str = request.args.get("limit", "20")
    try:
        limit = int(limit_str)
        if limit < 1:
            errors.append("limit deve ser ≥ 1")
        if limit > 100:
            errors.append("limit máximo permitido é 100")
    except ValueError:
        errors.append(f"limit inválido: '{limit_str}' (deve ser um número inteiro)")

    categoria_param = request.args.get("category")

    simular_erro_str = request.args.get("simular_erro", "false").lower()
    simular_erro = simular_erro_str in ("true", "1", "yes", "sim")

    if errors:
        return jsonify({
            "status": "error",
            "message": "Parâmetros inválidos",
            "details": errors
        }), 400

    try:
        produtos_raw, status_code, is_fallback = fetcher.fetch_produtos(simular_erro=simular_erro)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Não foi possível obter os dados da fonte: {str(e)}"
        }), 503

    if produtos_raw is None:
        return jsonify({
            "status": "error",
            "message": "Serviço indisponível",
            "meta": {
                "resilience": {
                    "fallback_ativado": is_fallback
                }
            }
        }), status_code

    validos: List[Produto] = []
    integridade = {
        "erros_por_campo": {},
        "tipos_erros_detectados": set(),
        "source_url": "https://dummyjson.com/products",
        "acoes_tomadas": {"aceitos": 0, "descartados": 0}
    }

    for item in produtos_raw:
        try:
            prod = Produto(**item)
            validos.append(prod)
            integridade["acoes_tomadas"]["aceitos"] += 1
        except ValidationError as e:
            integridade["acoes_tomadas"]["descartados"] += 1
            for erro in e.errors():
                campo = erro["loc"][0] if erro["loc"] else "desconhecido"
                tipo_erro = erro["type"]
                integridade["tipos_erros_detectados"].add(tipo_erro)

                if campo not in integridade["erros_por_campo"]:
                    integridade["erros_por_campo"][campo] = {
                        "quantidade": 0,
                        "exemplos": []
                    }
                integridade["erros_por_campo"][campo]["quantidade"] += 1
                if len(integridade["erros_por_campo"][campo]["exemplos"]) < 3:
                    integridade["erros_por_campo"][campo]["exemplos"].append(str(item.get(campo, "ausente")))

    integridade["tipos_erros_detectados"] = list(integridade["tipos_erros_detectados"])

    produtos_filtrados = validos

    if categoria_param:
        categorias_desejadas = [
            cat.strip().lower()
            for cat in categoria_param.split(",")
            if cat.strip()
        ]
        if categorias_desejadas:
            produtos_filtrados = [
                p for p in validos
                if p.category.lower() in categorias_desejadas
            ]

    total_itens_filtrados = len(produtos_filtrados)
    total_paginas = (total_itens_filtrados + limit - 1) // limit if limit > 0 else 1

    if page > total_paginas and total_paginas > 0:
        page = total_paginas

    start = (page - 1) * limit
    end = start + limit
    produtos_paginados = produtos_filtrados[start:end]

    produtos_json = [p.model_dump() for p in produtos_paginados]

    base_url = url_for("list_products", _external=True)
    links = {
        "self": f"{base_url}?page={page}&limit={limit}"
    }
    if categoria_param:
        links["self"] += f"&category={categoria_param}"

    if page > 1:
        links["prev"] = f"{base_url}?page={page-1}&limit={limit}"
        if categoria_param:
            links["prev"] += f"&category={categoria_param}"

    if page < total_paginas:
        links["next"] = f"{base_url}?page={page+1}&limit={limit}"
        if categoria_param:
            links["next"] += f"&category={categoria_param}"

    return jsonify({
        "status": "success",
        "data": {
            "produtos": produtos_json,
            "paginacao": {
                "pagina_atual": page,
                "itens_por_pagina": limit,
                "total_itens": total_itens_filtrados,
                "total_paginas": total_paginas,
                "links": links
            },
            "total_validos_antes_filtro": len(validos),
            "total_registros_originais": len(produtos_raw),
            "filtro_categoria_aplicado": categoria_param or "nenhum (todos)",
            "categorias_encontradas": list(sorted(set(p.category for p in produtos_filtrados)))
        },
        "meta": {
            "integrity_report": integridade,
            "fonte": "https://dummyjson.com/products",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    })
        

if __name__ == "__main__":
    app.run(debug=True)