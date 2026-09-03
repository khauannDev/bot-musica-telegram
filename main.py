import os
import logging
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Servidor Flask para o Render Web Service
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
        "Envie o nome da música para baixar!",
        parse_mode="Markdown"
    )

def buscar_e_baixar_api(nome_musica):
    # 1. Busca o vídeo via API do Invidious (espelho público do YouTube)
    search_url = f"https://inv.tux.pizza/api/v1/search?q={requests.utils.quote(nome_musica)}&type=video"
    res = requests.get(search_url, timeout=10).json()
    
    if not res or len(res) == 0:
        raise Exception("Nenhuma música encontrada com esse nome.")
    
    video_id = res[0]['videoId']
    titulo = res[0]['title']
    
    # 2. Pega o stream de áudio direto da API do Invidious
    video_data = requests.get(f"https://inv.tux.pizza/api/v1/videos/{video_id}", timeout=10).json()
    
    audio_url = None
    for fmt in video_data.get('adaptiveFormats', []):
        if 'audio' in fmt.get('type', ''):
            audio_url = fmt.get('url')
            break
            
    if not audio_url:
        raise Exception("Não foi possível extrair o link de áudio.")
        
    # 3. Baixa o arquivo de áudio no servidor
    response = requests.get(audio_url, stream=True, timeout=30)
    filename = "musica.mp3"
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                
    return filename, titulo

async def baixar_e_enviar_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text
    mensagem_espera = await update.message.reply_text("⚡ Buscando e baixando a música, aguarde...")

    try:
        arquivo_audio, titulo = buscar_e_baixar_api(texto_usuario)

        if arquivo_audio and os.path.exists(arquivo_audio):
            await mensagem_espera.edit_text("📤 Enviando áudio...")
            with open(arquivo_audio, 'rb') as audio:
                await update.message.reply_audio(audio=audio, title=titulo)
            os.remove(arquivo_audio)
            await mensagem_espera.delete()
        else:
            await mensagem_espera.edit_text("❌ Falha ao salvar o arquivo.")

    except Exception as e:
        await mensagem_espera.edit_text(f"❌ Erro ao baixar:\n`{str(e)}`", parse_mode="Markdown")
        if os.path.exists("musica.mp3"):
            os.remove("musica.mp3")

if __name__ == '__main__':
    Thread(target=run_web).start()

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
    
    print("Bot rodando via API Invidious!")
    app.run_polling()
  
