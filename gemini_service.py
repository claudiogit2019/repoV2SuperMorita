import os
from groq import Groq
#from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def procesar_voz_completo(audio_bytes, inventario_contexto):
    """
    Transcribe el audio y luego usa Llama para asignar productos y precios del inventario.
    """
    try:
        # 1. Transcripción con Whisper
        with open("temp_audio.wav", "wb") as f:
            f.write(audio_bytes)
        
        with open("temp_audio.wav", "rb") as file:
            transcripcion = client.audio.transcriptions.create(
                file=("temp_audio.wav", file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="es"
            )
        os.remove("temp_audio.wav")

        # 2. Procesamiento con Llama para formato: Producto | Cantidad | Subtotal
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system", 
                    "content": f"""Eres el cajero de Minimercado Morita. 
                    INVENTARIO DISPONIBLE: {inventario_contexto}.
                    TAREA: Según lo que el cliente diga, identifica el producto, la cantidad y calcula el subtotal usando el precio del inventario.
                    FORMATO OBLIGATORIO (una línea por producto): PRODUCTO | CANTIDAD | SUBTOTAL
                    Ejemplo: Coca Cola 1.5L | 2 | 5000"""
                },
                {"role": "user", "content": transcripcion}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"
