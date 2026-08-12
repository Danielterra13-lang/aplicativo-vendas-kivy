"""
Lógica das telas do Aplicativo de Vendas.
O layout (kv) fica em main.kv; aqui só ficam os dados e as ações.
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.checkbox import CheckBox
from kivy.uix.dropdown import DropDown
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout

import data_manager as dm

MESES_PT = ["", "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def app():
    return App.get_running_app()


def _formatar_mes(mes_iso):
    ano, mes = mes_iso.split("-")
    return f"{MESES_PT[int(mes)]}/{ano}"


def _formatar_dia(dia_iso):
    ano, mes, dia = dia_iso.split("-")
    return f"{dia}/{mes}/{ano}"


def _linha_com_fundo(**kwargs):
    """BoxLayout com um card cinza-escuro desenhado atrás, usado nas listas
    de 'Gerenciar vendas' e 'Gerenciar vendedores'. O retângulo acompanha
    pos/size do widget (por isso o bind -- sem isso ele fica "preso" no
    tamanho que tinha no instante da criação)."""
    from kivy.graphics import Color, RoundedRectangle

    row = BoxLayout(**kwargs)
    with row.canvas.before:
        Color(0.19, 0.19, 0.21, 0.9)
        rect = RoundedRectangle(pos=row.pos, size=row.size, radius=[10])

    def _atualizar(_instancia, _valor):
        rect.pos = row.pos
        rect.size = row.size

    row.bind(pos=_atualizar, size=_atualizar)
    return row


def _label_flex(**kwargs):
    """Label cujo text_size acompanha a própria largura do widget. Usar um
    número fixo de dp pro text_size (como fizemos antes) funciona bem numa
    janela de desktop, mas quebra em celular: a largura da tela é menor que
    esse número fixo, e o texto passa a ser desenhado numa caixa mais larga
    que a tela, cortando os primeiros caracteres pra fora da área visível.
    Vinculando text_size à largura real do widget, o texto sempre alinha e
    quebra certo, em qualquer tamanho de tela."""
    lbl = Label(**kwargs)
    lbl.bind(width=lambda inst, valor: setattr(inst, "text_size", (valor, None)))
    return lbl


# --------------------------------------------------------------- Login
class LoginScreen(Screen):
    def on_pre_enter(self, *a):
        # Como esta é a primeira tela do app, o Kivy pode tentar ativá-la
        # ainda durante a montagem do main.kv, antes de self.ids estar
        # pronto -- nesse caso, tenta de novo no próximo frame.
        if "email_input" not in self.ids:
            Clock.schedule_once(lambda dt: self.on_pre_enter(), 0)
            return

        app().vendedor_atual = None
        app().cliente_atual = None
        self.ids.senha_input.text = ""

    def entrar(self):
        email = self.ids.email_input.text.strip()
        senha = self.ids.senha_input.text
        if not email or not senha:
            self._popup_aviso("Preencha email e senha.")
            return

        botao = self.ids.get("botao_entrar")
        if botao:
            botao.disabled = True
        vendedor, erro = app().store.fazer_login(email, senha)
        if botao:
            botao.disabled = False

        if erro == "PERFIL_AUSENTE":
            # A conta de login existe e a senha está certa, mas o cadastro
            # do vendedor (nome/foto) não foi encontrado -- provavelmente
            # foi excluído em "Gerenciar vendedores" antes. Manda pra Criar
            # Conta, mas em modo "completar cadastro": não cria uma conta
            # nova, só preenche o perfil que falta pra essa que já existe.
            tela_criar = self.manager.get_screen("criar_conta")
            tela_criar.modo_recuperacao = True
            self.manager.current = "criar_conta"
            return

        if erro:
            self._popup_aviso(erro)
            return

        app().vendedor_atual = vendedor
        self.manager.current = "menu"

    def ir_para_criar_conta(self):
        self.manager.current = "criar_conta"

    def _popup_aviso(self, msg):
        Popup(title="Atenção", content=Label(text=msg), size_hint=(0.7, 0.3)).open()


# ---------------------------------------------------------- Criar conta
class CriarContaScreen(Screen):
    foto_selecionada = None
    # True quando chegamos aqui vindo do Login porque a conta existe mas o
    # cadastro (nome/foto) sumiu -- nesse caso email/senha ficam desativados
    # e "confirmar" só recria o perfil, sem mexer na conta de login.
    modo_recuperacao = False

    def on_pre_enter(self, *a):
        self.foto_selecionada = dm.FOTOS_PERFIL[0]
        self.ids.nome_input.text = ""
        grid = self.ids.grid_fotos
        grid.clear_widgets()
        for foto in dm.FOTOS_PERFIL:
            img_btn = Factory.CardButton(size_hint=(None, None), size=(dp(74), dp(74)), padding=dp(4))
            img_btn.add_widget(Image(source=foto))
            img_btn.bind(on_release=lambda *_a, f=foto: self.escolher_foto(f))
            grid.add_widget(img_btn)

        if self.modo_recuperacao:
            self.ids.barra_topo.titulo = "Completar cadastro"
            self.ids.email_input.text = "(conta já existe -- só falta o perfil)"
            self.ids.email_input.disabled = True
            self.ids.senha_input.text = ""
            self.ids.senha_input.disabled = True
        else:
            self.ids.barra_topo.titulo = "Criar conta"
            self.ids.email_input.text = ""
            self.ids.email_input.disabled = False
            self.ids.senha_input.text = ""
            self.ids.senha_input.disabled = False

    def escolher_foto(self, foto):
        self.foto_selecionada = foto
        self.ids.preview.source = foto

    def confirmar(self):
        nome = self.ids.nome_input.text.strip()
        if not nome:
            self._popup_aviso("Digite o nome do vendedor.")
            return
        foto = self.foto_selecionada or dm.FOTOS_PERFIL[0]

        if self.modo_recuperacao:
            vendedor = app().store.completar_perfil(nome, foto)
            self.modo_recuperacao = False
            app().vendedor_atual = vendedor
            self.manager.current = "menu"
            return

        email = self.ids.email_input.text.strip()
        senha = self.ids.senha_input.text
        if not email or not senha:
            self._popup_aviso("Preencha email e senha.")
            return

        botao = self.ids.get("botao_criar")
        if botao:
            botao.disabled = True
        vendedor, erro = app().store.criar_conta(email, senha, nome, foto)
        if botao:
            botao.disabled = False

        if erro:
            self._popup_aviso(erro)
            return

        app().vendedor_atual = vendedor
        self.manager.current = "menu"

    def _popup_aviso(self, msg):
        Popup(title="Atenção", content=Label(text=msg), size_hint=(0.7, 0.3)).open()

    def voltar(self):
        self.modo_recuperacao = False
        self.manager.current = "login"


# ------------------------------------------------------------------ Menu
class MenuScreen(Screen):
    def on_pre_enter(self, *a):
        v = app().vendedor_atual
        if v:
            self.ids.foto_vendedor.source = v["foto"]
            self.ids.nome_vendedor.text = v["nome"]

    def sair(self):
        app().store.sair()
        app().vendedor_atual = None
        self.manager.current = "login"


# --------------------------------------------------------------- Clientes
class ClientesScreen(Screen):
    def on_pre_enter(self, *a):
        grid = self.ids.grid_clientes
        grid.clear_widgets()
        for cliente in dm.CLIENTES:
            card = Factory.CardButton(size_hint=(None, None), size=(dp(140), dp(150)))
            card.add_widget(Image(source=cliente["foto"], size_hint=(1, 0.75)))
            card.add_widget(Label(text=cliente["nome"], size_hint=(1, 0.25), color=(1, 1, 1, 1)))
            card.bind(on_release=lambda *_a, cid=cliente["id"]: self.selecionar_cliente(cid))
            grid.add_widget(card)

    def selecionar_cliente(self, cliente_id):
        app().cliente_atual = dm._cliente_por_id(cliente_id)
        self.manager.current = "produtos"

    def voltar(self):
        self.manager.current = "menu"


# --------------------------------------------------------------- Produtos
class ProdutoRow(BoxLayout):
    pass


class ProdutosScreen(Screen):
    def on_pre_enter(self, *a):
        self.carrinho = {p["id"]: 0 for p in dm.PRODUTOS}
        cliente = app().cliente_atual
        self.ids.titulo_cliente.text = f"Venda para: {cliente['nome']}" if cliente else "Venda"
        self._montar_lista()
        self._atualizar_total()

    def _montar_lista(self):
        box = self.ids.lista_produtos
        box.clear_widgets()
        self._labels_qtd = {}
        for produto in dm.PRODUTOS:
            row = Factory.ProdutoRow(size_hint=(1, None), height=dp(72))
            row.add_widget(Image(source=produto["foto"], size_hint=(0.18, 1)))

            info = BoxLayout(orientation="vertical", size_hint=(0.42, 1))
            info.add_widget(_label_flex(text=produto["nome"], color=(1, 1, 1, 1), halign="left",
                                         valign="middle"))
            info.add_widget(_label_flex(text=f"R$ {produto['preco']:.2f}", color=(0.8, 0.85, 1, 1),
                                         font_size=sp(13), halign="left", valign="middle"))
            row.add_widget(info)

            menos = Factory.TemaButtonFino(text="-", size_hint=(0.12, 0.8))
            menos.bind(on_release=lambda *_a, pid=produto["id"]: self._alterar_qtd(pid, -1))
            row.add_widget(menos)

            lbl_qtd = Label(text="0", size_hint=(0.12, 1), color=(1, 1, 1, 1), bold=True)
            self._labels_qtd[produto["id"]] = lbl_qtd
            row.add_widget(lbl_qtd)

            mais = Factory.TemaButtonFino(text="+", size_hint=(0.12, 0.8))
            mais.bind(on_release=lambda *_a, pid=produto["id"]: self._alterar_qtd(pid, 1))
            row.add_widget(mais)

            box.add_widget(row)

    def _alterar_qtd(self, produto_id, delta):
        nova = max(0, self.carrinho[produto_id] + delta)
        self.carrinho[produto_id] = nova
        self._labels_qtd[produto_id].text = str(nova)
        self._atualizar_total()

    def _atualizar_total(self):
        total = 0.0
        for produto in dm.PRODUTOS:
            total += produto["preco"] * self.carrinho[produto["id"]]
        self.ids.total_label.text = f"Total: R$ {total:.2f}"

    def finalizar_venda(self):
        itens = [{"produto_id": pid, "qtd": qtd} for pid, qtd in self.carrinho.items() if qtd > 0]
        if not itens:
            Popup(title="Atenção", content=Label(text="Adicione ao menos 1 item."),
                  size_hint=(0.7, 0.3)).open()
            return
        venda = app().store.registrar_venda(
            app().vendedor_atual["id"], app().cliente_atual["id"], itens
        )
        Popup(title="Venda registrada",
              content=Label(text=f"Total: R$ {venda['total']:.2f}\nCliente: {app().cliente_atual['nome']}"),
              size_hint=(0.75, 0.4)).open()
        self.manager.current = "menu"

    def voltar(self):
        self.manager.current = "clientes"


# --------------------------------------------------------- Vendas da empresa
class VendasEmpresaScreen(Screen):
    def on_pre_enter(self, *a):
        self.dias_marcados = set()
        self.meses_marcados = set()
        self._montar_dropdown_meses()
        self._montar_dropdown_dias()
        self._atualizar()

    # ---- dropdowns de período (multi-seleção via checkbox, não fecham ao marcar) ----

    LARGURA_DROPDOWN = dp(240)

    def _montar_dropdown_meses(self):
        meses = app().store.meses_disponiveis()
        itens = [(_formatar_mes(mes),
                  lambda ativo, m=mes: self._marcar(self.meses_marcados, m, ativo, "meses"))
                 for mes in meses]
        self.dropdown_meses = self._criar_dropdown(itens)

    def _montar_dropdown_dias(self):
        dias = app().store.dias_disponiveis()
        itens = [(_formatar_dia(dia),
                  lambda ativo, d=dia: self._marcar(self.dias_marcados, d, ativo, "dias"))
                 for dia in dias]
        self.dropdown_dias = self._criar_dropdown(itens)

    def _criar_dropdown(self, itens):
        """Monta um painel sólido (fundo cinza-escuro, cantos arredondados,
        borda) dentro do DropDown -- por padrão o DropDown é transparente e
        fica ilegível em cima do conteúdo da tela."""
        from kivy.graphics import Color, RoundedRectangle, Line

        dropdown = DropDown(auto_dismiss=False, auto_width=False, width=self.LARGURA_DROPDOWN)

        painel = BoxLayout(orientation="vertical", size_hint=(None, None),
                           width=self.LARGURA_DROPDOWN, padding=dp(10), spacing=dp(6))
        with painel.canvas.before:
            Color(0.15, 0.15, 0.17, 0.98)
            fundo = RoundedRectangle(pos=painel.pos, size=painel.size, radius=[10])
            Color(1, 1, 1, 0.15)
            borda = Line(rounded_rectangle=(painel.x, painel.y, painel.width, painel.height, 10), width=dp(1))

        def _atualizar_fundo(_inst, _val):
            fundo.pos = painel.pos
            fundo.size = painel.size
            borda.rounded_rectangle = (painel.x, painel.y, painel.width, painel.height, 10)

        painel.bind(pos=_atualizar_fundo, size=_atualizar_fundo)

        if not itens:
            painel.add_widget(Label(text="Sem vendas ainda", color=(1, 1, 1, 0.6), font_size=sp(13),
                                     size_hint_y=None, height=dp(32)))
        for texto, callback in itens:
            painel.add_widget(self._linha_checkbox(texto, callback))

        btn_fechar = Factory.TemaButtonFino(text="Fechar", size_hint_y=None, height=dp(38))
        btn_fechar.bind(on_release=lambda *_a: dropdown.dismiss())
        painel.add_widget(btn_fechar)

        # altura total = soma dos filhos (cada um já tem height fixo) + padding/spacing
        painel.height = sum(c.height for c in painel.children) + painel.spacing * (len(painel.children) - 1) + 20

        dropdown.add_widget(painel)
        dropdown.height = painel.height
        return dropdown

    def _linha_checkbox(self, texto, callback):
        linha = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        caixa = CheckBox(size_hint=(None, None), size=(dp(24), dp(24)))
        caixa.bind(active=lambda _inst, valor: callback(valor))
        linha.add_widget(caixa)
        linha.add_widget(Label(text=texto, color=(1, 1, 1, 0.9), font_size=sp(13),
                                halign="left", valign="middle",
                                text_size=(self.LARGURA_DROPDOWN - dp(60), dp(34))))
        return linha

    def abrir_dropdown_meses(self, botao):
        self.dropdown_meses.open(botao)

    def abrir_dropdown_dias(self, botao):
        self.dropdown_dias.open(botao)

    def _marcar(self, conjunto, valor, ativo, tipo):
        if ativo:
            conjunto.add(valor)
        else:
            conjunto.discard(valor)
        if tipo == "meses":
            n = len(self.meses_marcados)
            self.ids.botao_filtro_meses.text = f"Meses ({n})" if n else "Meses"
        else:
            n = len(self.dias_marcados)
            self.ids.botao_filtro_dias.text = f"Dias ({n})" if n else "Dias"
        self._atualizar()

    def limpar_filtro(self):
        if getattr(self, "dropdown_meses", None):
            self.dropdown_meses.dismiss()
        if getattr(self, "dropdown_dias", None):
            self.dropdown_dias.dismiss()
        self.on_pre_enter()
        self.ids.botao_filtro_meses.text = "Meses"
        self.ids.botao_filtro_dias.text = "Dias"

    def _cartao_kpi(self, titulo, valor):
        card = _linha_com_fundo(orientation="vertical", size_hint=(1, None), height=dp(90),
                                 padding=dp(12), spacing=dp(4))
        card.add_widget(_label_flex(text=titulo, color=(1, 1, 1, 0.65), font_size=sp(12),
                                     halign="left", valign="top"))
        card.add_widget(_label_flex(text=valor, color=(1, 1, 1, 1), bold=True, font_size=sp(17),
                                     halign="left", valign="middle"))
        return card

    def _atualizar(self):
        k = app().store.kpis_gerais(dias=self.dias_marcados, meses=self.meses_marcados)

        grid = self.ids.grid_kpis
        grid.clear_widgets()
        cartoes = [
            ("Faturamento total", f"R$ {k['total_faturado']:.2f}"),
            ("Vendas registradas", str(k["qtd_vendas"])),
            ("Ticket médio", f"R$ {k['ticket_medio']:.2f}"),
            ("Melhor cliente", f"{k['top_cliente'][0]}\nR$ {k['top_cliente'][1]:.2f}" if k["top_cliente"] else "—"),
            ("Produto mais vendido",
             f"{k['top_produto'][0]}\nR$ {k['top_produto'][1]:.2f}" if k["top_produto"] else "—"),
        ]
        for titulo, valor in cartoes:
            grid.add_widget(self._cartao_kpi(titulo, valor))

        ranking = self.ids.ranking_vendedores
        ranking.clear_widgets()
        if not k["por_vendedor"]:
            ranking.add_widget(Label(text="Nenhuma venda no período selecionado.", color=(1, 1, 1, 0.8),
                                      size_hint_y=None, height=dp(28)))
        for nome, total in k["por_vendedor"]:
            ranking.add_widget(_label_flex(text=f"{nome}: R$ {total:.2f}", color=(1, 1, 1, 1),
                                            size_hint_y=None, height=dp(26), halign="left", valign="middle"))

        lista = self.ids.lista_vendas_data
        lista.clear_widgets()
        vendas = app().store.vendas_filtradas(self.dias_marcados, self.meses_marcados)
        if not vendas:
            lista.add_widget(Label(text="Nenhuma venda no período selecionado.", color=(1, 1, 1, 0.8),
                                    size_hint_y=None, height=dp(28)))
        for venda in vendas:
            cliente = dm._cliente_por_id(venda["cliente_id"])
            vendedor = app().store.vendedor_por_id(venda["vendedor_id"])
            nome_cliente = cliente["nome"] if cliente else venda["cliente_id"]
            nome_vendedor = vendedor["nome"] if vendedor else "vendedor removido"
            data_fmt = venda["data"][:16].replace("T", " ")

            row = _linha_com_fundo(size_hint=(1, None), height=dp(56), padding=[dp(12), dp(6)], spacing=dp(10))
            info = BoxLayout(orientation="vertical")
            info.add_widget(_label_flex(text=f"{data_fmt}  ·  {nome_cliente}", color=(1, 1, 1, 1),
                                         bold=True, font_size=sp(13), halign="left", valign="middle"))
            info.add_widget(_label_flex(text=nome_vendedor, color=(1, 1, 1, 0.65), font_size=sp(12),
                                         halign="left", valign="middle"))
            row.add_widget(info)
            row.add_widget(Label(text=f"R$ {venda['total']:.2f}", color=(1, 1, 1, 1), bold=True,
                                  size_hint=(None, 1), width=dp(100)))
            lista.add_widget(row)

    def voltar(self):
        self.manager.current = "menu"


# ------------------------------------------------------------- Configurações
class ConfiguracoesScreen(Screen):
    def limpar_vendas(self):
        conteudo = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        conteudo.add_widget(Label(text="Apagar TODAS as vendas registradas?\nEssa ação não pode ser desfeita."))
        botoes = BoxLayout(size_hint=(1, 0.4), spacing=dp(10))
        popup = Popup(title="Confirmar", content=conteudo, size_hint=(0.8, 0.4))

        def confirmar(*_a):
            app().store.limpar_vendas()
            popup.dismiss()

        btn_sim = Factory.TemaButtonFino(text="Sim, apagar")
        btn_nao = Factory.TemaButtonFino(text="Cancelar")
        btn_sim.bind(on_release=confirmar)
        btn_nao.bind(on_release=popup.dismiss)
        botoes.add_widget(btn_sim)
        botoes.add_widget(btn_nao)
        conteudo.add_widget(botoes)
        popup.open()

    def voltar(self):
        self.manager.current = "menu"


# ------------------------------------------------------------ Gerenciar vendas
class GerenciarVendasScreen(Screen):
    def on_pre_enter(self, *a):
        self._montar_lista()

    def _montar_lista(self):
        box = self.ids.lista_vendas
        box.clear_widgets()
        vendas = app().store.listar_vendas()

        if not vendas:
            box.add_widget(Label(text="Nenhuma venda registrada.", color=(1, 1, 1, 0.8),
                                  size_hint_y=None, height=dp(40)))
            return

        for venda in vendas:
            cliente = dm._cliente_por_id(venda["cliente_id"])
            vendedor = app().store.vendedor_por_id(venda["vendedor_id"])
            nome_cliente = cliente["nome"] if cliente else venda["cliente_id"]
            nome_vendedor = vendedor["nome"] if vendedor else "vendedor removido"
            data_fmt = venda["data"][:16].replace("T", " ")

            row = _linha_com_fundo(size_hint=(1, None), height=dp(64), padding=[dp(12), dp(6)], spacing=dp(10))

            info = BoxLayout(orientation="vertical")
            info.add_widget(_label_flex(text=f"{nome_cliente}  —  R$ {venda['total']:.2f}", color=(1, 1, 1, 1),
                                         bold=True, halign="left", valign="middle"))
            info.add_widget(_label_flex(text=f"{nome_vendedor} · {data_fmt}", color=(1, 1, 1, 0.65),
                                         font_size=sp(12), halign="left", valign="middle"))
            row.add_widget(info)

            btn_excluir = Factory.TemaButtonFino(text="Excluir", size_hint=(None, 1), width=dp(90))
            btn_excluir.bind(on_release=lambda *_a, vid=venda["id"]: self._confirmar_exclusao(vid))
            row.add_widget(btn_excluir)
            box.add_widget(row)

    def _confirmar_exclusao(self, venda_id):
        conteudo = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        conteudo.add_widget(Label(text="Excluir esta venda?\nEssa ação não pode ser desfeita."))
        botoes = BoxLayout(size_hint=(1, 0.4), spacing=dp(10))
        popup = Popup(title="Confirmar", content=conteudo, size_hint=(0.8, 0.4))

        def confirmar(*_a):
            app().store.excluir_venda(venda_id)
            popup.dismiss()
            self._montar_lista()

        btn_sim = Factory.TemaButtonFino(text="Sim, excluir")
        btn_nao = Factory.TemaButtonFino(text="Cancelar")
        btn_sim.bind(on_release=confirmar)
        btn_nao.bind(on_release=popup.dismiss)
        botoes.add_widget(btn_sim)
        botoes.add_widget(btn_nao)
        conteudo.add_widget(botoes)
        popup.open()

    def voltar(self):
        self.manager.current = "configuracoes"


# -------------------------------------------------------- Gerenciar vendedores
class GerenciarVendedoresScreen(Screen):
    def on_pre_enter(self, *a):
        self._montar_lista()

    def _montar_lista(self):
        box = self.ids.lista_vendedores
        box.clear_widgets()
        vendedores = app().store.listar_vendedores()

        if not vendedores:
            box.add_widget(Label(text="Nenhum vendedor cadastrado.", color=(1, 1, 1, 0.8),
                                  size_hint_y=None, height=dp(40)))
            return

        for vendedor in vendedores:
            row = _linha_com_fundo(size_hint=(1, None), height=dp(64), padding=[dp(12), dp(6)], spacing=dp(10))

            row.add_widget(Image(source=vendedor["foto"], size_hint=(None, 1), width=dp(48)))
            row.add_widget(_label_flex(text=vendedor["nome"], color=(1, 1, 1, 1), bold=True,
                                        halign="left", valign="middle"))

            btn_excluir = Factory.TemaButtonFino(text="Excluir", size_hint=(None, 1), width=dp(90))
            btn_excluir.bind(on_release=lambda *_a, vid=vendedor["id"], nome=vendedor["nome"]:
                              self._confirmar_exclusao(vid, nome))
            row.add_widget(btn_excluir)
            box.add_widget(row)

    def _confirmar_exclusao(self, vendedor_id, nome):
        conteudo = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        conteudo.add_widget(Label(
            text=f"Excluir o vendedor \"{nome}\"?\nAs vendas dele continuam no histórico\nda empresa, mas sem vendedor associado."
        ))
        botoes = BoxLayout(size_hint=(1, 0.4), spacing=dp(10))
        popup = Popup(title="Confirmar", content=conteudo, size_hint=(0.85, 0.45))

        def confirmar(*_a):
            era_vendedor_atual = app().vendedor_atual and app().vendedor_atual["id"] == vendedor_id
            app().store.excluir_vendedor(vendedor_id)
            popup.dismiss()
            if era_vendedor_atual:
                # Só apaga o cadastro no banco -- a conta de login em si
                # continua existindo no Firebase Auth (excluir isso exigiria
                # o Admin SDK, que não usamos aqui). Por isso forçamos logout:
                # se essa pessoa tentar entrar de novo, o login funciona mas
                # sem achar o perfil, então é melhor já cair na tela inicial.
                app().store.sair()
                app().vendedor_atual = None
                self.manager.current = "login"
            else:
                self._montar_lista()

        btn_sim = Factory.TemaButtonFino(text="Sim, excluir")
        btn_nao = Factory.TemaButtonFino(text="Cancelar")
        btn_sim.bind(on_release=confirmar)
        btn_nao.bind(on_release=popup.dismiss)
        botoes.add_widget(btn_sim)
        botoes.add_widget(btn_nao)
        conteudo.add_widget(botoes)
        popup.open()

    def voltar(self):
        self.manager.current = "configuracoes"
