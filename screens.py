"""
Lógica das telas do Aplicativo de Vendas.
O layout (kv) fica em main.kv; aqui só ficam os dados e as ações.
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.factory import Factory
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


# ------------------------------------------------------- Seleção de perfil
class SelecaoPerfilScreen(Screen):
    def on_pre_enter(self, *a):
        # Como esta é a primeira tela do app, o Kivy pode tentar ativá-la
        # ainda durante a montagem do main.kv, antes de self.ids estar
        # pronto -- nesse caso, tenta de novo no próximo frame.
        if "grid_vendedores" not in self.ids:
            Clock.schedule_once(lambda dt: self.on_pre_enter(), 0)
            return

        app().vendedor_atual = None
        app().cliente_atual = None
        grid = self.ids.grid_vendedores
        grid.clear_widgets()
        for vendedor in app().store.listar_vendedores():
            grid.add_widget(self._criar_card(vendedor))

    def _criar_card(self, vendedor):
        card = Factory.CardButton(size_hint=(None, None), size=(130, 160))
        card.add_widget(Image(source=vendedor["foto"], size_hint=(1, 0.75)))
        card.add_widget(Label(text=vendedor["nome"], size_hint=(1, 0.25),
                               color=(1, 1, 1, 1), shorten=True, shorten_from="right"))
        card.bind(on_release=lambda *_a, vid=vendedor["id"]: self.selecionar_vendedor(vid))
        return card

    def selecionar_vendedor(self, vendedor_id):
        app().vendedor_atual = app().store.vendedor_por_id(vendedor_id)
        self.manager.current = "menu"


# ---------------------------------------------------------- Novo vendedor
class AdicionarVendedorScreen(Screen):
    foto_selecionada = None

    def on_pre_enter(self, *a):
        self.foto_selecionada = dm.FOTOS_PERFIL[0]
        self.ids.nome_input.text = ""
        grid = self.ids.grid_fotos
        grid.clear_widgets()
        for foto in dm.FOTOS_PERFIL:
            img_btn = Factory.CardButton(size_hint=(None, None), size=(90, 90), padding=4)
            img_btn.add_widget(Image(source=foto))
            img_btn.bind(on_release=lambda *_a, f=foto: self.escolher_foto(f))
            grid.add_widget(img_btn)

    def escolher_foto(self, foto):
        self.foto_selecionada = foto
        self.ids.preview.source = foto

    def confirmar(self):
        nome = self.ids.nome_input.text.strip()
        if not nome:
            self._popup_aviso("Digite o nome do vendedor.")
            return
        vendedor = app().store.adicionar_vendedor(nome, self.foto_selecionada or dm.FOTOS_PERFIL[0])
        app().vendedor_atual = vendedor
        self.manager.current = "menu"

    def _popup_aviso(self, msg):
        Popup(title="Atenção", content=Label(text=msg), size_hint=(0.7, 0.3)).open()

    def voltar(self):
        self.manager.current = "selecao_perfil"


# ------------------------------------------------------------------ Menu
class MenuScreen(Screen):
    def on_pre_enter(self, *a):
        v = app().vendedor_atual
        if v:
            self.ids.foto_vendedor.source = v["foto"]
            self.ids.nome_vendedor.text = v["nome"]

    def trocar_vendedor(self):
        self.manager.current = "selecao_perfil"


# --------------------------------------------------------------- Clientes
class ClientesScreen(Screen):
    def on_pre_enter(self, *a):
        grid = self.ids.grid_clientes
        grid.clear_widgets()
        for cliente in dm.CLIENTES:
            card = Factory.CardButton(size_hint=(None, None), size=(140, 150))
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
            row = Factory.ProdutoRow(size_hint=(1, None), height=72)
            row.add_widget(Image(source=produto["foto"], size_hint=(0.18, 1)))

            info = BoxLayout(orientation="vertical", size_hint=(0.42, 1))
            info.add_widget(Label(text=produto["nome"], color=(1, 1, 1, 1), halign="left",
                                   valign="middle", text_size=(220, None)))
            info.add_widget(Label(text=f"R$ {produto['preco']:.2f}", color=(0.8, 0.85, 1, 1),
                                   font_size=13, halign="left", valign="middle", text_size=(220, None)))
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

    LARGURA_DROPDOWN = 240

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
                           width=self.LARGURA_DROPDOWN, padding=10, spacing=6)
        with painel.canvas.before:
            Color(0.15, 0.15, 0.17, 0.98)
            fundo = RoundedRectangle(pos=painel.pos, size=painel.size, radius=[10])
            Color(1, 1, 1, 0.15)
            borda = Line(rounded_rectangle=(painel.x, painel.y, painel.width, painel.height, 10), width=1)

        def _atualizar_fundo(_inst, _val):
            fundo.pos = painel.pos
            fundo.size = painel.size
            borda.rounded_rectangle = (painel.x, painel.y, painel.width, painel.height, 10)

        painel.bind(pos=_atualizar_fundo, size=_atualizar_fundo)

        if not itens:
            painel.add_widget(Label(text="Sem vendas ainda", color=(1, 1, 1, 0.6), font_size=13,
                                     size_hint_y=None, height=32))
        for texto, callback in itens:
            painel.add_widget(self._linha_checkbox(texto, callback))

        btn_fechar = Factory.TemaButtonFino(text="Fechar", size_hint_y=None, height=38)
        btn_fechar.bind(on_release=lambda *_a: dropdown.dismiss())
        painel.add_widget(btn_fechar)

        # altura total = soma dos filhos (cada um já tem height fixo) + padding/spacing
        painel.height = sum(c.height for c in painel.children) + painel.spacing * (len(painel.children) - 1) + 20

        dropdown.add_widget(painel)
        dropdown.height = painel.height
        return dropdown

    def _linha_checkbox(self, texto, callback):
        linha = BoxLayout(size_hint_y=None, height=34, spacing=8)
        caixa = CheckBox(size_hint=(None, None), size=(24, 24))
        caixa.bind(active=lambda _inst, valor: callback(valor))
        linha.add_widget(caixa)
        linha.add_widget(Label(text=texto, color=(1, 1, 1, 0.9), font_size=13,
                                halign="left", valign="middle",
                                text_size=(self.LARGURA_DROPDOWN - 60, 34)))
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
        card = _linha_com_fundo(orientation="vertical", size_hint=(1, None), height=90,
                                 padding=12, spacing=4)
        card.add_widget(Label(text=titulo, color=(1, 1, 1, 0.65), font_size=12,
                               halign="left", valign="top", text_size=(220, None)))
        card.add_widget(Label(text=valor, color=(1, 1, 1, 1), bold=True, font_size=17,
                               halign="left", valign="middle", text_size=(220, None)))
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
                                      size_hint_y=None, height=28))
        for nome, total in k["por_vendedor"]:
            ranking.add_widget(Label(text=f"{nome}: R$ {total:.2f}", color=(1, 1, 1, 1),
                                      size_hint_y=None, height=26, halign="left", valign="middle",
                                      text_size=(560, None)))

        lista = self.ids.lista_vendas_data
        lista.clear_widgets()
        vendas = app().store.vendas_filtradas(self.dias_marcados, self.meses_marcados)
        if not vendas:
            lista.add_widget(Label(text="Nenhuma venda no período selecionado.", color=(1, 1, 1, 0.8),
                                    size_hint_y=None, height=28))
        for venda in vendas:
            cliente = dm._cliente_por_id(venda["cliente_id"])
            vendedor = app().store.vendedor_por_id(venda["vendedor_id"])
            nome_cliente = cliente["nome"] if cliente else venda["cliente_id"]
            nome_vendedor = vendedor["nome"] if vendedor else "vendedor removido"
            data_fmt = venda["data"][:16].replace("T", " ")

            row = _linha_com_fundo(size_hint=(1, None), height=56, padding=[12, 6], spacing=10)
            info = BoxLayout(orientation="vertical")
            info.add_widget(Label(text=f"{data_fmt}  ·  {nome_cliente}", color=(1, 1, 1, 1),
                                   bold=True, font_size=13, halign="left", valign="middle",
                                   text_size=(400, None)))
            info.add_widget(Label(text=nome_vendedor, color=(1, 1, 1, 0.65), font_size=12,
                                   halign="left", valign="middle", text_size=(400, None)))
            row.add_widget(info)
            row.add_widget(Label(text=f"R$ {venda['total']:.2f}", color=(1, 1, 1, 1), bold=True,
                                  size_hint=(None, 1), width=100))
            lista.add_widget(row)

    def voltar(self):
        self.manager.current = "menu"


# ------------------------------------------------------------- Configurações
class ConfiguracoesScreen(Screen):
    def limpar_vendas(self):
        conteudo = BoxLayout(orientation="vertical", spacing=10, padding=10)
        conteudo.add_widget(Label(text="Apagar TODAS as vendas registradas?\nEssa ação não pode ser desfeita."))
        botoes = BoxLayout(size_hint=(1, 0.4), spacing=10)
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
                                  size_hint_y=None, height=40))
            return

        for venda in vendas:
            cliente = dm._cliente_por_id(venda["cliente_id"])
            vendedor = app().store.vendedor_por_id(venda["vendedor_id"])
            nome_cliente = cliente["nome"] if cliente else venda["cliente_id"]
            nome_vendedor = vendedor["nome"] if vendedor else "vendedor removido"
            data_fmt = venda["data"][:16].replace("T", " ")

            row = _linha_com_fundo(size_hint=(1, None), height=64, padding=[12, 6], spacing=10)

            info = BoxLayout(orientation="vertical")
            info.add_widget(Label(text=f"{nome_cliente}  —  R$ {venda['total']:.2f}", color=(1, 1, 1, 1),
                                   bold=True, halign="left", valign="middle", text_size=(420, None)))
            info.add_widget(Label(text=f"{nome_vendedor} · {data_fmt}", color=(1, 1, 1, 0.65),
                                   font_size=12, halign="left", valign="middle", text_size=(420, None)))
            row.add_widget(info)

            btn_excluir = Factory.TemaButtonFino(text="Excluir", size_hint=(None, 1), width=90)
            btn_excluir.bind(on_release=lambda *_a, vid=venda["id"]: self._confirmar_exclusao(vid))
            row.add_widget(btn_excluir)
            box.add_widget(row)

    def _confirmar_exclusao(self, venda_id):
        conteudo = BoxLayout(orientation="vertical", spacing=10, padding=10)
        conteudo.add_widget(Label(text="Excluir esta venda?\nEssa ação não pode ser desfeita."))
        botoes = BoxLayout(size_hint=(1, 0.4), spacing=10)
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
                                  size_hint_y=None, height=40))
            return

        for vendedor in vendedores:
            row = _linha_com_fundo(size_hint=(1, None), height=64, padding=[12, 6], spacing=10)

            row.add_widget(Image(source=vendedor["foto"], size_hint=(None, 1), width=48))
            row.add_widget(Label(text=vendedor["nome"], color=(1, 1, 1, 1), bold=True,
                                  halign="left", valign="middle", text_size=(280, None)))

            btn_excluir = Factory.TemaButtonFino(text="Excluir", size_hint=(None, 1), width=90)
            btn_excluir.bind(on_release=lambda *_a, vid=vendedor["id"], nome=vendedor["nome"]:
                              self._confirmar_exclusao(vid, nome))
            row.add_widget(btn_excluir)
            box.add_widget(row)

    def _confirmar_exclusao(self, vendedor_id, nome):
        conteudo = BoxLayout(orientation="vertical", spacing=10, padding=10)
        conteudo.add_widget(Label(
            text=f"Excluir o vendedor \"{nome}\"?\nAs vendas dele continuam no histórico\nda empresa, mas sem vendedor associado."
        ))
        botoes = BoxLayout(size_hint=(1, 0.4), spacing=10)
        popup = Popup(title="Confirmar", content=conteudo, size_hint=(0.85, 0.45))

        def confirmar(*_a):
            era_vendedor_atual = app().vendedor_atual and app().vendedor_atual["id"] == vendedor_id
            app().store.excluir_vendedor(vendedor_id)
            popup.dismiss()
            if era_vendedor_atual:
                app().vendedor_atual = None
                self.manager.current = "selecao_perfil"
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
