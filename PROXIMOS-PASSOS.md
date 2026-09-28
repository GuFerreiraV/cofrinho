# 🚀 Próximos Passos: Publicação (Vercel + Neon)

Situação: a Fase 1 está funcional e o código já está preparado para produção, com webhook, PostgreSQL e o estado das conversas no banco.
O passo a passo técnico completo está no [README](README.md#deploy-vercel--neon). Este arquivo é o **checklist** da publicação.

> Por que Vercel + Neon e não uma VM? A Oracle Cloud e as outras VMs gratuitas exigem cartão de crédito físico. A Vercel e o Neon têm plano gratuito sem cartão. Como a Vercel não guarda disco nem memória entre requests, o banco foi para o Neon e o estado das conversas para a tabela `fsm_estados`.

---

## ✅ Checklist

### 1. GitHub
- [ ] Criar um repositório **privado** e vazio em github.com/new (ex: `chatbot-financeiro`)
- [ ] Conferir que `.env` e `data/` **não** estão no commit: `git status --ignored`
- [ ] Enviar o código:
  ```fish
  git remote add origin git@github.com:<seu-usuario>/chatbot-financeiro.git
  git push -u origin main
  ```

> Se o `BOT_TOKEN` algum dia for commitado, revogue-o no @BotFather (`/revoke`), porque apagar o commit não basta.

### 2. Neon (banco)
- [ ] Criar a conta em console.neon.tech (login com o GitHub)
- [ ] Criar o projeto na região **São Paulo** (ou na mais próxima)
- [ ] Copiar a connection string **pooled** (o host contém `-pooler`)
- [ ] Criar as tabelas: `env DATABASE_URL="<string do neon>" alembic upgrade head`

### 3. Vercel (aplicação)
- [ ] Criar a conta em vercel.com (login com o GitHub, plano Hobby)
- [ ] Importar o repositório (Framework Preset: **Other**)
- [ ] Gerar o segredo: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Cadastrar as variáveis: `BOT_TOKEN`, `DATABASE_URL`, `WEBHOOK_SECRET` e `TIMEZONE`
- [ ] Fazer o deploy e abrir `https://<projeto>.vercel.app/api/webhook`, que deve responder `{"status":"ok"}`
- [ ] Se o build falhar por versão do Python, ajuste o `.python-version` para uma versão que a Vercel suporte (ex: `3.12`)

### 4. Ligar o Telegram à Vercel
- [ ] No `.env` local, preencher `WEBHOOK_URL` e o **mesmo** `WEBHOOK_SECRET`
- [ ] `python scripts/webhook.py registrar`
- [ ] Testar pelo celular: `/ajuda`, um gasto, `/diario`
- [ ] `python scripts/webhook.py info`: não deve aparecer "Último erro"

### 5. Desenvolvimento a partir de agora
- [ ] Criar um **segundo bot** no @BotFather só para testes locais. Use o token dele no `.env` local, porque o bot de produção fica com o webhook e o polling local se recusa a rodar nele.
- [ ] Fluxo de mudanças: editar → `pytest -q` → `git push`, e a Vercel faz o deploy automático
- [ ] Mudou algum model? Crie a migration (`alembic revision --autogenerate -m "..."`) e rode `alembic upgrade head` no Neon **antes** do push

---

## 🔜 Depois da publicação (opcional)

- **Migrar os gastos já registrados localmente:** o SQLite em `data/financeiro.db` não vai para o Neon automaticamente. Se os registros de teste importarem, dá para escrever um script de cópia. Senão, comece do zero em produção.
- **CI no GitHub Actions** rodando `ruff check .` e `pytest -q` a cada push
- **Backups:** o Neon guarda um histórico curto para restauração (verifique o limite do plano gratuito). Um `pg_dump` mensal para o seu PC dá mais segurança.
- **Fase 2 do roadmap:** `/editar`, `/excluir` e refinamento das palavras-chave
