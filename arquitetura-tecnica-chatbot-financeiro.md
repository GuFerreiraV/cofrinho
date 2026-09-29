# 🏗️ Arquitetura Técnica: Chatbot Financeiro (Telegram)

Documento complementar ao [escopo funcional](escopo-chatbot-financeiro-telegram.md). Descreve a stack, a arquitetura de código, o modelo de dados, a segurança e o deploy **no estado atual do projeto**.

---

## 1. Stack Tecnológica

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | **Python 3.12+** | Ecossistema maduro para bots, tipagem gradual, libs de data/parsing prontas |
| Framework do bot | **aiogram 3.x** | Async nativo e FSM (máquina de estados) embutida, ideal para o fluxo "o bot pergunta o que faltar" |
| HTTP (serverless) | **FastAPI** | Endpoints do webhook e do dashboard nas funções da Vercel |
| ORM | **SQLAlchemy 2 (async)** + **Alembic** | O mesmo código roda em SQLite e PostgreSQL; Alembic versiona o schema |
| Banco (produção) | **PostgreSQL no Neon** via `asyncpg` | Gratuito, sem cartão, com pooler (PgBouncer) para conexões serverless |
| Banco (local) | **SQLite** via `aiosqlite` | Zero infraestrutura para desenvolver |
| Parsing | regex + `dateparser` | Extrai valor, forma de pagamento, data e descrição localmente, sem API externa |
| Dashboard | HTML + JS puro + **Chart.js** + `telegram-web-app.js` | Mini App sem etapa de build, servido pela própria função |
| Config | `pydantic-settings` | Variáveis de ambiente tipadas; segredos como `SecretStr` |
| Testes | `pytest` + `pytest-asyncio` | Inclui testes ponta a ponta do Dispatcher com um Telegram falso |
| Logging | `structlog` | Logs estruturados, sem dados financeiros do usuário |

**Parsing com IA (futuro):** a API do Claude (Haiku) pode entrar se o parsing por regex ficar limitado demais para frases mais livres. Por enquanto não é necessária.

---

## 2. Visão Geral

```
                         ┌──────────────── Vercel (serverless) ────────────────┐
Telegram ── update ────▶ │ api/webhook.py   valida o secret ─▶ aiogram         │
  (chat)                 │                                     handlers         │
                         │                                        │             │
Telegram ── Mini App ──▶ │ api/dashboard.py GET: página                         │
  (/dashboard)           │                  POST: valida initData ─▶ services  │
                         └─────────────────────────────┬────────────────────────┘
                                                       │ asyncpg + TLS verificado
                                                ┌──────▼──────┐
                                                │ Neon (PG)   │ despesas
                                                │  pooler     │ fsm_estados
                                                └─────────────┘
```

**Execução local:** `python -m bot.main` roda o mesmo Dispatcher em modo polling com SQLite, e `uvicorn api.dashboard:app` serve o dashboard.

### Camadas

```
Handlers (aiogram routers)        bot/handlers/     comandos, FSM, botões
        │
Services (regras de negócio)      bot/services/     parser, categorização, relatórios,
        │                                           dashboard, formatação (sem aiogram)
Repository (SQLAlchemy)           bot/repositories/ sempre filtra por user_id
        │
Banco (PostgreSQL / SQLite)
```

Os services não dependem do aiogram. Por isso o dashboard reaproveita os mesmos repositórios, formatadores e categorias do bot, sem duplicar regras.

---

## 3. Estrutura de Pastas

```
chatbot-financeiro/
├── api/
│   ├── webhook.py              # função Vercel: POST do Telegram → aiogram
│   └── dashboard.py            # função Vercel: página (GET) e dados (POST) do dashboard
├── bot/
│   ├── main.py                 # execução local (polling)
│   ├── app.py                  # montagem do Bot/Dispatcher (filtro de chat privado, middlewares)
│   ├── config.py               # pydantic-settings
│   ├── db.py                   # engine, URL do Neon → asyncpg, SSL verificado
│   ├── fsm_storage.py          # estado das conversas na tabela fsm_estados (expira em 24h)
│   ├── middlewares.py          # sessão do banco por update
│   ├── keyboards.py            # teclados inline e CallbackData
│   ├── relogio.py              # "hoje" no fuso configurado
│   ├── handlers/
│   │   ├── gasto.py            # /gasto, texto livre, fila de vários gastos, correção de categoria
│   │   ├── relatorios.py       # /diario /semanal /mensal /geral
│   │   └── start_ajuda.py      # /start /ajuda /dashboard
│   ├── services/
│   │   ├── parser_service.py
│   │   ├── categorizacao_service.py
│   │   ├── relatorio_service.py
│   │   ├── dashboard_service.py
│   │   └── formatador_service.py
│   ├── repositories/despesa_repository.py
│   ├── models/                 # Despesa, FsmEstado
│   ├── states/registro_gasto.py
│   └── web/
│       ├── auth.py             # validação do initData do Mini App
│       └── dashboard.html      # página do dashboard
├── alembic/                    # migrations (0001 despesas, 0002 fsm_estados + timezone)
├── scripts/webhook.py          # registrar/remover/consultar o webhook
├── tests/
├── vercel.json
├── requirements.txt            # dependências de produção (Vercel)
└── pyproject.toml
```

---

## 4. Fluxo de Registro de Despesa

1. **Entrada:** `/gasto <texto>` ou mensagem livre, com até 300 caracteres.
2. **`parse_varios`** divide a mensagem em trechos, um por gasto:
   - datas e textos entre aspas são **mascarados** (trocados por espaços do mesmo tamanho) para que `05/09` não seja lido como valor;
   - entre dois valores, corta no último conector (`,` `;` `e` `mais` `também`). Sem conector, os valores ficam no mesmo trecho.
3. **`parse`** interpreta cada trecho, em sequência:
   1. descrição entre aspas;
   2. data;
   3. valor (prefere o número com `R$` ou "reais");
   4. forma de pagamento (sinônimos, dos mais específicos para os mais genéricos);
   5. descrição: o que sobrar, sem conectores nas pontas.
4. **Herança:** forma de pagamento e data informadas uma vez valem para os trechos sem elas, se não houver conflito.
5. **FSM com fila:** o primeiro gasto vira o atual e os demais vão para a chave `fila`. Para cada gasto:
   - completo e com categoria reconhecida: é salvo na hora, com confirmação e botão ✏️;
   - faltando algo: o bot pergunta só aquilo (valor, data, forma com botões, descrição, categoria com botões);
   - depois de salvar, o próximo da fila é carregado. `/cancelar` descarta tudo.

O estado da conversa fica no banco (`fsm_estados`), e não em memória: na Vercel, cada mensagem pode cair numa instância diferente.

---

## 5. Categorização

- **Palavras-chave:** o dicionário `PALAVRAS_CHAVE` em `categorizacao_service.py` compara palavras inteiras, sem diferenciar acentos nem maiúsculas, e aceita plural simples.
- **Nenhuma palavra-chave bate:** o bot pergunta a categoria com botões inline.
- **Correção:** o botão "✏️ Corrigir categoria" confere se o gasto pertence a quem clicou antes de mostrar as opções.

---

## 6. Dashboard (Mini App)

| Etapa | Detalhe |
|---|---|
| Abertura | `/dashboard` envia um botão `web_app`. A URL vem de `DASHBOARD_URL` ou, na Vercel, de `VERCEL_PROJECT_PRODUCTION_URL` |
| Página | `GET /api/dashboard` devolve o HTML estático, que carrega `telegram-web-app.js` e Chart.js |
| Identidade | A página envia `Telegram.WebApp.initData`. O backend valida o HMAC com o token do bot (`safe_parse_webapp_init_data`) e recusa `initData` com mais de 24h |
| Dados | `POST /api/dashboard` com `{initData, periodo, categoria}` devolve total, pizza, barras e maiores gastos |
| Agregação | `DashboardService` agrega em Python sobre `DespesaRepository.listar`, com resultado idêntico em SQLite e PostgreSQL |

- **Visual:** a página usa as cores do tema do Telegram (`--tg-theme-*`). A paleta dos gráficos tem ordem fixa, em que a cor segue a categoria e não o ranking, e foi validada para daltonismo nos modos claro e escuro.
- **Segurança:** textos do usuário são inseridos via `textContent`, sem risco de XSS.
- **Desenvolvimento local:** `DASHBOARD_DEV_USER_ID` dispensa o `initData`, mas só quando a variável `VERCEL` não existe.

---

## 7. Modelo de Dados

```python
class Despesa(Base):
    __tablename__ = "despesas"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)   # from_user.id do Telegram
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    forma_pagamento: Mapped[str] = mapped_column(index=True)
    data: Mapped[date] = mapped_column(Date, index=True)
    descricao: Mapped[str]
    categoria: Mapped[str] = mapped_column(index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class FsmEstado(Base):
    __tablename__ = "fsm_estados"
    chave: Mapped[str] = mapped_column(String(255), primary_key=True)  # bot:chat:user:destino
    estado: Mapped[str | None]
    dados: Mapped[dict] = mapped_column(JSON)       # gasto atual + fila
    atualizado_em: Mapped[datetime]                 # expira em 24h
```

As formas de pagamento e as categorias são strings. Incluir uma nova (como o Voucher) não exige migration.

---

## 8. Segurança

| Risco | Mitigação |
|---|---|
| Updates falsos no webhook | O cabeçalho `X-Telegram-Bot-Api-Secret-Token` é comparado em tempo constante; sem ele, a resposta é `401` |
| Dados compartilhados em grupos | Filtro no Dispatcher: só conversas privadas. O dono de cada gasto é sempre `from_user.id` |
| Acesso a gastos de outro usuário | Toda consulta do repositório filtra por `user_id`, e callbacks conferem o dono |
| Dashboard acessado por terceiros | Identidade só pelo `initData` assinado pelo Telegram, com validade de 24h. Nenhum id enviado pelo cliente é aceito |
| Vazamento de credenciais | `BOT_TOKEN`, `DATABASE_URL` e `WEBHOOK_SECRET` são `SecretStr` e não aparecem em repr nem em logs |
| Interceptação da conexão com o banco | TLS com verificação de CA e hostname (`certifi`) |
| Dados financeiros em logs | Os logs registram só os campos que faltam e ids, nunca texto, valor ou descrição |
| Entradas abusivas | Limites de 300 caracteres por mensagem, 100 por descrição e 5 gastos por mensagem |
| Update reenviado após erro | O webhook sempre responde `200` (o erro vai para o log), evitando gastos duplicados |

---

## 9. Hospedagem & Deploy

| Componente | Serviço | Observação |
|---|---|---|
| Funções `api/webhook.py` e `api/dashboard.py` | Vercel (Hobby, Framework Preset **Other**) | Deploy automático a cada push na `main` |
| Banco | Neon (free), connection string **pooled** | Migrations rodadas do PC: `alembic upgrade head` |
| Webhook | `python scripts/webhook.py registrar` | Registra a URL, o secret e o menu de comandos |

**Latência:** depois de um tempo parados, a função e o banco (o Neon suspende quando ocioso) levam alguns segundos para acordar. Com eles ativos, a resposta é rápida.

O passo a passo completo está no [README](README.md#deploy-vercel--neon).

---

## 10. Roadmap Técnico

| Fase | Entregas técnicas | Estado |
|---|---|---|
| 1 | aiogram + SQLAlchemy, parser regex + `dateparser`, categorização, relatórios | ✅ |
| 2 | Webhook na Vercel, Neon/asyncpg, FSM no banco, correções de segurança, Voucher, vários gastos por mensagem | ✅ |
| 3 | Dashboard em Mini App (MVP ✅); `/editar` e `/excluir` com FSM; mais visões no dashboard | 🚧 |
| 4 | Metas de orçamento (tabela `orcamentos`), alertas agendados (Vercel Cron), exportação PDF/Excel | 🔜 |
