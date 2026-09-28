# 🏗️ Arquitetura Técnica: Chatbot Financeiro (Telegram)

Documento complementar ao escopo funcional, definindo linguagem, frameworks, arquitetura de código, modelo de dados e integrações.

---

## 1. Stack Tecnológica

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | **Python 3.12+** | Ecossistema maduro para bots, tipagem gradual, libs de data/parsing prontas |
| Framework do bot | **aiogram 3.x** | Async nativo, FSM (máquina de estados) embutida — ideal para o fluxo guiado quando faltar campo, filtros e middlewares elegantes |
| ORM | **SQLAlchemy 2.0 (async)** + **Alembic** | Migração indolor de SQLite → PostgreSQL quando o dashboard entrar em cena; Alembic cuida do versionamento do schema |
| Banco (fase 1) | **SQLite** via `aiosqlite` | Zero custo, zero infra, suficiente para uso pessoal |
| Banco (fase 3+) | **PostgreSQL** | Quando o dashboard web for implementado (múltiplas conexões concorrentes) |
| Parsing de linguagem natural | `dateparser` + regex | Extrai valor, forma de pagamento e data por padrões (ex: `R?\$?\s?\d+([.,]\d{2})?`, dicionário de formas de pagamento); sem custo de API, sem dependência externa |
| Parsing avançado (fase futura) | API do Claude (Haiku) | Não incluído na fase 1 — fica como possível upgrade se o parsing por regex se mostrar limitado demais em frases mais livres |
| Config | `pydantic-settings` | Variáveis de ambiente tipadas e validadas |
| Testes | `pytest` + `pytest-asyncio` | Padrão de mercado para código async |
| Logging | `structlog` | Logs estruturados, úteis para debugar parsing de linguagem natural |

**Por que aiogram em vez de python-telegram-bot?** Ambos são async atualmente, mas o FSM (`aiogram.fsm`) do aiogram encaixa perfeitamente no fluxo "bot pergunta o que faltar" descrito no escopo (seção 2.1), sem precisar de lib extra.

---

## 2. Arquitetura em Camadas

```
┌─────────────────────────────────────────┐
│         Telegram (usuário)               │
└───────────────────┬───────────────────────┘
                    │ updates (polling ou webhook)
┌───────────────────▼───────────────────────┐
│  Handlers (aiogram routers)                │
│  - comandos: /gasto, /diario, /mensal...   │
│  - FSM states: aguardando_valor, etc.      │
│  - mensagens em texto livre                │
└───────────────────┬───────────────────────┘
                    │
┌───────────────────▼───────────────────────┐
│  Services (regras de negócio)              │
│  - ParserService (regex + dateparser)      │
│  - CategorizacaoService (palavra-chave)    │
│  - RelatorioService (agrega por período)   │
│  - FormatadorService (R$, ícones)          │
└───────────────────┬───────────────────────┘
                    │
┌───────────────────▼───────────────────────┐
│  Repository (SQLAlchemy)                   │
│  - DespesaRepository                       │
│  - UsuarioRepository                       │
└───────────────────┬───────────────────────┘
                    │
┌───────────────────▼───────────────────────┐
│  Banco (SQLite → PostgreSQL)               │
└─────────────────────────────────────────────┘
```

Sem chamada a API externa na fase 1 — todo o parsing e categorização rodam localmente (regex + dicionário de palavras-chave).

Separar **handlers → services → repository** evita que a lógica de negócio fique presa no aiogram — importante se um dia você quiser reusar `RelatorioService` no dashboard web (fase 3), sem reescrever nada.

---

## 3. Estrutura de Pastas

```
chatbot-financeiro/
├── bot/
│   ├── __init__.py
│   ├── main.py                # ponto de entrada, registra routers
│   ├── config.py              # pydantic-settings (BOT_TOKEN, ANTHROPIC_API_KEY, DB_URL)
│   ├── handlers/
│   │   ├── gasto.py           # /gasto + fluxo FSM + linguagem natural
│   │   ├── relatorios.py      # /diario /semanal /mensal /geral
│   │   ├── edicao.py          # /editar /excluir (fase 2)
│   │   └── ajuda.py
│   ├── states/
│   │   └── registro_gasto.py  # FSM states (aguardando_valor, aguardando_forma...)
│   ├── services/
│   │   ├── parser_service.py
│   │   ├── categorizacao_service.py
│   │   ├── relatorio_service.py
│   │   └── formatador_service.py
│   ├── repositories/
│   │   ├── despesa_repository.py
│   │   └── usuario_repository.py
│   └── models/
│       └── despesa.py          # modelos SQLAlchemy
├── alembic/                    # migrations
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 4. Fluxo de Registro de Despesa

Combinando as três opções do escopo (seção 2.1) em um fluxo único:

1. **Comando estruturado** (`/gasto 45 debito "mercado"`) → parsing direto por regex, campos já vêm em ordem fixa.
2. **Linguagem natural** (`"Gastei 45 reais no mercado com débito hoje"`) → `ParserService` roda em sequência:
   - regex para valor: `R?\$?\s?\d+(?:[.,]\d{2})?`
   - dicionário de sinônimos para forma de pagamento (`pix`, `débito`/`cartão de débito`, `crédito`, `dinheiro`)
   - `dateparser` para expressões de data em português (`hoje`, `ontem`, `dia 5`, `05/09`)
   - o que sobrar do texto (sem os trechos já capturados) vira a descrição
3. **Campos faltando** (de qualquer uma das duas entradas, ou que o regex não conseguiu identificar) → bot entra em FSM e pergunta só o que falta, campo a campo — nunca reinicia a conversa do zero.

Isso resolve a decisão em aberto #1 do escopo: comando é o caminho rápido, linguagem natural com regex é o fallback amigável, e o FSM garante que nada fica incompleto — tudo sem chamada de rede.

---

## 5. Categorização

- **Regra por palavra-chave**, único mecanismo na fase 1: dicionário `{"mercado": "Comida", "curso": "Estudos", "cinema": "Lazer", "aporte": "Investimentos", ...}`, testado contra a descrição extraída.
- Se nenhuma palavra-chave bater, o bot **pergunta a categoria com botões inline** (um clique, sem digitar) — nunca deixa cair em "Outros" silenciosamente.
- Toda despesa registrada tem um botão "✏️ corrigir categoria" — resolve a decisão em aberto #3 (perguntar sempre seria fricção demais; só perguntar quando a palavra-chave falha é o equilíbrio certo).
- O dicionário de palavras-chave fica em um arquivo separado (`categorizacao_service.py`) para ser fácil de expandir conforme você for usando o bot e percebendo padrões que faltam.

---

## 6. Modelo de Dados (SQLAlchemy)

```python
# bot/models/despesa.py
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import Numeric, Date, DateTime
from datetime import date, datetime
from decimal import Decimal

class Base(DeclarativeBase):
    pass

class Despesa(Base):
    __tablename__ = "despesas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)  # chat_id do Telegram
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    forma_pagamento: Mapped[str] = mapped_column(index=True)
    data: Mapped[date] = mapped_column(Date, index=True)
    descricao: Mapped[str]
    categoria: Mapped[str] = mapped_column(index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Índices em `user_id`, `data` e `categoria` porque são exatamente os campos usados nos `GROUP BY` dos comandos `/diario`, `/semanal`, `/mensal` e `/geral`.

O `user_id` como chave de isolamento já cobre a decisão em aberto #5 (multiusuário): o schema já suporta múltiplos usuários isolados desde o dia um, mesmo que você seja o único usando agora — não custa nada a mais e evita retrabalho depois.

---

## 7. APIs Externas Necessárias

| API | Uso | Custo |
|---|---|---|
| **Telegram Bot API** | Recebimento/envio de mensagens (via aiogram) | Gratuita |

Nenhuma API externa é necessária na fase 1 — parsing e categorização rodam 100% localmente. Open Finance / integração bancária está explicitamente fora do escopo (seção 7 do documento original).

---

## 8. Hospedagem & Deploy

Duas rotas, dependendo do quanto você quer investir em infra agora:

**Opção A — Polling (recomendada para começar)**
- Sem necessidade de HTTPS/domínio.
- Roda em qualquer VPS barata, um Raspberry Pi, ou até um container gratuito (Railway free tier, Fly.io).
- Mais simples de depurar localmente.

**Opção B — Webhook**
- Necessário só quando o volume justificar (webhook é mais eficiente em escala, mas exige HTTPS).
- Faz sentido migrar para isso junto com a fase 3 (dashboard web), quando você já vai precisar de um domínio/certificado de qualquer forma.

Sugestão: começar com **polling em Railway ou Fly.io** (free tier cobre uso pessoal tranquilamente) e reavaliar para webhook só na fase do dashboard.

---

## 9. Roadmap Técnico (mapeado ao roadmap funcional)

| Fase funcional | Entregas técnicas |
|---|---|
| 1 | Setup do projeto (aiogram + SQLAlchemy + SQLite), handlers de `/gasto`, parser regex + `dateparser`, categorização por palavra-chave, comandos de relatório |
| 2 | FSM completo para edição/exclusão, `/ajuda`, refino do prompt de categorização |
| 3 | Migração SQLite → PostgreSQL, API REST simples (FastAPI, reusando `RelatorioService`) para alimentar o dashboard, deploy com webhook |
| 4 | Metas de orçamento (nova tabela `orcamentos`), job agendado (`APScheduler`) para alertas, exportação PDF/Excel |

---

## Próximos passos sugeridos

1. Definir onde hospedar (Railway, Fly.io ou VPS própria — polling funciona igual nas três, então a escolha pode esperar até você ter o bot rodando localmente).
2. Eu posso montar o `pyproject.toml` inicial + esqueleto de pastas já funcional, se quiser começar a codar.
