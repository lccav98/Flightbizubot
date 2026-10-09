# ✈️ Flight Bizu Bot (@Flightbizubot)

[![Telegram Bot](https://img.shields.io/badge/Telegram-@Flightbizubot-blue?logo=telegram&style=for-the-badge)](https://t.me/Flightbizubot)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white&style=for-the-badge)](https://python.org)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white&style=for-the-badge)](https://docker.com)
[![Status 24/7](https://img.shields.io/badge/Operação-24%2F7-brightgreen?style=for-the-badge)](#-execu%C3%A7%C3%A3o-247)

> **Radar autônomo 24/7 de passagens aéreas e locação de veículos.**  
> Monitora tarifas com até 12 meses de antecedência, identifica feirões relâmpago e envia alertas em tempo real no Telegram para **qualquer pessoa que acesse o bot**.

🔗 **Acesse o Bot diretamente no Telegram:**  
👉 **[@Flightbizubot](https://t.me/Flightbizubot)** *(ou [web.telegram.org/k/#@Flightbizubot](https://web.telegram.org/k/#@Flightbizubot))*

---

## 🎯 O que o Flight Bizu Bot faz?

- 🔍 **Varredura Contínua (Ida e Volta):** Monitora 12 rotas estratégicas com foco em Curitiba (PR), destinos nacionais (GIG, POA, JPA, FOR, URG, BVB, GEL) e internacionais (JFK, MIA, MAD, LIS, CDG).
- 📅 **Calendário Flexível (6 a 12 meses):** Analisa dias com menor probabilidade tarifária (terças, quartas e finais de semana) em múltiplos meses futuros.
- 🚗 **Cotações de Aluguel de Carros:** Links diretos e estimativas de diárias para todos os destinos no Rentcars, Booking e Kayak.
- 🔥 **Rastreador de Feirões e Notícias:** Captura promoções relâmpago de feeds especializados (Melhores Destinos, Passagens Imperdíveis, etc.).
- 👥 **Multi-Usuário Instantâneo:** Qualquer usuário que entrar pelo link e der `/start` é cadastrado automaticamente para receber notificações e consultar tarifas sob demanda.

---

## 📱 Comandos Disponíveis no Telegram

| Comando | Descrição |
|---|---|
| `/start` ou `/ajuda` | Boas-vindas, menu de ajuda e inscrição automática nos alertas |
| `/menores` | Exibe as menores tarifas históricas já registradas (Ida e Volta) |
| `/carros` | Cotações e links diretos para aluguel de veículos nos destinos |
| `/promos` | Feirões de passagens e notícias de promoções relâmpago recentes |
| `/buscar` | Dispara uma varredura manual imediata e envia relatório consolidado |
| `/alertas on` / `/alertas off` | Ativa ou pausa o recebimento de alertas automáticos 24/7 |
| `/status` | Exibe uptime, total de usuários inscritos e integridade do banco |

---

## 📍 Trechos Monitorados

1. **Boa Vista - RR (BVB) ➔ Curitiba - PR (CWB)**
2. **Curitiba - PR (CWB) ➔ Rio de Janeiro - RJ (SDU/GIG)**
3. **Curitiba - PR (CWB) ➔ Porto Alegre - RS (POA)**
4. **Curitiba - PR (CWB) ➔ Uruguaiana - RS (URG)**
5. **Curitiba - PR (CWB) ➔ João Pessoa - PB (JPA)**
6. **Curitiba - PR (CWB) ➔ Fortaleza - CE (FOR)**
7. **Curitiba - PR (CWB) ➔ Nova Iorque - EUA (JFK/EWR)**
8. **Curitiba - PR (CWB) ➔ Miami - EUA (MIA)**
9. **Curitiba - PR (CWB) ➔ Madrid - ESP (MAD)**
10. **Curitiba - PR (CWB) ➔ Lisboa - POR (LIS)**
11. **Curitiba - PR (CWB) ➔ Paris - FRA (CDG/ORY)**
12. **Curitiba - PR (CWB) ➔ Santo Ângelo - RS (GEL)**

---

## 🚀 Como Colocar para Funcionar 24/7

### Opção A: Nuvem (Deploy Gratuito 24/7)

O repositório já inclui `Dockerfile` e `docker-compose.yml` prontos para deploy contínuo em serviços de nuvem gratuitos ou de baixo custo:

#### 1. No Railway / Render / Koyeb / Fly.io:
1. Faça Fork ou conecte este repositório no seu painel.
2. Defina as variáveis de ambiente:
   - `TELEGRAM_BOT_TOKEN`: Token gerado com [@BotFather](https://t.me/BotFather)
   - `SCAN_INTERVAL_MINUTES`: `60` (ou frequência desejada)
   - `DISCOUNT_THRESHOLD_PERCENT`: `20`
   - `MONTHS_AHEAD`: `10`
   - `DB_PATH`: `/app/data/radar_viagens.db`
3. O serviço executará o `Dockerfile` e o bot estará online 24 horas por dia, 7 dias por semana.

#### 2. Com Docker Compose (VPS / Servidor):
```bash
docker compose up -d --build
```

---

### Opção B: Localmente no Windows (24/7 em Segundo Plano)

Se preferir rodar no seu próprio computador Windows:

1. **Clone o repositório:**
   ```powershell
   git clone https://github.com/lccav98/Flightbizubot.git
   cd Flightbizubot
   ```

2. **Crie o `.env` baseado no `.env.example`:**
   ```powershell
   copy .env.example .env
   ```
   *(Preencha seu `TELEGRAM_BOT_TOKEN`)*

3. **Instale as dependências:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Inicie em segundo plano (invisível):**
   - Dê dois cliques em `start_background.vbs`. O bot rodará silenciosamente.
   - Para parar quando quiser: execute `stop_background.bat`.
   - Para iniciar automaticamente ao ligar o Windows: execute `install_startup.bat`.

---

## 🛠️ Arquitetura do Projeto

```
Flightbizubot/
├── main.py                  # Ponto de entrada e CLI de operações
├── scheduler.py             # Agendador 24/7 e processador de comandos Telegram
├── telegram_notifier.py     # Gestão da API Telegram (broadcast e respostas privadas)
├── flight_engine.py         # Motor de busca e análise de tarifas aéreas
├── car_engine.py            # Motor de cotações e links de aluguel de veículos
├── promo_engine.py          # Monitor de feeds RSS de feirões e promoções
├── database.py              # Camada SQLite com persistência e multi-usuário
├── config.py                # Configurações de rotas, limites e alertas
├── requirements.txt         # Dependências do projeto
├── Dockerfile               # Container para deploy 24/7
├── docker-compose.yml       # Orquestração do container com volume persistente
├── start_background.vbs     # Inicialização invisível no Windows
├── stop_background.bat      # Encerramento do processo no Windows
└── install_startup.bat      # Inicialização automática no boot do Windows
```

---

## 🔒 Segurança

- **NUNCA** faça commit do seu arquivo `.env` nem exponha o seu `TELEGRAM_BOT_TOKEN`. O arquivo `.gitignore` deste projeto já está configurado para evitar vazamentos acidentais.
- O banco de dados SQLite armazena apenas dados públicos de tarifas e os `chat_id` dos usuários que deram `/start` no bot para receber alertas.

---

## 📄 Licença

Distribuído sob licença MIT. Veja `LICENSE` para mais informações.
