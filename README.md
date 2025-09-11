# Assistente de Estudos API

Uma API FastAPI para gerenciamento de estudos com funcionalidades de sincronização de tarefas, integração com portal acadêmico e ingestão de arquivos.

## Funcionalidades

- 🔍 **Health Check** - Verificação de saúde da aplicação
- 📝 **Sync de Tarefas** - Sincronização de tarefas em formato JSON
- 🎓 **Portal Acadêmico** - Integração para buscar cronogramas
- 📁 **Upload de Arquivos** - Sistema de ingestão de documentos

## Endpoints

### `GET /healthz`
Verificação de saúde da API.

**Resposta:**
```json
{
  "status": "healthy",
  "service": "Assistente de Estudos API"
}
```

### `POST /todo/sync`
Sincronização de tarefas (JSON).

**Body:**
```json
{
  "tasks": [
    {
      "title": "Título da Tarefa",
      "description": "Descrição opcional",
      "completed": false
    }
  ]
}
```

### `POST /portal/pull_schedule`
Buscar cronograma do portal (Form data).

**Parâmetros:**
- `periodo`: Período acadêmico
- `curso`: Nome do curso
- `instituicao`: Nome da instituição

### `POST /ingest/upload`
Upload de arquivo para ingestão.

**Form data:**
- `arquivo`: Arquivo para upload

## Instalação

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

4. Execute a aplicação:
```bash
python app.py
```

A API estará disponível em `http://localhost:8000`

## Docker

Para executar com Docker:

```bash
# Build da imagem
docker build -t assistente-estudos-api .

# Executar container
docker run -p 8000:8000 assistente-estudos-api
```

## Dependências

- **FastAPI**: Framework web moderno e rápido
- **Uvicorn**: Servidor ASGI
- **Pydantic**: Validação de dados
- **Requests**: Cliente HTTP
- **MSAL**: Autenticação Microsoft
- **python-dotenv**: Gerenciamento de variáveis de ambiente
- **Neo4j**: Driver para banco de dados Neo4j
- **Playwright**: Automação web
- **BeautifulSoup4**: Parser HTML/XML
- **OpenAI**: Cliente para API da OpenAI

## Estrutura do Projeto

```
assistente-estudos-api/
├── app.py              # Aplicação principal FastAPI
├── requirements.txt    # Dependências Python
├── Dockerfile         # Configuração Docker
├── .env.example       # Exemplo de variáveis de ambiente
├── services/          # Módulos de serviços
│   ├── __init__.py
│   └── README.md
└── README.md         # Este arquivo
```

## Desenvolvimento

A pasta `services/` está preparada para receber módulos específicos de cada funcionalidade:

- `auth_service.py` - Serviços de autenticação
- `todo_service.py` - Serviços de gerenciamento de tarefas
- `portal_service.py` - Serviços de integração com portal
- `ingest_service.py` - Serviços de processamento de arquivos