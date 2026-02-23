import requests

def fetch_produtos(simular_erro=False):
    url = "https://dummyjson.com/products"
    response = requests.get(url, timeout=5)
    response.raise_for_status()  # erro se a API falhar
    
    data = response.json()
    produtos = data["products"]

    if simular_erro:
        produtos[0]["price"] = -1
        produtos[3]["price"] = None
        produtos[10]["price"] = -100
        produtos[1].pop("title", None)
        produtos[2]["price"] = "caro"

    return produtos
