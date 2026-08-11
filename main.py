from kivy.app import App
from kivy.properties import ObjectProperty

# precisa ser importado antes do build() para as classes das telas
# (SelecaoPerfilScreen, MenuScreen, etc.) já existirem quando o main.kv for parseado.
from screens import (
    SelecaoPerfilScreen,
    AdicionarVendedorScreen,
    MenuScreen,
    ClientesScreen,
    ProdutosScreen,
    VendasEmpresaScreen,
    ConfiguracoesScreen,
    GerenciarVendasScreen,
    GerenciarVendedoresScreen,
)
from data_manager import DataStore


class MainApp(App):
    # Kivy carrega main.kv automaticamente (nome derivado de "MainApp"),
    # não é preciso chamar Builder.load_file manualmente.
    vendedor_atual = ObjectProperty(None, allownone=True)
    cliente_atual = ObjectProperty(None, allownone=True)

    def build(self):
        self.store = DataStore()
        self.title = "Aplicativo de Vendas"
        return self.root


if __name__ == "__main__":
    MainApp().run()
