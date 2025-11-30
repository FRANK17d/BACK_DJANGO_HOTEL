from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import LaundryOrder, LaundryStock


def _apply_stock_delta(category, delta_disponible=0, delta_lavanderia=0, delta_danado=0):
    obj, _ = LaundryStock.objects.get_or_create(category=category)
    obj.disponible = max(0, obj.disponible + int(delta_disponible))
    obj.lavanderia = max(0, obj.lavanderia + int(delta_lavanderia))
    obj.danado = max(0, obj.danado + int(delta_danado))
    obj.save()
    return obj


def _now_code():
    return timezone.now().strftime("%Y%m%d%H%M%S")


def _format_datetime(dt):
    if not dt:
        return None
    return dt.isoformat()


@api_view(["GET"])
def stock_list(request):
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    items = []
    for s in LaundryStock.objects.all().order_by('category'):
        # Asegurar que los datos estén sincronizados
        # Calcular disponible correctamente
        calculated_disponible = max(0, s.total - s.lavanderia - s.danado)
        
        # Asegurar que total = disponible + lavanderia + danado
        calculated_total = s.disponible + s.lavanderia + s.danado
        
        # Si hay inconsistencias, corregirlas
        needs_save = False
        if s.disponible != calculated_disponible:
            s.disponible = calculated_disponible
            needs_save = True
        
        # Si el total no coincide, ajustarlo
        if s.total != calculated_total and s.total == 0:
            # Solo ajustar si total es 0 (para no perder datos)
            s.total = calculated_total
            needs_save = True
        elif s.total < calculated_total:
            # Si total es menor que la suma, ajustar total
            s.total = calculated_total
            needs_save = True
        
        if needs_save:
            s.save()
        
        items.append({
            "category": s.category,
            "total": s.total,
            "disponible": s.disponible,
            "lavanderia": s.lavanderia,
            "danado": s.danado,
        })
    return Response({"stock": items})


@api_view(["POST"])
def stock_upsert(request):
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    payload = request.data or {}
    items = payload.get("items") or []
    if not isinstance(items, list):
        return Response({"error": "Formato inválido"}, status=status.HTTP_400_BAD_REQUEST)
    
    updated = []
    for it in items:
        cat = it.get("category")
        if not cat:
            continue
        obj, _ = LaundryStock.objects.get_or_create(category=cat)
        
        # Obtener valores actuales
        current_total = obj.total
        current_lavanderia = obj.lavanderia
        current_danado = obj.danado
        
        # Determinar qué campo se está editando (solo si tiene un valor explícito)
        editing_total = "total" in it and it.get("total") is not None
        editing_disponible = "disponible" in it and it.get("disponible") is not None
        editing_lavanderia = "lavanderia" in it and it.get("lavanderia") is not None
        editing_danado = "danado" in it and it.get("danado") is not None
        
        # Si no se está editando ningún campo, saltar este item
        if not (editing_total or editing_disponible or editing_lavanderia or editing_danado):
            continue
        
        if editing_total:
            # Se está editando el total del inventario
            new_total = max(0, int(it.get("total", 0)))
            obj.total = new_total
            # Disponible se calcula automáticamente: disponible = total - sucias - dañadas
            obj.disponible = max(0, new_total - current_lavanderia - current_danado)
        elif editing_disponible:
            # Se está editando disponible directamente
            new_disponible = max(0, int(it.get("disponible", 0)))
            
            # Validar que disponible no exceda el total actual
            # Si excede, ajustar el total automáticamente
            min_total_required = new_disponible + current_lavanderia + current_danado
            
            if new_disponible > current_total:
                # Si disponible excede el total, ajustar el total automáticamente
                obj.total = min_total_required
            else:
                # Si no excede, mantener el total actual
                obj.total = current_total
            
            obj.disponible = new_disponible
            
            # Validación adicional: asegurar que disponible no exceda el total final
            if obj.disponible > obj.total:
                obj.total = obj.disponible + obj.lavanderia + obj.danado
        elif editing_lavanderia:
            # Se está editando sucias
            new_lavanderia = max(0, int(it.get("lavanderia", 0)))
            obj.lavanderia = new_lavanderia
            # Disponible se calcula automáticamente: disponible = total - sucias - dañadas
            obj.disponible = max(0, current_total - new_lavanderia - current_danado)
            
            # Validar que sucias + dañadas no excedan el total
            if new_lavanderia + current_danado > current_total:
                return Response({
                    "error": f"La suma de sucias ({new_lavanderia}) y dañadas ({current_danado}) no puede exceder el total ({current_total})"
                }, status=status.HTTP_400_BAD_REQUEST)
        elif editing_danado:
            # Se está editando dañadas
            new_danado = max(0, int(it.get("danado", 0)))
            obj.danado = new_danado
            # Disponible se calcula automáticamente: disponible = total - sucias - dañadas
            obj.disponible = max(0, current_total - current_lavanderia - new_danado)
            
            # Validar que sucias + dañadas no excedan el total
            if current_lavanderia + new_danado > current_total:
                return Response({
                    "error": f"La suma de sucias ({current_lavanderia}) y dañadas ({new_danado}) no puede exceder el total ({current_total})"
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validación final: disponible no debe exceder el total
        if obj.disponible > obj.total:
            # Ajustar el total si disponible lo excede
            obj.total = obj.disponible + obj.lavanderia + obj.danado
        
        # Validación: disponible = total - sucias - dañadas (si no se editó disponible directamente)
        if not editing_disponible:
            calculated_disponible = max(0, obj.total - obj.lavanderia - obj.danado)
            if obj.disponible != calculated_disponible:
                obj.disponible = calculated_disponible
        
        # Validación final: asegurar que disponible <= total
        if obj.disponible > obj.total:
            obj.disponible = max(0, obj.total - obj.lavanderia - obj.danado)
        
        obj.save()
        updated.append({
            "category": obj.category,
            "total": obj.total,
            "disponible": obj.disponible,
            "lavanderia": obj.lavanderia,
            "danado": obj.danado,
        })
    return Response({"updated": updated})


@api_view(["POST"])
def send_to_laundry(request):
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    p = request.data or {}
    tg = int(p.get("toalla_grande") or 0)
    tm = int(p.get("toalla_mediana") or 0)
    tc = int(p.get("toalla_chica") or 0)
    sm = int(p.get("sabana_media_plaza") or 0)
    su = int(p.get("sabana_una_plaza") or 0)
    cm = int(p.get("cubrecama_media_plaza") or 0)
    cu = int(p.get("cubrecama_una_plaza") or 0)
    fu = int(p.get("funda") or 0)

    # Validar disponibilidad
    deficits = []
    for cat, qty in [
        ("TOALLAS_GRANDE", tg),
        ("TOALLAS_MEDIANA", tm),
        ("TOALLAS_CHICA", tc),
        ("SABANAS_MEDIA", sm),
        ("SABANAS_UNA", su),
        ("CUBRECAMAS_MEDIA", cm),
        ("CUBRECAMAS_UNA", cu),
        ("FUNDAS", fu),
    ]:
        s, _ = LaundryStock.objects.get_or_create(category=cat)
        if s.disponible < qty:
            deficits.append({"category": cat, "needed": qty, "available": s.disponible})
    
    if deficits:
        return Response({"error": "Stock insuficiente", "deficits": deficits}, status=status.HTTP_400_BAD_REQUEST)

    code = _now_code()
    order = LaundryOrder.objects.create(
        order_code=code,
        toalla_grande=tg,
        toalla_mediana=tm,
        toalla_chica=tc,
        sabana_media_plaza=sm,
        sabana_una_plaza=su,
        cubrecama_media_plaza=cm,
        cubrecama_una_plaza=cu,
        funda=fu,
        status="Enviado",
    )

    # Mover stock a lavandería
    _apply_stock_delta("TOALLAS_GRANDE", -tg, +tg)
    _apply_stock_delta("TOALLAS_MEDIANA", -tm, +tm)
    _apply_stock_delta("TOALLAS_CHICA", -tc, +tc)
    _apply_stock_delta("SABANAS_MEDIA", -sm, +sm)
    _apply_stock_delta("SABANAS_UNA", -su, +su)
    _apply_stock_delta("CUBRECAMAS_MEDIA", -cm, +cm)
    _apply_stock_delta("CUBRECAMAS_UNA", -cu, +cu)
    _apply_stock_delta("FUNDAS", -fu, +fu)

    return Response({
        "order": {
            "order_code": order.order_code,
            "status": order.status,
            "created_at": _format_datetime(order.created_at),
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def return_order(request, order_code):
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        o = LaundryOrder.objects.get(order_code=order_code)
    except LaundryOrder.DoesNotExist:
        return Response({"error": "Orden no encontrada"}, status=status.HTTP_404_NOT_FOUND)
    
    if o.status == "Retornado":
        return Response({"error": "Orden ya retornada"}, status=status.HTTP_400_BAD_REQUEST)

    _apply_stock_delta("TOALLAS_GRANDE", +int(o.toalla_grande or 0), -int(o.toalla_grande or 0))
    _apply_stock_delta("TOALLAS_MEDIANA", +int(o.toalla_mediana or 0), -int(o.toalla_mediana or 0))
    _apply_stock_delta("TOALLAS_CHICA", +int(o.toalla_chica or 0), -int(o.toalla_chica or 0))
    _apply_stock_delta("SABANAS_MEDIA", +int(o.sabana_media_plaza or 0), -int(o.sabana_media_plaza or 0))
    _apply_stock_delta("SABANAS_UNA", +int(o.sabana_una_plaza or 0), -int(o.sabana_una_plaza or 0))
    _apply_stock_delta("CUBRECAMAS_MEDIA", +int(o.cubrecama_media_plaza or 0), -int(o.cubrecama_media_plaza or 0))
    _apply_stock_delta("CUBRECAMAS_UNA", +int(o.cubrecama_una_plaza or 0), -int(o.cubrecama_una_plaza or 0))
    _apply_stock_delta("FUNDAS", +int(o.funda or 0), -int(o.funda or 0))

    o.status = "Retornado"
    o.returned_at = timezone.now()
    o.save()
    
    return Response({
        "ok": True,
        "estado": o.status,
        "fechaRetorno": _format_datetime(o.returned_at)
    })


@api_view(["POST"])
def damage_update(request):
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    p = request.data or {}
    cat = p.get("category")
    qty = int(p.get("quantity") or 0)
    action = (p.get("action") or "add").lower()
    
    s, _ = LaundryStock.objects.get_or_create(category=cat)
    
    if action == "add":
        if s.disponible < qty:
            return Response({"error": "Stock insuficiente"}, status=status.HTTP_400_BAD_REQUEST)
        _apply_stock_delta(cat, -qty, 0, +qty)
    elif action == "repair":
        if s.danado < qty:
            return Response({"error": "Dañado insuficiente"}, status=status.HTTP_400_BAD_REQUEST)
        _apply_stock_delta(cat, +qty, 0, -qty)
    else:
        return Response({"error": "Acción inválida"}, status=status.HTTP_400_BAD_REQUEST)
    
    s.refresh_from_db()
    return Response({
        "category": s.category,
        "disponible": s.disponible,
        "lavanderia": s.lavanderia,
        "danado": s.danado,
    })


@api_view(["GET"])
def list_orders(request):
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    items = []
    for o in LaundryOrder.objects.all()[:50]:
        items.append({
            "order_code": o.order_code,
            "status": o.status,
            "created_at": _format_datetime(o.created_at),
            "returned_at": _format_datetime(o.returned_at),
            "toalla_grande": o.toalla_grande,
            "toalla_mediana": o.toalla_mediana,
            "toalla_chica": o.toalla_chica,
            "sabana_media_plaza": o.sabana_media_plaza,
            "sabana_una_plaza": o.sabana_una_plaza,
            "cubrecama_media_plaza": o.cubrecama_media_plaza,
            "cubrecama_una_plaza": o.cubrecama_una_plaza,
            "funda": o.funda,
        })
    return Response({"orders": items})
