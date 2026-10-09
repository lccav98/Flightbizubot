"""
Script interativo para detectar automaticamente o Chat ID e testar o Bot do Telegram.
"""
import sys
import time
import re
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def update_env_file(token: str, chat_id: str):
    env_path = ".env"
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    # Substitui ou adiciona TELEGRAM_BOT_TOKEN
    if "TELEGRAM_BOT_TOKEN=" in content:
        content = re.sub(r"TELEGRAM_BOT_TOKEN=.*", f"TELEGRAM_BOT_TOKEN={token}", content)
    else:
        content += f"\nTELEGRAM_BOT_TOKEN={token}"

    # Substitui ou adiciona TELEGRAM_CHAT_ID
    if "TELEGRAM_CHAT_ID=" in content:
        content = re.sub(r"TELEGRAM_CHAT_ID=.*", f"TELEGRAM_CHAT_ID={chat_id}", content)
    else:
        content += f"\nTELEGRAM_CHAT_ID={chat_id}"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    print("=" * 60)
    print("🤖 CONFIGURAÇÃO AUTOMÁTICA DO TELEGRAM - RADAR DE VIAGENS")
    print("=" * 60)
    print()

    token = input("Cole a sua API KEY (Token do BotFather) e pressione ENTER:\n> ").strip()
    if not token:
        print("\n❌ Nenhum token informado. Operação cancelada.")
        return

    # 1. Valida o token e pega informações do bot
    print("\n🔍 Verificando token com os servidores do Telegram...")
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"https://api.telegram.org/bot{token}/getMe")
            if r.status_code != 200:
                print(f"❌ Token inválido ou não reconhecido: {r.status_code} - {r.text}")
                return
            bot_info = r.json().get("result", {})
            bot_name = bot_info.get("first_name", "Bot")
            bot_username = bot_info.get("username", "")
    except Exception as e:
        print(f"❌ Erro de conexão com o Telegram: {e}")
        return

    print(f"✅ Bot encontrado: {bot_name} (@{bot_username})")
    print()
    print("=" * 60)
    print(f"👉 AGORA, ABRA O TELEGRAM E ENVIE UMA MENSAGEM PARA O SEU BOT:")
    print(f"   Link direto: https://t.me/{bot_username}")
    print("   (Basta clicar em 'Iniciar' ou enviar 'Oi' ou '/start')")
    print("=" * 60)
    print("\n⏳ Aguardando sua mensagem no Telegram (verificando a cada 2 segundos)...")

    # 2. Polling de updates para capturar o chat_id
    chat_id = None
    user_name = ""
    for _ in range(60):  # tenta por até 2 minutos
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(f"https://api.telegram.org/bot{token}/getUpdates")
                if r.status_code == 200:
                    updates = r.json().get("result", [])
                    if updates:
                        # Pega o update mais recente
                        last_update = updates[-1]
                        msg = last_update.get("message") or last_update.get("channel_post") or {}
                        sender = msg.get("from") or {}
                        chat = msg.get("chat") or {}
                        chat_id = str(chat.get("id", ""))
                        user_name = sender.get("first_name") or chat.get("first_name") or "Viajante"
                        if chat_id:
                            break
        except Exception:
            pass
        time.sleep(2)
        print(".", end="", flush=True)

    print()
    if not chat_id:
        print("\n⚠️ Nenhuma mensagem recebida nos últimos 2 minutos.")
        print("Certifique-se de que clicou no link e enviou uma mensagem para o bot, depois execute novamente.")
        return

    print(f"\n🎉 SUCESSO! Mensagem recebida de: {user_name} (Chat ID: {chat_id})")

    # 3. Salva no .env
    update_env_file(token, chat_id)
    print("💾 Configurações salvas automaticamente no arquivo .env!")

    # 4. Envia mensagem de teste de confirmação para o Telegram do usuário
    try:
        welcome_text = (
            f"🎉 <b>Olá, {user_name}! Conexão estabelecida com sucesso!</b>\n\n"
            "✈️ Seu <b>Radar de Viagens & Veículos 24/7</b> está pronto para monitorar seus trechos.\n\n"
            "Comandos que você pode testar agora:\n"
            "• /buscar - Fazer uma varredura de tarifas\n"
            "• /carros - Cotações de locação de veículos\n"
            "• /status - Ver status do monitoramento\n"
            "• /ajuda - Menu completo"
        )
        with httpx.Client(timeout=10.0) as client:
            client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": welcome_text,
                    "parse_mode": "HTML"
                }
            )
        print("📨 Mensagem de teste enviada para o seu Telegram com sucesso!")
    except Exception as e:
        print(f"⚠️ Erro ao enviar mensagem de teste: {e}")

    print("\n✅ TUDO PRONTO! Agora você já pode iniciar o agente dando dois cliques em 'run.bat' ou 'start_background.vbs'.")

if __name__ == "__main__":
    main()
