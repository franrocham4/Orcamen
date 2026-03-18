# Orcamen — Controle de Pagamento 2025

Sistema Django automatizado para monitoramento e visualização da planilha **CONTROLE DE PAGAMENTO 2025.xlsm**.

## Funcionalidades

- 📊 **Dashboard** com todas as abas e dados da planilha em tempo real
- 🔄 **Sincronização automática** via Watchdog (monitora a pasta local)
- ⚡ **Celery + Redis** para processamento assíncrono em background
- 🗄️ **API REST** completa com Django REST Framework
- 🐳 **Docker Compose** para deploy fácil
- 🔍 **Busca e paginação** em todas as tabelas

## Início Rápido (sem Docker)

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Copiar e editar configurações
cp .env.example .env
# Edite WATCH_FOLDER com o caminho da sua pasta

# 3. Criar banco de dados e importar planilha
python manage.py migrate
python manage.py seed_excel

# 4. Criar superusuário (opcional)
python manage.py createsuperuser

# 5. Rodar o servidor
python manage.py runserver

# Em outro terminal — Celery (opcional, para processamento em background)
celery -A config worker -l info
```

Acesse: **http://localhost:8000/dashboard/**

## Com Docker

```bash
# Copiar .env e ajustar WATCH_FOLDER
cp .env.example .env

# Subir todos os serviços
docker-compose up

# Acesse http://localhost:8000/dashboard/
```

## Configuração (.env)

| Variável | Padrão | Descrição |
|---|---|---|
| `WATCH_FOLDER` | `C:\Users\danielcoelho\Desktop\Pasta` | Pasta monitorada |
| `EXCEL_FILENAME` | `CONTROLE DE PAGAMENTO 2025.xlsm` | Nome do arquivo |
| `SECRET_KEY` | (dev key) | Chave secreta Django |
| `DEBUG` | `True` | Modo debug |
| `REDIS_URL` | `redis://localhost:6379/0` | URL do Redis |
| `DATABASE_URL` | SQLite | URL do banco de dados |

## Estrutura

```
├── manage.py
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
└── apps/
    ├── core/              # Modelos: ExcelFile, ExcelSheet, ExcelRow, SyncHistory
    ├── excel_processor/   # Processador, Monitor (Watchdog), Tasks Celery, API
    └── dashboard/         # Views, Templates, URLs do dashboard
```

## API REST

| Endpoint | Descrição |
|---|---|
| `GET /api/files/` | Lista arquivos Excel |
| `GET /api/sheets/` | Lista abas |
| `GET /api/rows/?sheet=<id>` | Lista linhas de uma aba |
| `GET /api/sync/` | Histórico de sincronizações |
| `POST /api/sync/sincronizar_agora/` | Força sincronização manual |

## Monitoramento Automático

O sistema usa **Watchdog** para monitorar a pasta configurada em `WATCH_FOLDER`.
Quando detecta uma alteração em arquivo `.xlsx` ou `.xlsm`, dispara automaticamente
uma task Celery para processar e atualizar o banco de dados.

O dashboard atualiza automaticamente via polling a cada 5 segundos.
