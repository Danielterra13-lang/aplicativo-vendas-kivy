# Aplicativo de Vendas (Kivy + Firebase)

Link APK: https://github.com/Danielterra13-lang/aplicativo-vendas-kivy/releases/latest

App desktop de registro de vendas com sincronização em tempo real via Firebase Realtime Database (REST puro, sem SDK), autenticação por vendedor via Firebase Auth, cache local para uso offline e build automático de APK Android via GitHub Actions.

Originado do boilerplate de um curso da Hashtag Treinamentos e reconstruído com arquitetura, autenticação, persistência remota e identidade visual próprias.

## O que o app faz

- Cada vendedor tem conta própria (email/senha) e vê seu nome e foto ao entrar
- Registro de venda por carrinho: escolhe o cliente (rede), soma produtos com +/-, fecha o total
- Dashboard de KPIs da empresa: faturamento total, ticket médio, melhor cliente, produto mais vendido, ranking por vendedor
- Filtro multi-seleção por dia e por mês nos KPIs, via checkbox em dropdown
- Gerenciamento de vendedores e de vendas (exclusão individual, com confirmação)
- Funciona sem internet: lê e grava no cache local (`dados.json`) quando o Firebase está fora do ar, e sincroniza de novo na próxima vez que conseguir conexão

## Arquitetura

Separação estrita em camadas, decisão que facilitou muito iterar sem quebrar o resto:

- `main.py`: só bootstrap do App
- `main.kv`: todo o layout e os widgets
- `screens.py`: lógica de cada tela (nenhum posicionamento aqui)
- `data_manager.py`: única camada de dados, Firebase e cache local

`DataStore` (em `data_manager.py`) é a fonte única de verdade sobre vendedores e vendas. Toda leitura tenta o Firebase primeiro (mandando o token da sessão atual) e cai pro `dados.json` local se não conseguir. Toda escrita grava local primeiro e depois espelha pro Firebase.

## Persistência: Firebase via REST puro, sem SDK

`requests` puro contra a API REST do Realtime Database (`GET`/`PUT`/`DELETE` em `/colecao/id.json`) e da Identity Toolkit (`accounts:signUp`, `accounts:signInWithPassword`) para autenticação. Evita a dependência do SDK oficial, que não tem build pra todas as plataformas, e fica bem mais fácil de debugar porque é só HTTP.

As regras do banco (`firebase_rules.json`) exigem `auth != null` pra leitura e escrita, com validação de estrutura por campo (`.validate`).

## Bugs documentados (o que quebrou e como foi corrigido)

Erros reais encontrados durante a construção, registrados aqui porque o processo de debug importa tanto quanto o resultado final.

**Perda de dados entre dispositivos (o mais sério dos três).** A primeira versão gravava sempre sobrescrevendo o nó inteiro da coleção (`PUT` em `/vendedores.json` com tudo que estava na memória daquele dispositivo). Funciona com um dispositivo só. Quebra assim que existe mais de um sincronizando: se um dispositivo escreve antes de ter sincronizado tudo que já existia no Firebase, o `PUT` da coleção inteira apaga silenciosamente os registros que só existiam remotamente. Causou perda real de contas de vendedor em teste. Correção: gravar e apagar sempre por registro individual (`PUT`/`DELETE` em `/colecao/{id}.json`), nunca reescrever a coleção inteira a partir do estado local, exceto em ações que são explicitamente "apagar tudo".

**Nó do Firebase virando array com `null`.** O Realtime Database devolve um nó como array (com `null` nos índices vazios) quando as chaves de um registro são só números sequenciais, e como objeto quando não são. A função `_normalizar_colecao` aceita os dois formatos e sempre devolve uma lista limpa.

**Layout calibrado pra desktop quebrando em outros tamanhos de tela.** Usar um número fixo de `dp` pro `text_size` de uma `Label` funciona numa janela larga, mas corta texto em telas mais estreitas. Correção: vincular o `text_size` à largura real do próprio widget (`bind(width=...)`), sem número fixo, funcionando em qualquer tamanho.

**Race condition no Kivy.** A primeira tela do `ScreenManager` pode disparar `on_pre_enter` antes de `self.ids` estar populado. Toda tela que depende disso protege com uma checagem e reagenda pro próximo frame se os ids ainda não existirem.

## Trade-offs conscientes

- **Sem login persistente entre execuções.** O app sempre pede email/senha ao abrir, por escolha explícita, mesmo sendo tecnicamente possível guardar sessão. Prioriza segurança simples sobre conveniência.
- **Excluir vendedor não exclui a conta de login.** Apagar o cadastro (nome/foto) via "Gerenciar vendedores" não apaga a conta no Firebase Auth, porque isso exigiria o Admin SDK. Se a pessoa tentar entrar de novo, a senha funciona mas o perfil não é encontrado, e o app oferece uma tela de "completar cadastro" que recria o perfil reaproveitando o mesmo uid, em vez de forçar conta nova.
- **Excluir vendedor mantém o histórico de vendas.** As vendas ficam no relatório da empresa como "vendedor removido", em vez de desaparecer junto com o cadastro.
- **Catálogo de clientes e produtos é fixo no código** (`CLIENTES` e `PRODUTOS` em `data_manager.py`), não vem de um cadastro dinâmico. Decisão consciente pra manter o escopo de portfólio simples. Preços são placeholders.

## Build Android sem VirtualBox

O curso original ensinava VirtualBox com Linux completo pra rodar o `buildozer` (que só roda em Linux). Aqui o build acontece via GitHub Actions, usando a imagem Docker oficial `kivy/buildozer` direto com `docker run`, sem precisar de VM nem instalação local. O workflow roda a cada push na `main` e disponibiliza o APK como artefato da execução, em **Actions > Build Android APK**.

## Como rodar no Windows

1. Clone o repositório
2. Rode `iniciar.bat`, que cria o ambiente virtual, instala as dependências do `requirements.txt` e abre o app
3. Pra criar um atalho na área de trabalho, rode `criar_atalho.vbs`

## Stack

Python 3, Kivy, `requests`, `certifi` (bundle de certificados SSL, necessário pro Android empacotado achar as autoridades certificadoras), Firebase Realtime Database e Firebase Auth via REST, GitHub Actions com Buildozer.

## Próximos passos

- Publicar o case study completo (Notion + GitHub) no mesmo formato dos outros projetos do portfólio
