# Chatbot Financeiro (Telegram)

Bot de Telegram para registrar despesas pessoais pelo chat, categorizá-las automaticamente e consultar relatórios em R$, com um dashboard de gráficos que abre dentro do próprio Telegram.

- **Produção:** webhook numa função serverless da [Vercel](https://vercel.com) + PostgreSQL no [Neon](https://neon.tech) (ambos com plano gratuito, sem cartão).
- **Local:** polling + SQLite, sem precisar de nenhum serviço externo.

Especificação: [`escopo-chatbot-financeiro-telegram.md`](escopo-chatbot-financeiro-telegram.md) · [`arquitetura-tecnica-chatbot-financeiro.md`](arquitetura-tecnica-chatbot-financeiro.md)

---

## Uso

| Entrada | Exemplo |
|---|---|
| Comando | `/gasto 45 debito "mercado"` |
| Linguagem natural | `Gastei 45 reais no mercado com débito hoje` |
| Fluxo guiado | `/gasto` sozinho: o bot pergunta o que faltar |
| Vários gastos | `Gastei 119 reais no mercado ontem, no débito e R$20 na padaria hoje, usando o voucher` |

- **Formas de pagamento:** Pix, Débito, Crédito (ou "cartão"), Dinheiro, Voucher (ou VR, VA, vale-refeição, vale-alimentação)
- **Vários gastos numa mensagem:** até 5, separados por `,` `;` `e` `mais` `também`. Forma de pagamento e data ditas uma vez valem para todos (`45 no mercado e 20 na padaria, no pix`). Se faltar algo em algum deles, o bot pergunta um de cada vez.
- **Datas:** `hoje` (padrão), `ontem`, `anteontem`, `05/09`, `05/09/2026`, `dia 5`, `5 de setembro`
- **Categorias:** 🎮 Lazer · 📚 Estudos · 🍔 Comida · 📈 Investimentos · 📦 Outros. São detectadas por palavra-chave; se nenhuma bater, o bot pergunta com botões. Todo registro tem o botão ✏️ para corrigir.
- **Relatórios:** `/diario`, `/semanal` (desde segunda), `/mensal`, `/geral`
- **Dashboard:** `/dashboard` abre um painel (Mini App do Telegram) com o total do período, gráfico de pizza por categoria (ou por forma de pagamento, ao filtrar uma categoria), barras dos últimos 6 meses e os 5 maiores gastos. Filtros: este mês, 3 meses ou tudo, e categoria.
- **Outros:** `/cancelar`, `/ajuda`

---

## Desenvolvimento local

Pré-requisitos: Python 3.12+ e um bot criado no [@BotFather](https://t.me/BotFather) (`/newbot`, copie o token).

```fish
python -m venv .venv
source .venv/bin/activate.fish       # bash/zsh: source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env                 # preencha o BOT_TOKEN
alembic upgrade head                 # cria o SQLite em data/financeiro.db
python -m bot.main                   # inicia o bot em modo polling
```

> ⚠️ **Polling e webhook não funcionam ao mesmo tempo** no mesmo bot. Se o webhook de produção estiver ativo, `python -m bot.main` se recusa a iniciar. Crie um **segundo bot de testes** no @BotFather para desenvolver localmente (recomendado), ou desligue a produção com `python scripts/webhook.py remover`.

### Dashboard local

Fora do Telegram não há `initData` assinado, então o dashboard usa um usuário fixo de desenvolvimento (o atalho é ignorado na Vercel):

```fish
pip install -e ".[dev]"                      # inclui o uvicorn
env DASHBOARD_DEV_USER_ID=<seu id no Telegram> uvicorn api.dashboard:app --reload --port 8000
```

Abra `http://localhost:8000/api/dashboard`. O seu id aparece na coluna `user_id` da tabela `despesas`.

### Testes e lint

```fish
pytest -q
ruff check . ; ruff format .
```

### Variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `BOT_TOKEN` | Sim | — | Token do @BotFather |
| `DATABASE_URL` | Não | `sqlite+aiosqlite:///./data/financeiro.db` | Banco. Aceita a string de conexão do Neon como vem do painel (`postgresql://...?sslmode=require`) |
| `TIMEZONE` | Não | `America/Sao_Paulo` | Fuso usado para definir "hoje" |
| `LOG_LEVEL` | Não | `INFO` | `DEBUG` mostra o resultado do parser de cada mensagem |
| `WEBHOOK_URL` | Produção | — | `https://<projeto>.vercel.app/api/webhook` |
| `WEBHOOK_SECRET` | Produção | — | Segredo que o Telegram envia em cada update; o endpoint recusa requests sem ele |
| `DASHBOARD_URL` | Não | Na Vercel: `https://<domínio de produção>/api/dashboard` | URL do Mini App aberto pelo `/dashboard` |
| `DASHBOARD_DEV_USER_ID` | Não | — | Só local: abre o dashboard no navegador como este usuário. Ignorado na Vercel |

---

## Deploy (Vercel + Neon)

### 1. Banco no Neon

1. Crie um projeto em [console.neon.tech](https://console.neon.tech), de preferência na região **São Paulo** (`sa-east-1`) ou na mais próxima.
2. Em **Connect**, copie a connection string com **Connection pooling** ligado (o host contém `-pooler`).
3. Crie as tabelas a partir do seu PC:
   ```fish
   env DATABASE_URL="postgresql://...-pooler.../neondb?sslmode=require" alembic upgrade head
   ```

### 2. Projeto na Vercel

1. Suba o repositório no GitHub.
2. Em [vercel.com/new](https://vercel.com/new), importe o repositório (Framework Preset: **Other**).
3. Em **Settings → Environment Variables**, cadastre:
   - `BOT_TOKEN`
   - `DATABASE_URL` (a do Neon)
   - `WEBHOOK_SECRET`. Gere com `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `TIMEZONE` (opcional)
4. Faça o deploy e confira `https://<projeto>.vercel.app/api/webhook` no navegador. Deve responder `{"status":"ok"}`.

### 3. Apontar o Telegram para a Vercel

No seu `.env` local, preencha `WEBHOOK_URL` e **o mesmo** `WEBHOOK_SECRET` cadastrado na Vercel. Depois:

```fish
python scripts/webhook.py registrar   # registra o webhook e o menu de comandos
python scripts/webhook.py info        # status, updates pendentes e último erro
```

A cada `git push` na branch principal, a Vercel faz o deploy sozinha. Se um commit alterar os modelos, rode antes `alembic upgrade head` contra o Neon. Se mudar a lista de comandos (`COMANDOS` em `bot/handlers/start_ajuda.py`), rode `registrar` de novo para atualizar o menu do Telegram.

O dashboard não precisa de configuração extra: a Vercel informa o domínio de produção (`VERCEL_PROJECT_PRODUCTION_URL`) e o `/dashboard` monta a URL a partir dele.

### Solução de problemas

- **Bot não responde:** rode `python scripts/webhook.py info`. Um "Último erro" indica falha no endpoint. Veja os logs em Vercel → projeto → **Logs**.
- **`401` nos logs:** o `WEBHOOK_SECRET` da Vercel é diferente do que foi usado no `registrar`. Após corrigir a variável, faça um redeploy.
- **Dashboard mostra "Abra pelo Telegram":** a página foi aberta fora do Telegram, ou o `initData` expirou (validade de 24h). Feche e abra de novo pelo `/dashboard`.
- **Primeira resposta lenta:** é normal. Depois de um tempo parados, a função e o banco (o Neon suspende quando ocioso) levam alguns segundos para acordar.

---

## Arquitetura

```
api/webhook.py        FastAPI: recebe o update, valida o secret, entrega ao aiogram
api/dashboard.py      FastAPI: página do dashboard (GET) e dados (POST, autenticado pelo initData)
bot/main.py           execução local (polling)
bot/app.py            montagem compartilhada do Bot/Dispatcher
bot/handlers/         aiogram: comandos, fluxo guiado (FSM), botões
bot/services/         regras de negócio sem aiogram: parser, categorização, relatórios, formatação
bot/repositories/     acesso ao banco (SQLAlchemy async)
bot/fsm_storage.py    estado das conversas no banco (serverless não guarda memória)
bot/web/              página do dashboard (HTML + JS, sem build) e autenticação do Mini App
alembic/              migrations
scripts/webhook.py    registrar/remover/consultar o webhook
```

Para ensinar novas palavras-chave ao categorizador, edite `PALAVRAS_CHAVE` em `bot/services/categorizacao_service.py`.
