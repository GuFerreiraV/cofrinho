# 📋 Escopo do Projeto: Chatbot de Controle Financeiro (Telegram)

> **Estado atual:** fases 1 e 2 entregues e em produção (Vercel + Neon). Fase 3 (dashboard) iniciada com o MVP em Mini App do Telegram.

## 1. Visão Geral

Bot para Telegram que permite ao usuário registrar despesas pessoais de forma rápida via chat, categorizá-las automaticamente e consultar relatórios de gastos (diário, semanal, mensal e geral) e um dashboard com gráficos, com todos os valores formatados em Reais (R$) e uso de ícones para facilitar a leitura.

**Objetivo principal:** eliminar o atrito de registrar gastos manualmente em planilhas, permitindo o lançamento em segundos direto pelo Telegram.

---

## 2. Escopo Funcional

### 2.1 Registro de Despesas

O usuário registra uma despesa informando:

| Campo | Descrição | Obrigatório |
|---|---|---|
| 💰 Valor gasto | Valor em R$ (`45`, `45,90`, `R$ 1.234,56`) | Sim |
| 💳 Forma de pagamento | Pix, Débito, Crédito, Dinheiro ou Voucher | Sim |
| 📅 Data | Data do gasto (padrão: hoje, se omitida) | Sim |
| 📝 Descrição | Texto livre descrevendo o gasto (até 100 caracteres) | Sim |

**Formas de entrada** (todas implementadas):

| Entrada | Exemplo |
|---|---|
| Comando estruturado | `/gasto 45 debito "mercado"` |
| Linguagem natural | *"Gastei 45 reais no mercado com débito hoje"* |
| Vários gastos numa mensagem | *"Gastei 119 reais no mercado ontem, no débito e R$20 na padaria hoje, usando o voucher"* |
| Conversa guiada | `/gasto` sozinho, ou qualquer mensagem incompleta: o bot pergunta só o que faltar |

**Formas de pagamento reconhecidas:**

| Forma | Ícone | Sinônimos aceitos |
|---|---|---|
| Pix | ⚡ | pix |
| Débito | 💳 | débito, cartão de débito |
| Crédito | 💳 | crédito, cartão de crédito, cartão |
| Dinheiro | 💵 | dinheiro, espécie, cash |
| Voucher | 🎟️ | voucher, VR, VA, vale-refeição, vale-alimentação, cartão voucher |

**Datas reconhecidas:** `hoje`, `ontem`, `anteontem`, `05/09`, `05/09/2026`, `dia 5`, `5 de setembro`. Datas sem ano, ou só com o dia, são interpretadas no passado. Uma data inválida (`31/02`) faz o bot perguntar a data.

**Vários gastos numa mensagem:**
- **Divisão:** a mensagem é dividida entre os valores, no último conector (`,` `;` `e` `mais` `também`) antes de cada novo valor. Números sem conector entre si continuam sendo um gasto só: em *"2 pães por 10 reais"*, o valor é R$ 10.
- **Herança de campos:** forma de pagamento e data informadas uma única vez valem para os demais gastos, desde que não haja conflito. Em *"45 no mercado e 20 na padaria, no pix"*, os dois ficam Pix.
- **Gastos incompletos:** entram numa fila, e o bot pergunta o que falta em cada um, em ordem ("Gasto 2 de 3 · …").
- **Limite:** 5 gastos por mensagem.

### 2.2 Categorização

Cada despesa é enquadrada automaticamente em uma categoria por palavra-chave da descrição:

| Categoria | Ícone | Exemplos |
|---|---|---|
| Lazer | 🎮 | Videogames, cinema, shopping, streaming |
| Estudos | 📚 | Cursos, livros, material escolar |
| Comida | 🍔 | Mercado, restaurante, delivery, padaria |
| Investimentos | 📈 | Aportes, tesouro, CDB, ações |
| Outros | 📦 | Gastos não classificados |

- **Sem palavra-chave conhecida:** o bot pergunta a categoria com botões inline, em vez de jogar em "Outros" sem avisar.
- **Correção:** todo registro tem o botão "✏️ Corrigir categoria".

### 2.3 Consulta de Gastos

| Comando | Função |
|---|---|
| `/diario` | Total gasto no dia atual, por categoria |
| `/semanal` | Total gasto na semana atual (desde segunda-feira), por categoria |
| `/mensal` | Total gasto no mês atual, por categoria |
| `/geral` | Total histórico, somando todos os meses |
| `/dashboard` | Abre o painel com gráficos (Mini App do Telegram) |

**Formato da resposta** (exemplo `/mensal`):

```
📊 Resumo de Setembro/2026

🎮 Lazer         R$ 320,00
📚 Estudos       R$ 150,00
🍔 Comida        R$ 890,50
📈 Investimentos R$ 500,00
📦 Outros        R$  45,00
─────────────────────────
💵 Total         R$ 1.905,50
```

### 2.4 Dashboard (MVP)

Painel aberto pelo `/dashboard`, que roda **dentro do Telegram** como Mini App e tem layout pensado para celular:

| Elemento | Conteúdo |
|---|---|
| Filtros | Período (este mês, últimos 3 meses, tudo) e categoria (todas ou uma) |
| Total | Soma e quantidade de gastos no período |
| Gráfico de pizza | Distribuição por categoria. Com uma categoria filtrada, distribuição por forma de pagamento |
| Gráfico de barras | Total por mês nos últimos 6 meses (respeita o filtro de categoria) |
| Maiores gastos | Os 5 maiores gastos do período, com data e forma de pagamento |

- **Tema:** acompanha o modo claro ou escuro do Telegram.
- **Cores:** cada categoria tem sempre a mesma cor. A paleta é validada para daltonismo, e a legenda mostra valor e percentual, então a identificação nunca depende só da cor.

### 2.5 Comandos de Apoio

| Comando | Função | Estado |
|---|---|---|
| `/ajuda` | Lista de comandos com exemplos | ✅ Implementado |
| `/cancelar` | Cancela o registro em andamento (e a fila de gastos) | ✅ Implementado |
| `/editar` | Editar um gasto registrado | 🔜 Próxima fase |
| `/excluir` | Remover um gasto | 🔜 Próxima fase |
| `/categorias` | Listar/gerenciar categorias | 🔜 Futuro |

---

## 3. Requisitos Não Funcionais

- 💱 **Moeda:** todos os valores formatados em Reais (`R$ 1.234,56`, separador de milhar `.` e decimal `,`).
- 🎨 **Ícones:** uso consistente de emojis por categoria, forma de pagamento e tipo de mensagem (sucesso ✅, erro ❌, alerta ⚠️).
- ⚡ **Resposta rápida:** registro de gasto em no máximo 1-2 interações. Vários gastos cabem numa mensagem só.
- 🔒 **Privacidade e segurança:**
  - Os dados são isolados por usuário, pelo `from_user.id` do Telegram.
  - O bot só funciona em conversa privada e ignora grupos.
  - O dashboard só aceita a identidade assinada pelo Telegram (`initData`).
  - Os logs não registram valores nem descrições.
- 📱 **Disponibilidade:** o bot responde de forma consistente a comandos mal formatados, com mensagens de erro claras. Mensagens acima de 300 caracteres são recusadas.

---

## 4. Modelo de Dados

**Tabela `despesas`:**

| Campo | Tipo |
|---|---|
| id | int (PK) |
| user_id | bigint (id do usuário no Telegram) |
| valor | decimal(10,2) |
| forma_pagamento | varchar |
| data | date |
| descricao | varchar |
| categoria | varchar |
| criado_em | timestamp com fuso |

**Tabela `fsm_estados`:** estado das conversas em andamento (o que o bot está esperando e os dados parciais, inclusive a fila de gastos). Expira em 24h.

---

## 5. Arquitetura Técnica (resumo)

Detalhes em [`arquitetura-tecnica-chatbot-financeiro.md`](arquitetura-tecnica-chatbot-financeiro.md).

- **Bot:** Python 3.12+ com aiogram 3.
- **Banco:** PostgreSQL no Neon em produção; SQLite para desenvolvimento local.
- **Hospedagem:** funções serverless na Vercel. O bot recebe as mensagens por webhook, e o dashboard é servido pela mesma aplicação.
- **Categorização e parsing:** 100% locais (regex, dicionário de palavras-chave e `dateparser`), sem API externa.
- **Dashboard:** Mini App do Telegram com HTML, JS puro e Chart.js.

---

## 6. Decisões Tomadas

| # | Questão | Decisão |
|---|---|---|
| 1 | Entrada de dados | As três formas: comando estruturado, linguagem natural (inclusive com vários gastos) e conversa guiada para o que faltar |
| 2 | Categorização | Regras fixas por palavra-chave; IA fica como possível upgrade futuro |
| 3 | Correção de categoria | Pergunta só quando nenhuma palavra-chave bate. Sempre há o botão de correção |
| 4 | Múltiplas moedas | Só R$ |
| 5 | Multiusuário | Sim, desde o início: cada usuário vê só os próprios dados. Uso restrito a conversas privadas |
| 6 | Edição/exclusão | Fica para a próxima fase (só a correção de categoria já existe) |
| 7 | Acesso ao dashboard | Mini App do Telegram: sem login e sem link que possa vazar |
| 8 | Hospedagem | Vercel + Neon, planos gratuitos sem cartão de crédito |

---

## 7. Fora do Escopo (por enquanto)

- Metas de gastos e alertas de orçamento
- Integração com contas bancárias/Open Finance
- Relatórios exportáveis (PDF/Excel)
- Categorias personalizadas pelo usuário

---

## 8. Roadmap

| Fase | Entrega | Estado |
|---|---|---|
| 1 | Registro de despesas, categorização e comandos `/diario`, `/semanal`, `/mensal`, `/geral` | ✅ Entregue |
| 2 | Deploy em produção, `/ajuda`, correções de segurança, forma de pagamento Voucher, vários gastos por mensagem | ✅ Entregue |
| 3 | Dashboard com gráficos (MVP entregue: pizza, barras e maiores gastos), `/editar` e `/excluir` | 🚧 Em andamento |
| 4 | Metas de orçamento, alertas, exportação de relatórios | 🔜 Futuro |
