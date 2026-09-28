# 📋 Escopo do Projeto: Chatbot de Controle Financeiro (Telegram)

## 1. Visão Geral

Bot para Telegram que permite ao usuário registrar despesas pessoais de forma rápida via chat, categorizá-las automaticamente e consultar relatórios de gastos (diário, semanal, mensal e geral), com todos os valores formatados em Reais (R$) e uso de ícones para facilitar a leitura.

**Objetivo principal:** eliminar o atrito de registrar gastos manualmente em planilhas, permitindo o lançamento em segundos direto pelo Telegram.

---

## 2. Escopo Funcional

### 2.1 Registro de Despesas

O usuário registra uma despesa informando:

| Campo | Descrição | Obrigatório |
|---|---|---|
| 💰 Valor gasto | Valor em R$ | Sim |
| 💳 Forma de pagamento | Pix, Débito, Crédito, Dinheiro, etc. | Sim |
| 📅 Data | Data do gasto (padrão: hoje, se omitida) | Sim |
| 📝 Descrição | Texto livre descrevendo o gasto | Sim |

**Formas de entrada a decidir** (ver seção 6 — Decisões em Aberto):
- Mensagem em linguagem natural (ex: *"Gastei 45 reais no mercado com débito hoje"*) interpretada pelo bot
- Fluxo guiado por conversa (bot pergunta campo a campo)
- Comando estruturado (ex: `/gasto 45 debito "mercado"`)

> 💡 Recomendação: comando `/gasto` para início rápido, com fallback de conversa guiada (o bot pergunta o que faltar).

### 2.2 Categorização

Cada despesa é automaticamente enquadrada em uma categoria, com possibilidade de o usuário corrigir manualmente:

| Categoria | Ícone | Exemplos |
|---|---|---|
| Lazer | 🎮 | Videogames, cinema, shopping |
| Estudos | 📚 | Cursos, livros, material escolar |
| Comida | 🍔 | Mercado, restaurante, delivery |
| Investimentos | 📈 | Aportes, aplicações |
| Outros | 📦 | Gastos não classificados |

> 💡 Recomendação: categorização automática por palavras-chave da descrição (regra simples) com opção de usar IA (ex: API do Claude) para casos ambíguos, e sempre com botão de "corrigir categoria" após o registro.

### 2.3 Consulta de Gastos (Comandos)

| Comando | Função |
|---|---|
| `/diario` | Total gasto no dia atual, por categoria |
| `/semanal` | Total gasto na semana atual, por categoria |
| `/mensal` | Total gasto no mês atual, por categoria |
| `/geral` | Total histórico, somando todos os meses |
| `/dashboard` | Link para painel web com gráficos e indicadores *(fase futura)* |

**Formato sugerido de resposta** (exemplo `/mensal`):

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

### 2.4 Comandos de Apoio (sugeridos, fora do pedido original)

| Comando | Função |
|---|---|
| `/ajuda` | Lista de comandos disponíveis |
| `/editar` | Editar último gasto registrado |
| `/excluir` | Remover um gasto |
| `/categorias` | Listar/gerenciar categorias |

---

## 3. Requisitos Não Funcionais

- 💱 **Moeda:** todos os valores exibidos formatados em Reais (`R$ 1.234,56`, separador de milhar `.` e decimal `,`)
- 🎨 **Ícones:** uso consistente de emojis por categoria e por tipo de mensagem (sucesso ✅, erro ❌, alerta ⚠️)
- ⚡ **Resposta rápida:** registro de gasto em no máximo 1-2 interações
- 🔒 **Privacidade:** dados financeiros isolados por usuário (chat_id do Telegram como chave)
- 📱 **Disponibilidade:** bot deve responder de forma consistente a comandos mal formatados, com mensagens de erro claras

---

## 4. Modelo de Dados (sugestão inicial)

**Tabela `despesas`:**

| Campo | Tipo |
|---|---|
| id | int (PK) |
| user_id | bigint (chat_id do Telegram) |
| valor | decimal(10,2) |
| forma_pagamento | varchar |
| data | date |
| descricao | text |
| categoria | varchar |
| criado_em | timestamp |

**Tabela `usuarios`** (opcional, para preferências futuras): id, chat_id, nome, moeda_padrão, criado_em.

---

## 5. Arquitetura Técnica (sugestão)

- **Bot:** Python (`python-telegram-bot` ou `aiogram`) — ecossistema maduro, fácil de manter
- **Banco de dados:** SQLite (fase inicial, simples e sem custo) → migrável para PostgreSQL se o dashboard web for adiante
- **Categorização:** função local por palavras-chave; opcionalmente chamada à API do Claude para descrições ambíguas
- **Hospedagem:** VPS simples, Railway, ou similar (webhook do Telegram precisa de HTTPS)
- **Dashboard (futuro):** aplicação web separada consumindo o mesmo banco, com gráficos (ex: Chart.js) — fora do escopo desta primeira entrega, o comando `/dashboard` pode inicialmente responder "em breve"

---

## 6. Decisões em Aberto

Pontos que valem ser definidos antes de iniciar a implementação:

1. **Entrada de dados:** comando estruturado, linguagem natural, ou conversa guiada passo a passo?
2. **Categorização:** regras fixas por palavra-chave ou uso de IA para classificar automaticamente?
3. **Correção de categoria:** o bot deve perguntar confirmação sempre, ou só quando tiver baixa confiança?
4. **Múltiplas moedas:** o escopo é só R$, ou deve haver espaço para expansão futura?
5. **Multiusuário:** o bot é só para uso pessoal (um único usuário) ou deve suportar múltiplos usuários isolados desde já?
6. **Edição/exclusão:** faz parte da primeira versão ou fica para uma fase 2?

---

## 7. Fora do Escopo (Fase 1)

- Dashboard web completo (apenas o link/placeholder do comando `/dashboard`)
- Metas de gastos e alertas de orçamento
- Integração com contas bancárias/Open Finance
- Relatórios exportáveis (PDF/Excel)

---

## 8. Roadmap Sugerido

| Fase | Entrega |
|---|---|
| 1 | Registro de despesas + categorização + comandos `/diario`, `/semanal`, `/mensal`, `/geral` |
| 2 | Edição/exclusão de gastos, comando `/ajuda`, refinamento de categorização |
| 3 | Dashboard web com gráficos, ativação real do `/dashboard` |
| 4 | Metas de orçamento, alertas, exportação de relatórios |
