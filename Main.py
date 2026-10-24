import os
import docx
import boto3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN DE CREDENCIALES ---
TELEGRAM_TOKEN = "8950160590:AAFXBcLatWnBSwhKwS6kKhh0DzMviOsjinM"
AWS_ACCESS_KEY = "AKIAVWQLDBPXIJKSO3T6"
AWS_SECRET_KEY = "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"
AWS_REGION = "us-east-1"

# Inicializar cliente de Amazon Polly
polly_client = boto3.client(
    'polly',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Mándame un archivo .docx y lo convertiré en una nota de voz de alta calidad con Amazon Polly."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    
    # Verificar que el archivo sea .docx
    if not document.file_name.endswith('.docx'):
        await update.message.reply_text("Por favor, envía un archivo con formato .docx")
        return

    await update.message.reply_text("Procesando tu documento, dame un momento...")

    file_id = document.file_id
    new_file = await context.bot.get_file(file_id)
    doc_path = f"temp_{document.file_name}"
    await new_file.download_to_drive(doc_path)

    try:
        # Extraer texto del .docx
        doc = docx.Document(doc_path)
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        if not full_text.strip():
            await update.message.reply_text("El documento no contiene texto para leer.")
            return

        # Limitar longitud si excede el máximo de Polly en una llamada
        if len(full_text) > 3000:
            full_text = full_text[:3000]

        # Sintetizar voz con Amazon Polly (Motor Neural)
        response = polly_client.synthesize_speech(
            Engine='neural',
            OutputFormat='mp3',
            Text=full_text,
            VoiceId='Lupe'  # Voz en español
        )

        audio_path = "output_voice.mp3"
        if "AudioStream" in response:
            with open(audio_path, "wb") as f:
                f.write(response["AudioStream"].read())

        # Enviar nota de voz por Telegram
        with open(audio_path, "rb") as audio:
            await update.message.reply_voice(voice=audio)

        # Limpiar archivos temporales
        if os.path.exists(doc_path):
            os.remove(doc_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)

    except Exception as e:
        await update.message.reply_text(f"Ocurrió un error al procesar el archivo: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Bot en marcha...")
    app.run_polling()
