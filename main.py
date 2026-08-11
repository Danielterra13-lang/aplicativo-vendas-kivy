from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ObjectProperty

# precisa ser importado antes do build() para as classes das telas
# (LoginScreen, MenuScreen, etc.) já existirem quando o main.kv for parseado.
from screens import (
    LoginScreen,
    CriarContaScreen,
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

    def on_start(self):
        # Tela de Login já é a primeira exibida (é a que vem primeiro no
        # ScreenManager, no main.kv). Se houver uma sessão salva, tenta
        # renovar o token e pula direto pro Menu -- senão, fica no Login mesmo.
        Clock.schedule_once(self._tentar_auto_login, 0)

    def _tentar_auto_login(self, *_a):
        vendedor = self.store.tentar_login_automatico()
        if vendedor:
            self.vendedor_atual = vendedor
            self.root.current = "menu"


if __name__ == "__main__":
    MainApp().run()
