import os
import logging
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Servidor Flask em segundo plano
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot de Música Online 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *Bot de Música Online!*\n\n"
        "Envie o link do YouTube/SoundCloud ou o nome da música para baixar!",
        parse_mode="Markdown"
    )

def obter_link_youtube_por_busca(query_texto):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch1'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query_texto, download=False)
        if 'entries' in info and len(info['entries']) > 0:
            return info['entries'][0]['webpage_url'], info['entries'][0].get('title', 'Música')
        elif 'webpage_url' in info:
            return info['webpage_url'], info.get('title', 'Música')
    return None, None

def baixar_via_cobalt(url_video):
    # API pública do Cobalt para burlar qualquer restrição do YouTube
    endpoint = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url_video,
        "downloadMode": "audio",
        "audioFormat": "mp3"
    }
    
    response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
    data = response.json()
    
    if data.get("status") in ["tunnel", "redirect"]:
        audio_url = data.get("url")
        audio_req = requests.get(audio_url, stream=True)
        filename = "musica.mp3"
        with open(filename, 'wb') as f:
            for chunk in audio_req.iter_content(chunk_size=8192):
                f.write(chunk)
        return filename
    else:
        raise Exception(data.get("text", "Erro na API do Cobalt"))

async def baixar_e_enviar_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text
    mensagem_espera = await update.message.reply_text("⚡ Processando e baixando o áudio...")

    try:
        # Se for texto, obtém o URL do vídeo primeiro
        if texto_usuario.startswith("http"):
            url = texto_usuario
            titulo = "Música"
        else:
            url, titulo = obter_link_youtube_por_busca(texto_usuario)
            if not url:
                await mensagem_espera.edit_text("❌ Nenhuma música encontrada.")
                return

        # Baixa o áudio usando o servidor do Cobalt
        arquivo_audio = baixar_via_cobalt(url)

        if arquivo_audio and os.path.exists(arquivo_audio):
            await mensagem_espera.edit_text("📤 Enviando áudio...")
            with open(arquivo_audio, 'rb') as audio:
                await update.message.reply_audio(audio=audio, title=titulo)
            os.remove(arquivo_audio)
            await mensagem_espera.delete()
        else:
            await mensagem_espera.edit_text("❌ Falha ao salvar o arquivo de áudio.")

    except Exception as e:
        await mensagem_espera.edit_text(f"❌ Erro:\n`{str(e)}`", parse_mode="Markdown")
        if os.path.exists("musica.mp3"):
            os.remove("musica.mp3")

if __name__ == '__main__':
    Thread(target=run_web).start()

    # SEU TOKEN DO TELEGRAM:
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
    
    print("Bot com Cobalt API Iniciado!")
    app.run_polling()
                                 
