# 📦 Client Middleware API (versão completa)

API em **Flask** para validação e resumo de produtos com **Pydantic** e recursos de **resiliência**.

---

## 🔹 Modelos de Dados

### **Meta**

| Campo       | Tipo       | Descrição                   |
| ----------- | ---------- | --------------------------- |
| `createdAt` | `datetime` | Data de criação do registro |
| `updatedAt` | `datetime` | Data da última atualização  |

### **Produto**

| Campo      | Tipo    | Descrição              |
| ---------- | ------- | ---------------------- |
| `id`       | `int`   | Identificador único    |
| `title`    | `str`   | Nome do produto        |
| `price`    | `float` | Preço do produto (≥ 0) |
| `category` | `str`   | Categoria do produto   |
| `meta`     | `Meta`  | Metadata do registro   |

**Validação:** `price` ≥ 0. Produtos inválidos são descartados.

---

## 🔹 Endpoints

### **1. GET /status**

Retorna informações de saúde da API, uptime, ambiente e dependências.

**Exemplo de resposta:**

```json id="status-ex"
{
  "status": "healthy",
  "timestamp": "2026-02-26T18:00:00.123456",
  "environment": "development",
  "api": {
    "name": "Client_Middleware",
    "version": "1.0.0",
    "uptime": "0h 15m 30s",
    "uptime_seconds": 930,
    "started_at": "2026-02-26T17:45:00.123456",
    "total_requests": 15
  },
  "system": {
    "hostname": "MEU-PC",
    "python_version": "3.12.1",
    "platform": "Linux-6.5.0-100-generic-x86_64-with-glibc2.35"
  },
  "dependencies": {
    "cache": { "hits": 10, "misses": 3, "size": 5 },
    "circuit_breaker": {
      "open": false,
      "failure_count": 0
    },
    "last_fetch": {
      "timestamp": "2026-02-26T18:00:00",
      "status_code": 200,
      "fallback_used": false
    }
  }
}
```

---

### **2. GET /data/summary**

Resumo geral dos produtos válidos, estatísticas de preço e relatório de integridade.

**Parâmetros:** nenhum.

**Exemplo de resposta:**

```json id="summary-ex"
{
  "data": {
    "total_registros": 100,
    "validos": 95,
    "invalidos": 5,
    "media_preco": 199.5,
    "mediana_preco": 150.0,
    "contagem_por_categoria": {
      "electronics": 40,
      "furniture": 25,
      "clothing": 30
    }
  },
  "meta": {
    "integrity_report": {
      "erros_por_campo": {
        "price": {
          "quantidade": 3,
          "exemplos": [-10, -5, -1]
        }
      },
      "lista_erros_detectados": ["value_error.number.not_ge"],
      "acoes_tomadas": {
        "aceitos": 95,
        "descartados": 5
      },
      "source_url": "https://dummyjson.com/products"
    },
    "resilience": {
      "fallback_ativado": false
    }
  }
}
```

---

### **3. GET /data/summary-test**

Mesma função que `/data/summary`, mas **simula erros de dados** para teste do relatório de integridade.

**Parâmetros:** nenhum.

---

### **4. GET /data/products**

Lista produtos com **paginação**, **filtro por categoria** e opção de **simular erro**.

**Parâmetros de query:**

| Parâmetro      | Tipo | Obrigatório | Padrão | Descrição                                                                 |
| -------------- | ---- | ----------- | ------ | ------------------------------------------------------------------------- |
| `page`         | int  | opcional    | 1      | Página a ser retornada (≥ 1)                                              |
| `limit`        | int  | opcional    | 20     | Itens por página (1–100)                                                  |
| `category`     | str  | opcional    | todos  | Filtra produtos por categoria (pode ser múltiplas, separadas por vírgula) |
| `simular_erro` | bool | opcional    | false  | Simula erros de dados para teste                                          |

**Exemplo de URL:** `/data/products?page=2&limit=5&category=electronics,clothing&simular_erro=true`

**Exemplo de resposta:**

```json id="products-ex"
{
  "status": "success",
  "data": {
    "produtos": [
      {"id":1,"title":"Smartphone","price":1200.0,"category":"electronics","meta":{"createdAt":"2026-01-01T12:00:00","updatedAt":"2026-02-01T12:00:00"}},
      {"id":3,"title":"Camiseta","price":150.0,"category":"clothing","meta":{"createdAt":"2026-01-03T12:00:00","updatedAt":"2026-02-03T12:00:00"}}
    ],
    "paginacao": {
      "pagina_atual": 2,
      "itens_por_pagina": 5,
      "total_itens": 12,
      "total_paginas": 3,
      "links": {
        "self": "http://localhost/data/products?page=2&limit=5&category=electronics,clothing",
        "prev": "http://localhost/data/products?page=1&limit=5&category=electronics,clothing",
        "next": "http://localhost/data/products?page=3&limit=5&category=electronics,clothing"
      }
    },
    "total_validos_antes_filtro": 10,
    "total_registros_originais": 12,
    "filtro_categoria_aplicado": "electronics,clothing",
    "categorias_encontradas": ["clothing","electronics"]
  },
  "meta": {
    "integrity_report": {
      "erros_por_campo": {},
      "tipos_erros_detectados": [],
      "acoes_tomadas": {"aceitos":10,"descartados":0},
      "source_url": "https://dummyjson.com/products"
    },
    "fonte": "https://dummyjson.com/products",
    "timestamp": "2026-02-26T18:15:00Z"
  }
}
```

**Validações:**

* `page` e `limit` devem ser números inteiros válidos.
* `limit` máximo = 100.
* `category` filtra produtos válidos por categoria (case-insensitive).
* Se `simular_erro=true`, produtos inválidos serão incluídos para teste do relatório.

---

### 🔹 Observações gerais

* Produtos inválidos não são retornados no array final, mas aparecem no relatório de integridade.
* Estatísticas (`media_preco`, `mediana_preco`) consideram apenas produtos válidos.
* A API usa **resiliência**: fallback, circuit breaker e cache.
* Todos os endpoints retornam JSON padrão com `data` e `meta`.
* Paginação gera links `self`, `prev`, `next` automaticamente.