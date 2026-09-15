# MVP Budget API

Componente **secundária** do MVP de controle de assinaturas digitais, desenvolvido para a
disciplina de **Arquitetura de Software** da PUC-Rio.

O serviço mantém as metas de gasto por categoria em banco próprio, avalia o gasto informado pela
API principal contra essas metas e projeta o desembolso dos próximos meses.

## Papel na arquitetura

![Fluxograma da arquitetura do MVP](docs/architecture.png)

A API principal (`mvp-subscription-api`) nunca acessa o banco de metas: toda leitura e escrita passa
por este serviço, por REST, com chave de API própria e o `X-Request-ID` propagado. Se este serviço
ficar indisponível, a principal continua respondendo sem a avaliação de metas.

## Tecnologias

Python 3.13, FastAPI, SQLAlchemy 2 (async, `aiosqlite`), Redis com queda para cache em memória,
pytest e Docker.

## Pré-requisitos

| Ferramenta | Versão |
|---|---|
| [Docker](https://docs.docker.com/get-docker/) + Docker Compose | Docker 24+, Compose v2 |
| [Git](https://git-scm.com/downloads) | qualquer versão recente |
| [Python](https://www.python.org/downloads/) (só para execução local) | 3.13, mínimo 3.10 |

No macOS, o `python3` do sistema é o 3.9 e não instala as dependências. Confira com
`python3 --version` e use `python3.13` se necessário.

## Como executar

### Junto com a componente principal

O `docker-compose.yml` vive na raiz do repositório da componente principal. Clone os dois
repositórios lado a lado e suba o compose de lá:

```bash
git clone https://github.com/vtsouza29/mvp-subscription-api.git
git clone https://github.com/vtsouza29/mvp-budget-api.git
cd mvp-subscription-api
docker compose up --build
```

Este serviço fica em <http://localhost:8001/docs>.

### Somente esta componente

```bash
docker build -t mvp-budget-api .
docker run --rm -p 8000:8000 -e API_KEY=minha-chave -e SEED_ON_STARTUP=true mvp-budget-api
```

Sobe sem depender de Redis nem de outro container. Documentação em <http://localhost:8000/docs>.

### Execução local

```bash
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
python -m seeds.seed               # metas de demonstração, idempotente
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `API_KEY` | `budget-local-dev-key` | Chave exigida no cabeçalho `X-API-Key`. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/budget.db` | Banco do serviço. |
| `REDIS_URL` | vazio | Se ausente ou inacessível, o cache usa memória. |
| `CACHE_TTL_SECONDS` | `900` | Validade das respostas cacheadas. |
| `SEED_ON_STARTUP` | `false` | Cria metas sintéticas no start. |
| `LOG_LEVEL` | `INFO` | Nível de log. |

## Rotas

Todas as rotas de negócio exigem o cabeçalho `X-API-Key`. A rota `/health` é aberta.

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/budgets` | Cria a meta de uma categoria. |
| `GET` | `/api/v1/budgets` | Lista com filtro, ordenação e paginação. |
| `GET` | `/api/v1/budgets/{id}` | Consulta uma meta. |
| `PUT` | `/api/v1/budgets/{id}` | Substitui uma meta. |
| `DELETE` | `/api/v1/budgets/{id}` | Remove uma meta. |
| `POST` | `/api/v1/evaluations` | Avalia o gasto informado contra as metas. |
| `POST` | `/api/v1/projections` | Projeta o desembolso dos próximos meses. |
| `GET` | `/health` | Saúde do serviço e de suas dependências. |

Exemplo de avaliação:

```bash
curl -X POST http://localhost:8001/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: minha-chave" \
  -d '{
    "reference_month": "2026-09",
    "spending": [
      {"category": "STREAMING", "monthly_amount_brl": 45.90},
      {"category": "SAAS", "monthly_amount_brl": 240.00}
    ]
  }'
```

## Regras de negócio

**Classificação** por categoria, com `usage_pct = gasto / limite × 100`:

| Situação | Status |
|---|---|
| acima de 100% | `EXCEEDED` |
| a partir do `alert_threshold_pct` | `ALERT` |
| demais casos | `OK` |

O status consolidado é o pior status individual. Categorias com gasto informado e sem meta ativa
voltam em `unbudgeted_categories`. Metas inativas ficam fora da avaliação.

**Projeção.** Cada assinatura é distribuída nos meses em que é efetivamente cobrada, respeitando os
ciclos mensal, trimestral e anual. Uma data de renovação anterior à janela é avançada em ciclos
inteiros, de modo que um plano anual renovado em março continua caindo em março.

**Cache.** As duas rotas `POST` são cacheadas. A chave da avaliação inclui uma assinatura do
conjunto de metas, então alterar qualquer meta invalida as avaliações anteriores. A resposta traz
`cached` com a origem do resultado. Sem Redis, o serviço usa cache em processo e reporta `degraded`
no `/health`.

## Testes

```bash
pytest
```

## Estrutura

```
app/
├── main.py            # criação da aplicação e ciclo de vida
├── config.py          # settings via variáveis de ambiente
├── database.py        # engine, sessão e criação do schema
├── security.py        # autenticação por API key
├── core/              # enums, cache, erros, correlação, tipos
├── models/            # mapeamento ORM do agregado Budget
├── schemas/           # contratos de entrada e saída
├── repositories/      # acesso a dados
├── routers/           # rotas HTTP
└── services/          # regras de negócio
seeds/                 # dados sintéticos idempotentes
tests/                 # testes automatizados
```

## Repositórios do MVP

| Componente | Repositório |
|---|---|
| Principal, `mvp-subscription-api` | https://github.com/vtsouza29/mvp-subscription-api |
| Secundária, `mvp-budget-api` (esta) | https://github.com/vtsouza29/mvp-budget-api |

A documentação da API externa (Frankfurter) fica no repositório da componente principal, junto com
o `docker-compose.yml`.

## Licença

MIT.
