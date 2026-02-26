# 📦 Middleware de Transparência -- Flask

Middleware em Flask responsável por consumir uma API externa, validar
dados, gerar métricas agregadas e implementar mecanismos de
**resiliência**, incluindo:

-   Cache em memória com TTL\
-   Retry com backoff exponencial\
-   Fallback automático\
-   Circuit Breaker\
-   Monitoramento básico de integridade\
-   Endpoint de status

------------------------------------------------------------------------

# 🚀 Tecnologias Utilizadas

-   Python 3.10+
-   Flask
-   Requests
-   Pydantic
-   Cache em memória customizado (TTL)
-   Estratégias de resiliência implementadas manualmente

------------------------------------------------------------------------

# 📁 Estrutura do Projeto

app/ ├── main.py\
├── fetcher.py\
├── cache.py\
├── models.py\
└── requirements.txt

------------------------------------------------------------------------

# ⚙️ Como Rodar o Projeto

## 1️⃣ Criar ambiente virtual

python -m venv venv

Ativar:

Windows: venv`\Scripts`{=tex}`\activate`{=tex}

Linux/Mac: source venv/bin/activate

------------------------------------------------------------------------

## 2️⃣ Instalar dependências

pip install -r requirements.txt

Se não existir:

pip install flask requests pydantic

------------------------------------------------------------------------

## 3️⃣ Rodar o servidor

Dentro da pasta app:

py main.py

Servidor disponível em: http://127.0.0.1:5000

------------------------------------------------------------------------

# 🔎 Endpoints Disponíveis

## GET /status

Retorna informações de saúde da aplicação.

## GET /data/summary

Fluxo normal com cache, retry, fallback e circuit breaker.

## GET /data/summary-test

Simula erros para testar validação e integrity report.

------------------------------------------------------------------------

# 🛡 Estratégias de Resiliência

## Timeout explícito

timeout=5

## Retry com Backoff Exponencial

Tentativas limitadas com espera progressiva.

## Cache TTL

Armazena respostas válidas com expiração configurável.

## Fallback

Retorna última resposta válida do cache se a API falhar.

## Circuit Breaker

Interrompe chamadas externas após falhas consecutivas.

------------------------------------------------------------------------

# 🧪 Como Testar no Insomnia

1.  GET http://127.0.0.1:5000/data/summary
2.  Repetir requisição para validar cache.
3.  Quebrar URL externa para testar fallback.
4.  Reiniciar servidor com URL inválida para testar 503.
5.  Fazer múltiplas chamadas para testar circuit breaker.

------------------------------------------------------------------------

# 📊 Checklist de Resiliência

-   Timeout explícito ✔
-   Retry com backoff ✔
-   Cache TTL ✔
-   Fallback ✔
-   Circuit Breaker ✔
-   Endpoint de status ✔

------------------------------------------------------------------------

# 🏁 Conclusão

Este projeto demonstra boas práticas de resiliência em APIs, incluindo
proteção contra falhas externas, redução de chamadas em picos e
monitoramento básico de integridade.
