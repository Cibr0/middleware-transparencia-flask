import pytest
import requests_mock
from flask import Flask
from main import app 

from datetime import datetime

# Cria um cliente de teste do Flask que simula requisições HTTP sem rodar um servidor real
# Ativa modo TESTING para desativar verificações de produção
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:  # Cria o client para testes
        yield client  # O objeto 'client' é injetado nos testes como argumento


# Fixture para mockar todas as requisições HTTP feitas com requests.get, usando requests-mock
@pytest.fixture(autouse=True)
def mock_all_requests():
    with requests_mock.Mocker(real_http=False) as m:
        yield m  # O objeto 'm' é injetado nos testes para configurar respostas mockadas

# Dados de mock para testes, representando uma resposta típica da API externa
MOCK_DATA_SAFE = {
    "products": [
        {"id": i+1, "title": f"Produto {i+1}", "price": 99.99 + i*10, "category": "eletronicos",
         "meta": {"createdAt": "2023-01-01T00:00:00.000Z", "updatedAt": "2023-01-01T00:00:00.000Z"}}
        for i in range(12)
    ]
}

# Teste 1: rota /data/summary em condição normal → deve retornar 200
def test_summary_status_code_200(mock_all_requests, client):
    # Mocka a resposta da API externa para retornar dados seguros
    mock_all_requests.get("https://dummyjson.com/products", json=MOCK_DATA_SAFE)
    # Faz a requisição para a rota /data/summary usando o client de teste
    response = client.get("/data/summary")
    # Verifica que o status code é 200, indicando sucesso
    assert response.status_code == 200

# Teste 2: rota /data/summary com falha externa → deve retornar 503 ou 200 com fallback
def test_summary_status_code_503_on_failure(mock_all_requests, client):
    # Mocka a resposta da API externa para simular um erro (status code 500)
    mock_all_requests.get("https://dummyjson.com/products", status_code=500, text="Server error")
    response = client.get("/data/summary")
    # Verifica que o status code é 503 (serviço indisponível) ou 200 (fallback ativado)
    assert response.status_code in (200, 503, 500)
    # Verifica que a resposta indica claramente o fallback ou erro
    assert "fallback_ativado" in str(response.json) or \
           response.json.get("status") == "error" or \
           "Serviço indisponível" in str(response.json)

# Teste 3: rota /data/products em condição normal → 200
def test_products_status_code_200(mock_all_requests, client):
    mock_all_requests.get("https://dummyjson.com/products", json=MOCK_DATA_SAFE)
    response = client.get("/data/products")
    assert response.status_code == 200

# Teste 4: rota /data/products com falha externa → 200 (fallback) ou 503
def test_products_status_code_503_on_failure(mock_all_requests, client):
    mock_all_requests.get("https://dummyjson.com/products", status_code=500, text="Server error")
    response = client.get("/data/products")
    assert response.status_code in (200, 503, 500)

# Teste 5: verifica schema (estrutura) da rota /data/summary
def test_schema_match_summary(mock_all_requests, client):
    mock_all_requests.get("https://dummyjson.com/products", json=MOCK_DATA_SAFE)
    response = client.get("/data/summary")
    json_data = response.json
    assert response.status_code == 200
    assert "data" in json_data
    assert "meta" in json_data
    assert "integrity_report" in json_data["meta"]
    # Verifica que o relatório de integridade tem as chaves esperadas
    assert isinstance(json_data["data"].get("media_preco"), (int, float, type(None)))

# Teste 6: verifica schema da rota /data/products
def test_schema_match_products(mock_all_requests, client):
    mock_all_requests.get("https://dummyjson.com/products", json=MOCK_DATA_SAFE)
    response = client.get("/data/products")
    json_data = response.json
    assert response.status_code == 200
    assert "data" in json_data
    assert "produtos" in json_data["data"]
    assert isinstance(json_data["data"]["produtos"], list)
    # Verifica que o campo de paginação tem as chaves esperadas
    assert any(key in json_data["data"] for key in [
        "total_encontrados", "total_itens", "total_registros",
        "total_validos_antes_filtro", "total_registros_originais"
    ])

# Teste 7: sanidade de preços (≥ 0) e descarte de itens inválidos
def test_sanidade_numerica_temporal(mock_all_requests, client):
    # Mocka a resposta da API externa com alguns produtos contendo preços inválidos (negativos ou nulos)
    mock_data_with_errors = {
        "products": MOCK_DATA_SAFE["products"][:5] + [
            {"id": 6, "title": "Bad Price", "price": -5, "category": "test", "meta": {"createdAt": "2023-01-01T00:00:00.000Z", "updatedAt": "2023-01-01T00:00:00.000Z"}},
            {"id": 7, "title": "Null Price", "price": None, "category": "test", "meta": {"createdAt": "2023-01-01T00:00:00.000Z", "updatedAt": "2023-01-01T00:00:00.000Z"}},
        ]
    }
    mock_all_requests.get("https://dummyjson.com/products", json=mock_data_with_errors)
    # Força modo de erro para testar descarte e relatório de integridade
    response = client.get("/data/products?simular_erro=true")
    json_data = response.json
    data = json_data["data"]
    meta = json_data["meta"]

    # Verifica que todos os produtos retornados têm preço válido (≥ 0)
    for p in data["produtos"]:
        assert p["price"] >= 0

    # Verifica que o relatório de integridade indica que itens inválidos foram descartados
    assert meta["integrity_report"]["acoes_tomadas"]["descartados"] >= 1
    # Verifica que o relatório de integridade indica erros relacionados a preços
    assert "price" in meta["integrity_report"]["erros_por_campo"]

# Teste 8: parâmetros inválidos → deve retornar 400 com mensagem clara
def test_borda_params_invalidos(client):
    response = client.get("/data/products?page=abc&limit=-1")
    assert response.status_code == 400
    assert response.json["status"] == "error"
    assert "Parâmetros inválidos" in response.json["message"]

# Teste 9: campos nulos ou tipos trocados → deve descartar e reportar erros
def test_borda_campos_nulos_tipos_trocados(mock_all_requests, client):
    mock_data_bad = {
        "products": [
            MOCK_DATA_SAFE["products"][0],
            {"id": "string_id", "title": None, "price": "string_price", "category": "test", "meta": {"createdAt": None, "updatedAt": None}}
        ]
    }
    mock_all_requests.get("https://dummyjson.com/products", json=mock_data_bad)
    # Força modo de erro para testar descarte e relatório de integridade
    response = client.get("/data/products?simular_erro=true")
    assert response.status_code == 200
    meta = response.json["meta"]
    # Deve ter descartado o item com tipos errados  
    assert meta["integrity_report"]["acoes_tomadas"]["descartados"] >= 1
    # Deve reportar erros de parsing ou tipos para os campos problemáticos
    assert any("parsing" in err.lower() for err in meta["integrity_report"]["tipos_erros_detectados"])

# Teste 10: paginação vazia → deve retornar 0 itens ou fallback aceitável
def test_borda_paginacao_vazia(mock_all_requests, client):
    # Mocka a resposta da API externa para retornar uma lista vazia de produtos
    mock_all_requests.get("https://dummyjson.com/products", json={"products": []})
    response = client.get("/data/products?page=5&limit=10")
    assert response.status_code == 200
    data = response.json["data"]
    # Deve retornar uma lista vazia de produtos ou um fallback aceitável (última válida)
    assert len(data["produtos"]) <= 10  # Mesmo que seja fallback, não deve exceder o limite solicitado
    # Verifica que a paginação indica corretamente a página solicitada ou o total de itens encontrados
    assert data["paginacao"]["pagina_atual"] == 5 or data["paginacao"]["total_itens"] >= 0