import random
import math
import pandas as pd
import requests
from faker import Faker
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from time import sleep

# === CONFIGURAÇÕES ===
LAT_INICIAL = -20.2235779
LON_INICIAL = -40.2640909
RAIO_KM = 5
QTD_ENDERECOS_VALIDOS = 100
DISTANCIA_RUA = 200  # metros
USE_NOMINATIM = True

# === INICIALIZA ===
fake = Faker('pt_BR')
geolocator = Nominatim(user_agent="validador_com_overpass")

UF_SIGLAS = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM",
    "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES",
    "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
    "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC",
    "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"
}

# === FUNÇÕES ===

def gerar_latlong_aleatorio(lat, lon, raio_km):
    raio_graus = raio_km / 111
    angulo = random.uniform(0, 2 * math.pi)
    distancia = random.uniform(0, raio_graus)
    delta_lat = distancia * math.cos(angulo)
    delta_lon = distancia * math.sin(angulo) / math.cos(math.radians(lat))
    return lat + delta_lat, lon + delta_lon

def coordenada_de_rua_proxima(lat, lon, raio_metros=DISTANCIA_RUA):
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    way["highway"](around:{raio_metros},{lat},{lon});
    out center;
    """
    try:
        response = requests.post(overpass_url, data={'data': query}, timeout=25)
        data = response.json()
        for element in data.get("elements", []):
            ponto = element.get("center")
            if ponto:
                return ponto["lat"], ponto["lon"]
    except Exception as e:
        print(f"Erro na Overpass: {e}")
        return None
    return None

def buscar_endereco(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True, timeout=10, addressdetails=True)
        if location and "address" in location.raw:
            addr = location.raw["address"]
            rua = addr.get("road", "")
            numero = addr.get("house_number", "")
            bairro = addr.get("suburb") or addr.get("neighbourhood") or addr.get("residential") or ""
            cidade = addr.get("city") or addr.get("town") or addr.get("village") or ""
            estado = addr.get("state", "")
            uf = UF_SIGLAS.get(estado, estado)
            cep = addr.get("postcode", "")
            pais = addr.get("country", "")

            return f"{rua}, {numero}, {bairro}, {cidade}, {uf}, {cep}, {pais}".strip().strip(',')
    except GeocoderTimedOut:
        sleep(1)
    return None

# === EXECUÇÃO ===

resultados = []
tentativas = 0

print("Gerando coordenadas ajustadas para vias com endereço formatado...")

while len(resultados) < QTD_ENDERECOS_VALIDOS:
    lat_orig, lon_orig = gerar_latlong_aleatorio(LAT_INICIAL, LON_INICIAL, RAIO_KM)
    tentativas += 1

    coordenada_rua = coordenada_de_rua_proxima(lat_orig, lon_orig)
    if not coordenada_rua:
        print(f"[tentativa {tentativas}] ❌ Nenhuma rua próxima de ({lat_orig:.5f}, {lon_orig:.5f})")
        continue

    lat, lon = coordenada_rua

    endereco = None
    if USE_NOMINATIM:
        endereco = buscar_endereco(lat, lon)
        sleep(1)

    nome = f"{fake.first_name()} {fake.last_name()}"
    print(f"[{len(resultados)+1}] ✅ {nome} — {endereco or 'Coordenada sobre via'}")

    resultados.append({
        "Número": len(resultados) + 1,
        "Nome": nome,
        "Latitude": lat,
        "Longitude": lon,
        "Endereço": endereco or "—"
    })

# === EXPORTAÇÃO ===

df = pd.DataFrame(resultados)
df = df[["Número", "Nome", "Latitude", "Longitude", "Endereço"]]

nome_arquivo = input("Digite o nome do arquivo (sem .xlsx): ").strip()
if not nome_arquivo:
    nome_arquivo = "enderecos_formatados"

df.to_excel(f"{nome_arquivo}.xlsx", index=False)
print(f"\n✔️ Arquivo '{nome_arquivo}.xlsx' salvo com sucesso após {tentativas} tentativas.")
