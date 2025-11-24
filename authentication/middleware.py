import firebase_admin
from firebase_admin import auth as firebase_auth
import time
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

class FirebaseAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Solo aplicar autenticación a rutas API
        if not request.path.startswith('/api/'):
            return None
            
        token = request.headers.get('Authorization', '')
        if token.startswith('Bearer '):
            token = token[7:]  # Remover 'Bearer '
            
            try:
                # Verificar si Firebase está inicializado
                if not firebase_admin._apps:
                    print("Firebase no está inicializado")
                    request.firebase_user_id = None
                    request.firebase_user_role = None
                    request.firebase_user_email = None
                    request.firebase_user = None
                    return None
                    
                decoded_token = firebase_auth.verify_id_token(token)
                request.firebase_user_id = decoded_token['uid']
                request.firebase_user_role = decoded_token.get('role', 'admin')
                request.firebase_user_email = decoded_token.get('email', '')
                request.firebase_user = {
                    'uid': decoded_token['uid'],
                    'email': decoded_token.get('email', ''),
                    'role': decoded_token.get('role', 'admin')
                }
                print(f"Usuario autenticado: {request.firebase_user_email}, Rol: {request.firebase_user_role}")
            except Exception as e:
                err_text = str(e)
                if 'Token used too early' in err_text:
                    try:
                        time.sleep(2)
                        decoded_token = firebase_auth.verify_id_token(token)
                        request.firebase_user_id = decoded_token['uid']
                        request.firebase_user_role = decoded_token.get('role', 'admin')
                        request.firebase_user_email = decoded_token.get('email', '')
                        request.firebase_user = {
                            'uid': decoded_token['uid'],
                            'email': decoded_token.get('email', ''),
                            'role': decoded_token.get('role', 'admin')
                        }
                        print(f"Usuario autenticado (reintento): {request.firebase_user_email}, Rol: {request.firebase_user_role}")
                    except Exception as e2:
                        print(f"Error verificando token Firebase (reintento): {e2}")
                        request.firebase_user_id = None
                        request.firebase_user_role = None
                        request.firebase_user_email = None
                        request.firebase_user = None
                else:
                    print(f"Error verificando token Firebase: {e}")
                    request.firebase_user_id = None
                    request.firebase_user_role = None
                    request.firebase_user_email = None
                    request.firebase_user = None
        else:
            request.firebase_user_id = None
            request.firebase_user_role = None
            request.firebase_user_email = None
            request.firebase_user = None
            
        return None