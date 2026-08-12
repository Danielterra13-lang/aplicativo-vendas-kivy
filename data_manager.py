"""
Camada de dados do Aplicativo de Vendas.

Fonte da verdade: Firebase Realtime Database (REST API, sem SDK), protegido
por autenticação (Firebase Auth, também via REST puro, sem SDK). dados.json
continua existindo como cache local -- garante que o app funciona mesmo sem
internet e evita perda de dados se o Firebase estiver fora do ar. A cada
leitura tentamos o Firebase primeiro (mandando o idToken da sessão atual);
a cada escrita, gravamos local e espelhamos para o Firebase.

Login: cada vendedor tem uma conta própria (email/senha) no Firebase Auth.
O id do vendedor no banco passa a ser o próprio uid do Firebase para quem se
cadastra por aqui (os vendedores antigos, criados antes do login existir,
mantêm o id numérico sequencial de antes e continuam aparecendo nos
relatórios, só não têm mais uma conta vinculada).
"""

import json
import os
from datetime import datetime

import certifi

# No Android empacotado (buildozer), o Python não acha o bundle de
# certificados raiz (CA) do sistema, então toda chamada HTTPS quebra com
# erro de verificação SSL. O certifi empacota esse bundle junto com o app;
# isso precisa vir ANTES do "import requests" pra já valer pra tudo que o
# requests fizer. É inofensivo no desktop -- só aponta pro bundle certo.
os.environ["SSL_CERT_FILE"] = certifi.where()

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(BASE_DIR, "dados.json")

# URL base do Realtime Database (sem barra no final e sem ".json").
# Ajuste aqui se trocar de projeto/banco no Firebase.
FIREBASE_URL = "https://tough-country-457016-i0-default-rtdb.firebaseio.com"
FIREBASE_TIMEOUT = 5  # segundos

# Web API Key do projeto Firebase (Configurações do projeto > Geral, ou
# Google Cloud Console > APIs e Serviços > Credenciais). Necessária só para
# as chamadas de autenticação (login/criar conta), não para o Realtime
# Database em si.
FIREBASE_API_KEY = "AIzaSyBf1ANZCkLQ3oa6epoiJYCGO76HNk0_NhM"

# Traduz os códigos de erro que o Firebase Auth devolve em texto técnico
# (em inglês) para mensagens que fazem sentido pra quem está usando o app.
MENSAGENS_ERRO_AUTH = {
    "EMAIL_EXISTS": "Já existe uma conta com esse email.",
    "EMAIL_NOT_FOUND": "Não existe conta com esse email.",
    "INVALID_PASSWORD": "Senha incorreta.",
    "INVALID_LOGIN_CREDENTIALS": "Email ou senha incorretos.",
    "USER_DISABLED": "Essa conta foi desativada.",
    "INVALID_EMAIL": "Email inválido.",
    "MISSING_PASSWORD": "Digite uma senha.",
    "MISSING_EMAIL": "Digite um email.",
}


def _mensagem_erro_auth(resp_json):
    codigo = resp_json.get("error", {}).get("message", "Erro desconhecido")
    if codigo.startswith("WEAK_PASSWORD"):
        return "A senha precisa ter pelo menos 6 caracteres."
    if codigo.startswith("TOO_MANY_ATTEMPTS"):
        return "Muitas tentativas seguidas. Espere um pouco e tente de novo."
    return MENSAGENS_ERRO_AUTH.get(codigo, codigo)

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
    # str() no key porque a partir da autenticação os ids passam a ser mistos
    # (inteiros dos vendedores antigos + uids em string dos que fizeram
    # login) -- sorted() não compara int com str diretamente.
    itens.sort(key=lambda item: str(item.get("id", 0)))
    return itens


class DataStore:
    """Carrega e salva vendedores/vendas no Firebase Realtime Database,
    com dados.json como cache local, e expõe consultas já prontas (KPIs)
    para as telas de relatório."""

    def __init__(self, arquivo=ARQUIVO_DADOS, firebase_url=FIREBASE_URL):
        self.arquivo = arquivo
        self.firebase_url = firebase_url.rstrip("/") if firebase_url else None
        self.online = True  # atualizado a cada tentativa de acesso ao Firebase
        self.id_token = None  # token da sessão atual (Firebase Auth), None = deslogado
        self.uid = None
        self._dados = {"vendedores": [], "vendas": []}
        # Sem login ainda não temos idToken, então isso só preenche o cache
        # local (dados.json) se as regras do banco exigirem auth -- assim que
        # o login acontecer, carregar() é chamado de novo já autenticado.
        self.carregar()

    # ---------- Firebase (REST, sem SDK) ----------

    def _firebase_get(self):
        if not self.firebase_url:
            return None
        try:
            params = {"auth": self.id_token} if self.id_token else {}
            resp = requests.get(f"{self.firebase_url}/.json", params=params, timeout=FIREBASE_TIMEOUT)
            resp.raise_for_status()
            self.online = True
            return resp.json()
        except Exception as erro:
            self.online = False
            print(f"[Firebase] não foi possível ler o banco ({erro}). Usando cache local.")
            return None

    def _firebase_put_registro(self, colecao, item):
        """Grava só ESSE registro (PUT em /colecao/id.json), sem tocar no
        resto da coleção.

        Importante: nunca fazemos mais um PUT no nó inteiro (/.json ou
        /vendedores.json) a partir dos dados em memória. Cada dispositivo
        (desktop, celular) só carrega pro cache local o que já viu, e como
        as leituras exigem estar autenticado, é fácil um dispositivo escrever
        antes de ter sincronizado tudo -- um PUT no nó inteiro nesse
        momento apagaria silenciosamente os registros que só existiam no
        Firebase e não tinham chegado ainda nesse dispositivo. Gravando
        registro por registro, essa perda de dados entre dispositivos não
        acontece."""
        if not self.firebase_url:
            return
        try:
            params = {"auth": self.id_token} if self.id_token else {}
            resp = requests.put(
                f"{self.firebase_url}/{colecao}/{item['id']}.json",
                json=item, params=params, timeout=FIREBASE_TIMEOUT,
            )
            resp.raise_for_status()
            self.online = True
        except Exception as erro:
            self.online = False
            print(f"[Firebase] não foi possível gravar no banco ({erro}). Dados salvos só localmente por enquanto.")

    def _firebase_delete_registro(self, colecao, item_id):
        if not self.firebase_url:
            return
        try:
            params = {"auth": self.id_token} if self.id_token else {}
            resp = requests.delete(
                f"{self.firebase_url}/{colecao}/{item_id}.json",
                params=params, timeout=FIREBASE_TIMEOUT,
            )
            resp.raise_for_status()
            self.online = True
        except Exception as erro:
            self.online = False
            print(f"[Firebase] não foi possível excluir no banco ({erro}).")

    def _firebase_delete_colecao(self, colecao):
        """Apaga a coleção inteira -- usado só em ações explícitas do tipo
        'limpar todas as vendas', onde apagar tudo é exatamente a intenção."""
        if not self.firebase_url:
            return
        try:
            params = {"auth": self.id_token} if self.id_token else {}
            resp = requests.delete(
                f"{self.firebase_url}/{colecao}.json",
                params=params, timeout=FIREBASE_TIMEOUT,
            )
            resp.raise_for_status()
            self.online = True
        except Exception as erro:
            self.online = False
            print(f"[Firebase] não foi possível limpar a coleção ({erro}).")

    # ---------- Autenticação (Firebase Auth REST) ----------

    def criar_conta(self, email, senha, nome, foto):
        """Cria a conta no Firebase Auth e, junto, o perfil do vendedor
        (usando o uid da conta como id do vendedor). Retorna (vendedor, None)
        em caso de sucesso, ou (None, mensagem_de_erro) em caso de falha."""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
        try:
            resp = requests.post(
                url,
                json={"email": email, "password": senha, "returnSecureToken": True},
                timeout=FIREBASE_TIMEOUT,
            )
            resp_json = resp.json()
        except Exception as erro:
            return None, f"Sem conexão com o Firebase ({erro})."

        if not resp.ok:
            return None, _mensagem_erro_auth(resp_json)

        self.id_token = resp_json["idToken"]
        self.uid = resp_json["localId"]

        vendedor = {"id": self.uid, "nome": nome.strip(), "foto": foto, "email": email}
        self._dados["vendedores"].append(vendedor)
        self._salvar_local()
        self._firebase_put_registro("vendedores", vendedor)
        return vendedor, None

    def completar_perfil(self, nome, foto):
        """Recria o cadastro do vendedor no banco reaproveitando uma conta
        que já existe no Firebase Auth (self.uid/self.id_token já setados
        por fazer_login) mas que ficou sem perfil -- por exemplo, se o
        cadastro foi excluído em 'Gerenciar vendedores' mas a conta de
        login continuou existindo. Não cria uma conta nova, só o registro."""
        vendedor = {"id": self.uid, "nome": nome.strip(), "foto": foto}
        self._dados["vendedores"] = [v for v in self._dados["vendedores"] if v["id"] != self.uid]
        self._dados["vendedores"].append(vendedor)
        self._salvar_local()
        self._firebase_put_registro("vendedores", vendedor)
        return vendedor

    def fazer_login(self, email, senha):
        """Autentica no Firebase Auth e carrega o perfil do vendedor
        correspondente ao uid. Retorna (vendedor, None) em caso de sucesso.
        Se a autenticação falhar, retorna (None, mensagem_de_erro). Se a
        conta autenticar mas não tiver um cadastro de vendedor associado
        (perfil apagado, conta órfã), retorna (None, "PERFIL_AUSENTE") --
        nesse caso self.id_token/self.uid continuam preenchidos, pra dar
        pra chamar completar_perfil() na sequência sem pedir login de novo.

        Não guardamos sessão em disco de propósito: a cada vez que o app
        abre, pede email/senha de novo (decisão explícita do usuário)."""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        try:
            resp = requests.post(
                url,
                json={"email": email, "password": senha, "returnSecureToken": True},
                timeout=FIREBASE_TIMEOUT,
            )
            resp_json = resp.json()
        except Exception as erro:
            return None, f"Sem conexão com o Firebase ({erro})."

        if not resp.ok:
            return None, _mensagem_erro_auth(resp_json)

        self.id_token = resp_json["idToken"]
        self.uid = resp_json["localId"]

        self.carregar()  # agora com idToken válido, recarrega já autenticado
        vendedor = self.vendedor_por_id(self.uid)
        if not vendedor:
            return None, "PERFIL_AUSENTE"
        return vendedor, None

    def sair(self):
        """Encerra a sessão atual (logout)."""
        self.id_token = None
        self.uid = None

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

    def _salvar_local(self):
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(self._dados, f, ensure_ascii=False, indent=2)

    # ---------- vendedores ----------

    def listar_vendedores(self):
        return list(self._dados["vendedores"])

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
            self._salvar_local()
            self._firebase_delete_registro("vendedores", vendedor_id)
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
        self._salvar_local()
        self._firebase_put_registro("vendas", venda)
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
            self._salvar_local()
            self._firebase_delete_registro("vendas", venda_id)
        return removeu

    def limpar_vendas(self):
        self._dados["vendas"] = []
        self._salvar_local()
        self._firebase_delete_colecao("vendas")

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
