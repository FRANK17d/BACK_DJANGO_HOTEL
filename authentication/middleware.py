import firebase_admin
from firebase_admin import auth as firebase_auth
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
                decoded_token = firebase_auth.verify_id_token(token)
                request.firebase_user_id = decoded_token['uid']
                request.firebase_user_role = decoded_token.get('role', 'admin')
                request.firebase_user_email = decoded_token.get('email', '')
            except Exception as e:
                print(f"Error verificando token Firebase: {e}")
                request.firebase_user_id = None
                request.firebase_user_role = None
                request.firebase_user_email = None
        else:
            request.firebase_user_id = None
            request.firebase_user_role = None
            request.firebase_user_email = None
            
        return None