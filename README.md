# 🏦 Finance Hub

Aplicação de finanças pessoais que importa extratos CSV/OFX, armazena transações no PostgreSQL e oferece categorização e recursos de IA local com Ollama, garantindo **privacidade total** dos dados financeiros sem depender de serviços ou APIs externas na nuvem.

---

## 🎯 Problema & Solução

Aplicativos de finanças pessoais frequentemente exigem o envio de dados bancários sensíveis para servidores de terceiros ou dependem de integrações pagas. O **Finance Hub** resolve esse problema combinando engenharia de dados assíncrona com inferência de IA local:

- **Ingestão Orientada a Eventos (Hot-Folder):** Basta salvar um extrato bancário na pasta `inbox/` para que o sistema o detecte, processe, categorize e arquive automaticamente em `inbox/processed/`.
- **Deduplicação Híbrida:** Garante integridade financeira bloqueando lançamentos repetidos através de hash criptográfico (`SHA-256`) combinado com correspondência aproximada (*Fuzzy Matching* via `rapidfuzz` em janela de `±2 dias`).
- **Copiloto IA Privado (Ollama):** Integração assíncrona com modelos locais (`nous-hermes2:latest`, `qwen2.5-coder`, etc.) que consultam os dados agregados diretamente do PostgreSQL para responder perguntas em linguagem natural e gerar diagnósticos financeiros.

---

## 🏗️ Arquitetura e Stack Tecnológica

- **Linguagem:** Python 3.12
- **API & Assincronismo:** FastAPI + Uvicorn + `httpx`
- **Banco de Dados & ORM:** PostgreSQL 16 (Docker Compose) + SQLAlchemy 2.0 (`asyncpg` / `greenlet`)
- **Monitoramento de Arquivos:** `watchdog` (File System Observer integrado ao ciclo de vida `lifespan` da API)
- **Deduplicação & Categorização:** Regras declarativas YAML + `SHA-256` + `rapidfuzz`
- **IA Local:** Ollama REST API (`/api/generate`)

### Fluxo de Dados

```text
[Extrato .CSV / .OFX]
        │
        ▼ (Drop na pasta inbox/)
[Watchdog File Watcher] ──► [CategorizationService (Regras YAML)]
                                      │
                                      ▼
                     [Deduplicação SHA-256 + Fuzzy Matching]
                                      │
                                      ▼
                        [PostgreSQL 16 (Docker Container)]
                                      │
                                      ▼
                   [FinanceAICopilot (FastAPI + Ollama Local)]
📸 Demonstração em Execução
1. Documentação Interativa (Swagger UI)
Endpoints para categorização rápida, ingestão com persistência, consulta de histórico e interação com o copiloto financeiro:

2. Deduplicação Híbrida em Ação
Ao reenviar um extrato já importado, a camada de integridade identifica e bloqueia 100% das transações duplicadas:

3. Copiloto Financeiro Local (POST /ai/ask)
Consulta em linguagem natural sobre o histórico armazenado no PostgreSQL, processada localmente pelo Ollama sem envio de dados externos:

🚀 Configuração local
Pré-requisitos
Python 3.12+ e uv

Docker e Docker Compose

Ollama instalado e rodando localmente

Passo a passo
Copie .env.example para .env.

No .env, substitua a senha de exemplo por uma senha forte e única. Atualize a senha correspondente em DATABASE_URL e gere SECRET_KEY com:

Bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
(Codifique caracteres especiais da senha para uso na URL do banco).

Baixe o modelo local no Ollama:

Bash
ollama pull nous-hermes2:latest
Instale as dependências com uv sync e inicie o banco com docker compose up -d db:

Bash
uv sync
docker compose up -d db
Inicie a API com uv run uvicorn src.finance.api.main:app --reload:

Bash
uv run uvicorn src.finance.api.main:app --reload --reload-dir src --port 8609
Acesse a documentação interativa em http://127.0.0.1:8609/docs.

⚠️ Atenção: Não publique o arquivo .env nem reutilize os valores de exemplo em produção.

🔒 Privacidade dos dados
Coloque extratos pessoais na pasta inbox/ para importação. O conteúdo de inbox/ é ignorado pelo Git, assim como arquivos CSV, OFX, PDF e bancos de dados locais. Não force a inclusão desses arquivos no repositório; use apenas dados sintéticos em exemplos e testes.

📂 Estrutura do Projeto
Plaintext
banco_py/
├── docs/
│   └── images/                  # Prints da aplicação para documentação
├── inbox/                       # Hot-folder monitorada pelo Watchdog (ignorada no Git)
│   └── processed/               # Extratos já importados e arquivados
├── src/
│   └── finance/
│       ├── api/
│       │   └── main.py          # Rotas FastAPI e ciclo de vida (lifespan)
│       ├── core/
│       │   ├── config.py        # Configurações via Pydantic Settings
│       │   └── database.py      # Engine e sessão assíncrona SQLAlchemy 2.0
│       ├── ingestion/           # Parsers de CSV e OFX
│       ├── models/
│       │   └── transaction.py   # Modelos ORM (Account e Transaction)
│       └── services/
│           ├── ai_copilot.py    # Integração assíncrona com Ollama e contexto SQL
│           ├── categorize.py    # Motor de categorização
│           ├── folder_watcher.py# Watcher de eventos da pasta inbox/
│           └── transaction_service.py # Deduplicação e persistência
├── .env.example                 # Template de variáveis de ambiente
├── docker-compose.yml           # Infraestrutura PostgreSQL 16
├── pyproject.toml / uv.lock     # Gerenciamento de dependências via uv
└── README.md