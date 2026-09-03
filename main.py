import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Servidor Flask em segundo plano para o Render Web Service
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot de Música Online 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# Configuração de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *Bot de Música Online!*\n\n"
        "Envie o nome da música ou o link do YouTube para baixar!",
        parse_mode="Markdown"
    )

async def baixar_e_enviar_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text
    mensagem_espera = await update.message.reply_text("⚡ Buscando e baixando a música, aguarde...")

    query = texto_usuario if texto_usuario.startswith("http") else f"ytsearch1:{texto_usuario}"

    # Configuração com bypass para o bloqueio do YouTube em IP de servidor
    ydl_opts = {
        'format': 'ba[ext=m4a]/ba/b',
        'outtmpl': 'musica.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'skip_download_archive': True,
        'no_warnings': True,
        'concurrent_fragment_downloads': 10,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    }

    loop = asyncio.get_running_loop()

    try:
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                
                if 'entries' in info:
                    if not info['entries']:
                        raise Exception("Nenhum vídeo foi encontrado.")
                    info = info['entries'][0]
                    
                return info.get('title', 'Música')

        titulo = await loop.run_in_executor(None, download)
        
        arquivo_audio = None
        for ext in ['.m4a', '.mp3', '.webm', '.ogg']:
            if os.path.exists(f"musica{ext}"):
                arquivo_audio = f"musica{ext}"
                break

        if arquivo_audio:
            await mensagem_espera.edit_text("📤 Enviando áudio...")
            
            with open(arquivo_audio, 'rb') as audio:
                await update.message.reply_audio(audio=audio, title=titulo)

            os.remove(arquivo_audio)
            await mensagem_espera.delete()
        else:
            await mensagem_espera.edit_text("❌ Erro ao localizar o arquivo baixado.")

    except Exception as e:
        await mensagem_espera.edit_text(f"❌ Erro:\n`{str(e)}`", parse_mode="Markdown")
        for ext in ['.m4a', '.mp3', '.webm', '.ogg']:
            if os.path.exists(f"musica{ext}"):
                os.remove(f"musica{ext}")

if __name__ == '__main__':
    Thread(target=run_web).start()

    # SUBSTITUA O TEXTO ABAIXO PELO SEU TOKEN REAL DO BOTFATHER:
    TOKEN = "8933997079:AAFgDr0qTexfVgjYPl6D7ot3W8yI7JZvhfA"
    
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, baixar_e_enviar_musica))
    
    print("Bot Iniciado no Render Web Service!")
    app.run_polling()
              
