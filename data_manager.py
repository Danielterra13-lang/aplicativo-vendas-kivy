"""
Camada de dados do Aplicativo de Vendas.

Fonte da verdade: Firebase Realtime Database (REST API, sem SDK).
dados.json continua existindo como cache local -- garante que o app
funciona mesmo sem internet e evita perda de dados se o Firebase estiver
fora do ar. A cada leitura tentamos o Firebase primeiro; a cada escrita,
gravamos local e espelhamos para o Firebase.

Isso pressupõe regras públicas (".read"/".write": true), como configurado
agora. Quando for hora de restringir as regras, o próximo passo é acrescentar
autenticação (Firebase Auth) e mandar o idToken em cada requisição -- a
interface pública desta classe (DataStore) foi pensada para não precisar
mudar nas telas quando isso acontecer.
"""

import json
import os
from datetime import datetime

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(BASE_DIR, "dados.json")

# URL base do Realtime Database (sem barra no final e sem ".json").
# Ajuste aqui se trocar de projeto/banco no Firebase.
FIREBASE_URL = "https://tough-country-457016-i0-default-rtdb.firebaseio.com"
FIREBASE_TIMEOUT = 5  # segundos

# Catálogo fixo de clientes (redes), ligado aos ícones existentes em
# icones/fotos_clientes/
CLIENTES = [
    {"id": "carrefour", "nome": "Carrefour", "foto": "icones/fotos_clientes/carrefour.png"},
    {"id": "dia", "nome": "Dia", "foto": "icones/fotos_clientes/dia.png"},
    {"id": "guanabara", "nome": "Guanabara", "foto": "icones/fotos_clientes/guanabara.png"},
    {"id": "mundial", "nome": "Mundial", "foto": "icones/fotos_clientes/mundial.png"},
    {"id": "paodeacucar", "nome": "Pão de Açúcar", "foto": "icones/fotos_clientes/paodeacucar.png"},
    {"id": "prezunic", "nome": "Prezunic", "foto": "icones/fotos_clientes/prezunic.png"},
]

# Catálogo fixo de produtos, ligado aos ícones em icones/fotos_produtos/
# Preços são placeholders -- ajuste livremente aqui, é a única fonte da verdade.
PRODUTOS = [
    {"id": "arroz", "nome": "Arroz 5kg", "preco": 24.90, "foto": "icones/fotos_produtos/arroz.png"},
    {"id": "azeite", "nome": "Azeite 500ml", "preco": 18.50, "foto": "icones/fotos_produtos/azeite.png"},
    {"id": "carne", "nome": "Carne Bovina (kg)", "preco": 42.00, "foto": "icones/fotos_produtos/carne.png"},
    {"id": "feijao", "nome": "Feijão 1kg", "preco": 8.90, "foto": "icones/fotos_produtos/feijao.png"},
    {"id": "frango", "nome": "Frango (kg)", "preco": 12.50, "foto": "icones/fotos_produtos/frango.png"},
    {"id": "macarrao", "nome": "Macarrão 500g", "preco": 4.50, "foto": "icones/fotos_produtos/macarrao.png"},
    {"id": "queijo", "nome": "Queijo (kg)", "preco": 39.90, "foto": "icones/fotos_produtos/queijo.png"},
]

# Fotos de perfil disponíveis para o vendedor escolher ao se cadastrar.
FOTOS_PERFIL = [f"icones/fotos_perfil/foto{i}.png" for i in range(1, 18)]


def _cliente_por_id(cliente_id):
    for c in CLIENTES:
        if c["id"] == cliente_id:
            return c
    return None


def _produto_por_id(produto_id):
    for p in PRODUTOS:
        if p["id"] == produto_id:
            return p
    return None


def _normalizar_colecao(bruto):
    """O Firebase Realtime Database devolve um nó como dict quando as
    chaves não são só números sequenciais (ex: {"1": {...}, "2": {...}}),
    mas quando são, ele "decide" que é um array e devolve uma lista com
    null nos índices que não existem (ex: nosso id 1 vira o índice 1, e o
    índice 0 -- que nunca usamos -- some como null). Essa função aceita
    os dois formatos e sempre devolve uma lista limpa, ordenada por id."""
    if not bruto:
        return []
    itens = list(bruto.values()) if isinstance(bruto, dict) else list(bruto)
    itens = [item for item in itens if item]
    itens.sort(key=lambda item: item.get("id", 0))
    return itens


class DataStore:
    """Carrega e salva vendedores/vendas no Firebase Realtime Database,
    com dados.json como cache local, e expõe consultas já prontas (KPIs)
    para as telas de relatório."""

    def __init__(self, arquivo=ARQUIVO_DADOS, firebase_url=FIREBASE_URL):
        self.arquivo = arquivo
        self.firebase_url = firebase_url.rstrip("/") if firebase_url else None
        self.online = True  # atualizado a cada tentativa de acesso ao Firebase
        self._dados = {"vendedores": [], "vendas": []}
        self.carregar()

    # ---------- Firebase (REST, sem SDK) ----------

    def _firebase_get(self):
        if not self.firebase_url:
            return None
        try:
            resp = requests.get(f"{self.firebase_url}/.json", timeout=FIREBASE_TIMEOUT)
            resp.raise_for_status()
            self.online = True
            return resp.json()
        except Exception as erro:
            self.online = False
            print(f"[Firebase] não foi possível ler o banco ({erro}). Usando cache local.")
            return None

    def _firebase_put(self):
        if not self.firebase_url:
            return
        # Realtime Database trabalha melhor com objetos (dict) do que com
        # listas/arrays -- por isso convertemos id -> registro antes de enviar.
        payload = {
            "vendedores": {str(v["id"]): v for v in self._dados["vendedores"]},
            "vendas": {str(v["id"]): v for v in self._dados["vendas"]},
        }
        try:
            resp = requests.put(f"{self.firebase_url}/.json", json=payload, timeout=FIREBASE_TIMEOUT)
            resp.raise_for_status()
            self.online = True
        except Exception as erro:
            self.online = False
            print(f"[Firebase] não foi possível gravar no banco ({erro}). Dados salvos só localmente por enquanto.")

    # ---------- persistência ----------

    def carregar(self):
        remoto = self._firebase_get()
        if remoto:
            self._dados = {
                "vendedores": _normalizar_colecao(remoto.get("vendedores")),
                "vendas": _normalizar_colecao(remoto.get("vendas")),
            }
            self._salvar_local()
            return

        # Firebase indisponível (ou banco vazio) -> usa o cache local
        if os.path.exists(self.arquivo):
            with open(self.arquivo, "r", encoding="utf-8") as f:
                self._dados = json.load(f)
        else:
            self._dados = {"vendedores": [], "vendas": []}
            self._salvar_local()

    def salvar(self):
        self._salvar_local()
        self._firebase_put()

    def _salvar_local(self):
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(self._dados, f, ensure_ascii=False, indent=2)

    # ---------- vendedores ----------

    def listar_vendedores(self):
        return list(self._dados["vendedores"])

    def adicionar_vendedor(self, nome, foto):
        novo_id = (max([v["id"] for v in self._dados["vendedores"]], default=0)) + 1
        vendedor = {"id": novo_id, "nome": nome.strip(), "foto": foto}
        self._dados["vendedores"].append(vendedor)
        self.salvar()
        return vendedor

    def vendedor_por_id(self, vendedor_id):
        for v in self._dados["vendedores"]:
            if v["id"] == vendedor_id:
                return v
        return None

    def excluir_vendedor(self, vendedor_id):
        """Remove o vendedor do cadastro. As vendas dele são mantidas no
        histórico (kpis_gerais trata vendedor ausente como "vendedor
        removido"), só o vínculo de quem é o "dono" do perfil some."""
        antes = len(self._dados["vendedores"])
        self._dados["vendedores"] = [v for v in self._dados["vendedores"] if v["id"] != vendedor_id]
        removeu = len(self._dados["vendedores"]) != antes
        if removeu:
            self.salvar()
        return removeu

    # ---------- vendas ----------

    def registrar_venda(self, vendedor_id, cliente_id, itens):
        """itens: lista de dicts {"produto_id": str, "qtd": int}"""
        itens_completos = []
        total = 0.0
        for item in itens:
            produto = _produto_por_id(item["produto_id"])
            if not produto or item["qtd"] <= 0:
                continue
            subtotal = produto["preco"] * item["qtd"]
            total += subtotal
            itens_completos.append({
                "produto_id": produto["id"],
                "nome": produto["nome"],
                "qtd": item["qtd"],
                "preco_unit": produto["preco"],
                "subtotal": subtotal,
            })

        if not itens_completos:
            return None

        novo_id = (max([v["id"] for v in self._dados["vendas"]], default=0)) + 1
        venda = {
            "id": novo_id,
            "vendedor_id": vendedor_id,
            "cliente_id": cliente_id,
            "itens": itens_completos,
            "total": round(total, 2),
            "data": datetime.now().isoformat(timespec="seconds"),
        }
        self._dados["vendas"].append(venda)
        self.salvar()
        return venda

    def listar_vendas(self, vendedor_id=None):
        vendas = self._dados["vendas"]
        if vendedor_id is not None:
            vendas = [v for v in vendas if v["vendedor_id"] == vendedor_id]
        return sorted(vendas, key=lambda v: v["data"], reverse=True)

    def excluir_venda(self, venda_id):
        """Remove uma venda específica (ex: cadastro feito errado)."""
        antes = len(self._dados["vendas"])
        self._dados["vendas"] = [v for v in self._dados["vendas"] if v["id"] != venda_id]
        removeu = len(self._dados["vendas"]) != antes
        if removeu:
            self.salvar()
        return removeu

    def limpar_vendas(self):
        self._dados["vendas"] = []
        self.salvar()

    # ---------- filtros de período (usados no relatório) ----------

    def dias_disponiveis(self):
        """Lista de datas (YYYY-MM-DD) que têm pelo menos uma venda, mais recente primeiro."""
        return sorted({v["data"][:10] for v in self._dados["vendas"]}, reverse=True)

    def meses_disponiveis(self):
        """Lista de meses (YYYY-MM) que têm pelo menos uma venda, mais recente primeiro."""
        return sorted({v["data"][:7] for v in self._dados["vendas"]}, reverse=True)

    def vendas_filtradas(self, dias=None, meses=None):
        """Filtra vendas pelos dias/meses marcados (checkboxes, multi-seleção).
        Uma venda entra se o dia dela estiver marcado OU o mês dela estiver
        marcado (união dos dois filtros). Sem nenhuma marcação -> tudo passa."""
        dias = set(dias or [])
        meses = set(meses or [])
        vendas = self._dados["vendas"]
        if not dias and not meses:
            return sorted(vendas, key=lambda v: v["data"], reverse=True)
        selecionadas = [v for v in vendas if v["data"][:10] in dias or v["data"][:7] in meses]
        return sorted(selecionadas, key=lambda v: v["data"], reverse=True)

    # ---------- KPIs (relatório "Vendas da Empresa") ----------

    def kpis_gerais(self, dias=None, meses=None):
        vendas = self.vendas_filtradas(dias, meses)
        total_faturado = sum(v["total"] for v in vendas)
        qtd_vendas = len(vendas)
        ticket_medio = (total_faturado / qtd_vendas) if qtd_vendas else 0.0

        por_cliente = {}
        por_produto = {}
        por_vendedor = {}

        for v in vendas:
            cliente = _cliente_por_id(v["cliente_id"])
            nome_cliente = cliente["nome"] if cliente else v["cliente_id"]
            por_cliente[nome_cliente] = por_cliente.get(nome_cliente, 0.0) + v["total"]

            vendedor = self.vendedor_por_id(v["vendedor_id"])
            nome_vendedor = vendedor["nome"] if vendedor else "—"
            por_vendedor[nome_vendedor] = por_vendedor.get(nome_vendedor, 0.0) + v["total"]

            for item in v["itens"]:
                por_produto[item["nome"]] = por_produto.get(item["nome"], 0.0) + item["subtotal"]

        top_cliente = max(por_cliente.items(), key=lambda x: x[1]) if por_cliente else None
        top_produto = max(por_produto.items(), key=lambda x: x[1]) if por_produto else None
        top_vendedor = max(por_vendedor.items(), key=lambda x: x[1]) if por_vendedor else None

        return {
            "total_faturado": round(total_faturado, 2),
            "qtd_vendas": qtd_vendas,
            "ticket_medio": round(ticket_medio, 2),
            "top_cliente": top_cliente,
            "top_produto": top_produto,
            "top_vendedor": top_vendedor,
            "por_vendedor": sorted(por_vendedor.items(), key=lambda x: x[1], reverse=True),
        }
