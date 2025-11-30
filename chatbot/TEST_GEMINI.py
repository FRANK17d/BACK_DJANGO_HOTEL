# Script de prueba para verificar la configuracion de Gemini
# Ejecutar desde el shell de Django: exec(open('chatbot/TEST_GEMINI.py', encoding='utf-8').read())

import os
import google.generativeai as genai
from django.conf import settings

# Obtener API key
api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')

if not api_key:
    print("ERROR: GEMINI_API_KEY no esta configurada")
    print("Configurala en settings.py o como variable de entorno")
else:
    print(f"API Key encontrada: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Configurar Gemini
        genai.configure(api_key=api_key)
        print("Gemini configurado correctamente")
        
        # Probar modelo (intentar varios modelos en orden)
        models_to_try = [
            'gemini-2.5-flash',
            'gemini-2.5-flash-exp',
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro'
        ]
        
        model = None
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                print(f"Modelo '{model_name}' disponible")
                break
            except Exception as e:
                print(f"Modelo '{model_name}' no disponible: {e}")
                continue
        
        if model is None:
            print("ERROR: No se pudo inicializar ningun modelo")
            raise Exception("No hay modelos disponibles")
        
        # Probar generacion de contenido
        print("\nProbando generacion de contenido...")
        response = model.generate_content("Di 'Hola' en espanol")
        print(f"Respuesta recibida: {response.text}")
        print("\nTodo funciona correctamente!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

