import os
import io
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

# VOZ MASCULINA: 'Andres' (Neural - Es-MX) o 'Pedro' (Neural - Es-US)
VOICE_ID = 'Andres'

def split_text(text, max_length=2500):
    """Divide el texto en partes menores a max_length sin cortar oraciones."""
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 <= max_length:
            current_chunk += paragraph + "\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Envíame un archivo .docx completo y lo convertiré en notas de voz con voz masculina usando Amazon Polly."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    
    if not document.file_name.endswith('.docx'):
        await update.message.reply_text("Por favor, envía un archivo con formato .docx")
        return

    await update.message.reply_text("Procesando tu documento completo. Esto puede tomar un par de minutos según la longitud...")

    file_id = document.file_id
    new_file = await context.bot.get_file(file_id)
    doc_path = f"temp_{document.file_name}"
    await new_file.download_to_drive(doc_path)

    try:
        doc = docx.Document(doc_path)
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        if not full_text.strip():
            await update.message.reply_text("El documento no contiene texto para leer.")
            return

        # Dividir texto en fragmentos para Polly
        chunks = split_text(full_text)
        total_chunks = len(chunks)

        combined_audio = io.BytesIO()

        for i, chunk in enumerate(chunks):
            response = polly_client.synthesize_speech(
                Engine='neural',
                OutputFormat='mp3',
                Text=chunk,
                VoiceId=VOICE_ID
            )
            if "AudioStream" in response:
                combined_audio.write(response["AudioStream"].read())

        combined_audio.seek(0)
        audio_path = "output_voice_full.mp3"
        with open(audio_path, "wb") as f:
            f.write(combined_audio.read())

        # Enviar audio final
        with open(audio_path, "rb") as audio:
            await update.message.reply_voice(voice=audio)

        # Limpiar archivos
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
