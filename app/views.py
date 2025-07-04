import datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Event, User, Ticket, Comment, Notification, Venue, Discount, RefundRequest, Rating, Category, SatisfactionSurvey
from django.contrib import messages
from django.db.models import Q
import uuid
from urllib.parse import unquote
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from urllib.parse import unquote
import json

def is_organizer(user):
    return user.is_organizer


def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        username = request.POST.get("username")
        is_organizer = request.POST.get("is-organizer") is not None
        password = request.POST.get("password")
        password_confirm = request.POST.get("password-confirm")

        errors = User.validate_new_user(email, username, password, password_confirm)

        if len(errors) > 0:
            return render(
                request,
                "accounts/register.html",
                {
                    "errors": errors,
                    "data": request.POST,
                },
            )
        else:
            user = User.objects.create_user(
                email=email, username=username, password=password, is_organizer=is_organizer
            )
            login(request, user)
            return redirect("events")

    return render(request, "accounts/register.html", {})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(
                request, "accounts/login.html", {"error": "Usuario o contraseña incorrectos"}
            )

        login(request, user)
        return redirect("events")

    return render(request, "accounts/login.html")


def home(request):
    return render(request, "home.html")


@login_required
def events(request):
    current_time = timezone.now()
    events = Event.objects.filter(scheduled_at__gt=current_time).order_by("scheduled_at")
    for ev in events:
        ev.auto_update_state()  # Actualizar el estado de cada evento
    return render(
        request,
        "app/events.html",
        {"events": events, "user_is_organizer": request.user.is_organizer},
    )


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    event.auto_update_state()  # Actualizar el estado del evento
    user_has_rated = False
    
    if request.user.is_authenticated:
        user_has_rated = event.ratings.filter(user=request.user).exists()
    
    return render(
        request,
        "app/event_detail.html",
        {
            "event": event,
            "user_is_organizer": request.user.is_organizer,
            "user_has_rated": user_has_rated
        },
    )


@login_required
def event_delete(request, event_id):
    user = request.user
    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        event = get_object_or_404(Event, pk=event_id)
        event.delete()
        return redirect("events")

    return redirect("events")

@login_required
def event_canceled(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    user = request.user
    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        event = get_object_or_404(Event, pk=event_id)
        event.state = Event.CANCELED
        event.save()
        return redirect("events")

    return redirect("events")


@login_required
def event_form(request, event_id=None):
    user = request.user

    if not user.is_organizer:
        return redirect("events")

    venues = Venue.objects.all()
    categories = Category.objects.filter(is_active=True)
    event = None # Inicializa event para que siempre exista

    if event_id is not None:
        event = get_object_or_404(Event, pk=event_id)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        venue_id = request.POST.get("venue")
        category_id = request.POST.get("category")
        date = request.POST.get("date")
        time = request.POST.get("time")

        if not all([title, description, venue_id, date, time]):
            messages.error(request, "Todos los campos son obligatorios")
            return render(request, "app/event_form.html", {
                "event": event,
                "categories": categories,
                "venues": venues,
                "user_is_organizer": request.user.is_organizer,
                "data": request.POST
            })

        try:
            venue = get_object_or_404(Venue, pk=venue_id)
            category = get_object_or_404(Category, pk=category_id) if category_id else None
            [year, month, day] = date.split("-")
            [hour, minutes] = time.split(":")

            scheduled_at = timezone.make_aware(
                datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
            )

            #Logica de Creacion 
            if event_id is None:
                success, result = Event.new(
                    title=title,
                    description=description,
                    scheduled_at=scheduled_at,
                    organizer=request.user,
                    venue=venue,
                    category=category
                )
                if success:
                    # El evento se crea exitosamente
                    messages.success(request, "Evento creado exitosamente")
                    return redirect("events")
                else:
                    # Manejo de errores para la creacion
                    messages.error(request, f"Error al crear el evento: {result}") # Mensaje corregido
                    return render(request, "app/event_form.html", {
                        "event": event, # event aqui es None, o el original si es edición fallida
                        "categories": categories,
                        "venues": venues,
                        "user_is_organizer": request.user.is_organizer,
                        "errors": result,
                        "data": request.POST
                    })
            else:
                ##aca se actualiza el evento
                old_scheduled_at = event.scheduled_at
                old_venue = event.venue
                success, result = event.update(
                    title = title,
                    description = description,
                    scheduled_at = scheduled_at,
                    venue = venue,
                    category=category
                )

                if success:
                    messages.success(request, "Evento actualizado exitosamente")
                    if event is not None:
                        event.create_notification_on_event_update(old_scheduled_at, old_venue)
                    return redirect("events")

                else:
                    messages.error(request, f"Error al actualizar el evento: {result}")
                    return render(
                        request, "app/event_form.html",{
                            "event": event,
                            "categories": categories, # Estas son las categorías para el formulario
                            "venues": venues,
                            "user_is_organizer": request.user.is_organizer,
                            "errors": result,
                            "data": request.POST
                        })
        except (ValueError, TypeError) as e: # Captura errores de formato de fecha/hora o get_object_or_404
            messages.error(request, f"Error en el formato de datos o al encontrar el recurso: {e}")
            return render(request, "app/event_form.html", {
                "event": event,
                "categories": categories, # Estas son las categorías generales, no las seleccionadas
                "venues": venues,
                "user_is_organizer": request.user.is_organizer,
                "data": request.POST
            })

    # Si la solicitud no es POST, se muestra el formulario vacío o pre-llenado
    else:
        # Aquí puedes pre-llenar el formulario si 'event' existe (modo edición)
        initial_data = {}
        if event:
            # Asegúrate de formatear la fecha/hora para el input HTML (datetime-local)
            if event.scheduled_at:
                # Si scheduled_at es un campo DateTimeField aware (con USE_TZ=True),
                # es mejor usar `isoformat` o `strftime` con el formato correcto.
                # Ejemplo para input type="datetime-local": "YYYY-MM-DDTHH:MM"
                initial_scheduled_at = event.scheduled_at.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%dT%H:%M")
            else:
                initial_scheduled_at = ""

            initial_category_id = event.category.id if event.category else ""
            # Si event.categories es ManyToMany, necesitarías:
            # initial_category_ids = [c.id for c in event.categories.all()]

            initial_data = {
                "title": event.title,
                "description": event.description,
                "venue": event.venue.id if event.venue else "",
                "category": initial_category_id, # Para un solo select
                # "category": initial_category_ids, # Para un multi-select
                "date": event.scheduled_at.strftime("%Y-%m-%d") if event.scheduled_at else "",
                "time": event.scheduled_at.strftime("%H:%M") if event.scheduled_at else "",
                # 'scheduled_at' es mejor para un input type="datetime-local"
                "scheduled_at_datetime_local": initial_scheduled_at,
            }

        return render(request, "app/event_form.html", {
            "event": event,
            "categories": categories,
            "venues": venues,
            "user_is_organizer": request.user.is_organizer,
            "data": initial_data # Pasar los datos iniciales
        })


    return render(
        request,
        "app/event_form.html",
        {
            "event": event,
            "categories": categories,
            "venues": venues,
            "user_is_organizer": request.user.is_organizer,
        },
    )


@login_required
def refund_form(request, id):
    ticket = get_object_or_404(Ticket, pk=id)

    if request.method == "POST":
        ticket_code = request.POST.get("ticket_code")
        reason = request.POST.get("reason")
        additional_details = request.POST.get("additional_details")
        accepted_policy = request.POST.get("accepted_policy") == "on"

        # Validaciones básicas
        if not ticket_code or not reason or not accepted_policy:
            return render(request, "app/refund_form.html", {
                "error": "Todos los campos son obligatorios.",
                "data": request.POST
            })
        
        #Validacion para evitar que haya solicitudes de reembolso duplicadas
        existing_request = RefundRequest.objects.filter(
            user=request.user,
            ticket_code=ticket_code,
            approval__isnull=True,  # Reembolso todavia pendientes
        ).first()

        if existing_request:
            return render(request, "app/refund_form.html",{
                "error": "Ya tienes una solicitud de reembolso pendiente.",
                "data": request.POST
            })

        # Crear la solicitud de reembolso con estado pendiente
        RefundRequest.objects.create(
            ticket_code=ticket_code,
            reason=reason,
            additional_details=additional_details,
            user=request.user,
            accepted_policy=accepted_policy,
            approval=None,  # Estado pendiente
            event_name=ticket.event.title
        )

        # Crear una notificación para el usuario que solicitó el reembolso
        notification = Notification.objects.create(
            title="Solicitud de Reembolso Enviada",
            message=f"Tu solicitud de reembolso para el evento: '{ticket.event.title}' ha sido enviada y está en proceso de revisión.",
            priority="MEDIUM"
        )
        notification.users.add(request.user)
        notification.save()

        return redirect("tickets")

    return render(request, "app/refund_form.html", {"ticket": ticket})


@login_required
def refund_edit_form(request, id):
    refund_request = get_object_or_404(RefundRequest, pk=id)

    if request.method == "POST":
        ticket_code_uuid = uuid.UUID(refund_request.ticket_code)
        ticket = Ticket.objects.get(ticket_code=ticket_code_uuid, user=refund_request.user)

        ticket_code = request.POST.get("ticket_code")
        reason = request.POST.get("reason")
        additional_details = request.POST.get("additional_details")
        accepted_policy = request.POST.get("accepted_policy") == "on"

        # Validaciones básicas
        if not ticket_code or not reason or not accepted_policy:
            return render(request, "app/refund_form.html", {
                "error": "Todos los campos son obligatorios.",
                "data": request.POST
            })

        # Crear la solicitud de reembolso con estado pendiente
        RefundRequest.objects.update(
            ticket_code=ticket_code,
            reason=reason,
            additional_details=additional_details,
            user=request.user,
            accepted_policy=accepted_policy,
            approval=None,  # Estado pendiente
            event_name=ticket.event.title
        )

        # Crear una notificación para el usuario que solicitó el reembolso
        notification = Notification.objects.create(
            title="Solicitud de Reembolso Enviada",
            message=f"Tu solicitud de reembolso para el evento: '{ticket.event.title}' ha sido enviada y está en proceso de revisión.",
            priority="MEDIUM"
        )
        notification.users.add(request.user)
        notification.save()

        return redirect("events")

    return render(request, "app/refund_edit_form.html", {"refund_request": refund_request})

@login_required
def organizer_refund_requests(request):
    # Si no es organizador, redirigir a eventos
    if not request.user.is_organizer:
        # Obtener todos los eventos organizados por el usuario
        refund_requests = RefundRequest.objects.filter(user=request.user)

        # Asignar el evento relacionado a cada refund request
        for r in refund_requests:
            try:
                ticket_code_uuid = uuid.UUID(r.ticket_code)
                ticket = Ticket.objects.get(ticket_code=ticket_code_uuid, user=r.user)
                r.event = ticket.event
            except (Ticket.DoesNotExist, ValueError, TypeError):
                r.event = None

        return render(
            request,
            "app/organizer_refund_requests.html", 
            {
                "refund_requests": refund_requests,
            })
    else:
        # Obtener todos los eventos organizados por el usuario
        organizer_events = Event.objects.filter(organizer=request.user)

        # Obtener todos los refund requests cuyos usuarios compraron tickets para esos eventos
        refund_requests = RefundRequest.objects.filter(
            Q(event_name__in=organizer_events.values_list("title", flat=True))
            ).select_related("user")

        # Asignar el evento relacionado a cada refund request
        for r in refund_requests:
            try:
                ticket_code_uuid = uuid.UUID(r.ticket_code)
                ticket = Ticket.objects.get(ticket_code=ticket_code_uuid, user=r.user)
                r.event = ticket.event
            except (Ticket.DoesNotExist, ValueError, TypeError):
                r.event = None

        return render(request, "app/organizer_refund_requests.html", {
            "refund_requests": refund_requests,
        })


@login_required
def approve_refund_request(request, id):
    if not request.user.is_organizer:
        return redirect("events")

    refund = get_object_or_404(RefundRequest, pk=id)

    # Aseguramos que la solicitud aún no fue procesada
    if refund.approval is not None:
        messages.info(request, "La solicitud ya fue procesada.")
        return redirect("organizer_refund")

    # Buscar el ticket relacionado
    ticket = Ticket.objects.filter(
        ticket_code=refund.ticket_code,
        event__organizer=request.user
    ).first()

    if ticket:
        # Eliminar solo el ticket
        ticket.delete()

    # NO eliminar la refund request, solo actualizarla
    refund.approval = True
    refund.approval_date = timezone.now()
    refund.save()

    return redirect("organizer_refund")


@login_required
def reject_refund_request(request, id):
    # Si no es organizador, redirigir a eventos
    if not request.user.is_organizer:
        return redirect("events")
    
    refund = get_object_or_404(RefundRequest, pk=id)
    # Cambiar el estado a rechazado
    refund.approval = False
    refund.approval_date = timezone.now()
    refund.save()
    return redirect("organizer_refund")

@login_required
def refund_delete(request, id):
    
    refund = get_object_or_404(RefundRequest, pk=id)
    # Cambiar el estado a rechazado
    refund.delete()
    
    return redirect("organizer_refund")

@login_required
def view_refund_request(request, id):
    # si no es organizador, redirigir a eventos
    if not request.user.is_organizer:
        return redirect("events")
    refund = get_object_or_404(RefundRequest, pk=id)
    #verificar si la solicitud de reembolso ya fue aprobada o rechazada
    return render(request, "app/view_refund_request.html", {"refund": refund})


@login_required
@require_POST
def is_valid_code(request):
    """Valida que el código esté en formato correcto, exista y esté activo"""

    code = request.body.decode('utf-8').strip('"')
    errors = {}
    
    # Validaciones básicas
    if not isinstance(code, str):
        errors["code"] = "El código debe ser una cadena de texto."
    elif len(code) != 8:
        errors["code"] = "El código debe tener exactamente 8 caracteres."
    
    if errors:
        return JsonResponse({
            "errors": errors,
            "isValidCode": False,
        })
    
    try:
        discount = Discount.objects.get(code=code)
        print("MULTIPLIER:",  discount.multiplier)
        print("DISCOUNT:",  discount, "\n\n\n")
        
        
        messages.success(request, "Código validado correctamente")

        return JsonResponse({
            "message": "Código validado correctamente",
            "isValidCode": True,
            "multiplier": float(discount.multiplier),
            "code": discount.code
        })
        
    except Discount.DoesNotExist:
        return JsonResponse({
            "errors": {"code": "El código ingresado no existe."},
            "isValidCode": False,
        })
    
    except Exception as e:
        return JsonResponse({
            "errors": {"code": "Ocurrió un error al validar el código."},
            "isValidCode": False,
        })
            
@login_required
def buy_ticket(request, id):
    event = get_object_or_404(Event, pk=id)
    user = request.user
    available_tickets_to_buy = user.available_tickets_to_buy(event)

    if request.method == "POST":
        if available_tickets_to_buy == 0:
            messages.error(request, "Lo sentimos. Ya has comprado el máximo disponible de entradas por usuario.")
            return render(request, "app/buy_ticket.html", {"event": event, "available_tickets_to_buy": available_tickets_to_buy})

        try:
            quantity = int(request.POST.get("quantity"))
        except (TypeError, ValueError):
            messages.error(request, "La cantidad debe ser un número entero")
            return render(request, "app/buy_ticket.html", {"event": event, "available_tickets_to_buy": available_tickets_to_buy})

        type = request.POST.get("type")

        discount = None
        discount_str = request.POST.get("discount", "{}")
        try:
            discount_str = unquote(discount_str)
            discount_data = json.loads(discount_str)
            discount_info = discount_data.get("discount", {})
            
            if discount_info:
                discount_code = discount_info.get("code")
                if discount_code:
                    discount = Discount.objects.get(code=discount_code)
        except (json.JSONDecodeError, Discount.DoesNotExist):
            discount = None

        success, result = Ticket.new(quantity=quantity, type=type, event=event, user=user, discount=discount)

        if success:
            #GENERO UN CHEQUEO PARA VERIFICAR EL ESTADO DE SOLD OUT
            event.auto_update_state()
            messages.success(request, "¡Ticket comprado!")
            # Redirigir a la encuesta de satisfacción con el ID del ticket
            return redirect("satisfaction_survey", ticket_id=result.id)
        else:
            # Mostrar el mensaje de error específico
            for field, error in result.items():
                messages.error(request, error)
            return render(
                request,
                "app/buy_ticket.html",
                {
                    "event": event,
                    "available_tickets_to_buy": available_tickets_to_buy,
                    "errors": result,
                    "data": request.POST,
                }
            )

    return render(request, "app/buy_ticket.html", {"event": event, "available_tickets_to_buy": available_tickets_to_buy})

@login_required
def tickets(request):
    user = request.user

    return render(request, "app/tickets.html", {"tickets": user.tickets.all()})

@login_required
def ticket_detail(request, id):
    ticket = get_object_or_404(Ticket, pk=id)

    return render(request, "app/ticket_detail.html", {"ticket": ticket})

@login_required
def ticket_delete(request, id):
    user = request.user

    if request.method == "POST":
        ticket = get_object_or_404(Ticket, pk=id)

        if (ticket.user == user):
            ticket.delete()

    return redirect("tickets")

@login_required
def ticket_edit(request, id):
    ticket = get_object_or_404(Ticket, pk=id)

    if request.method == "POST":
        print ("Entraste al POST")
        try:
            quantity = int(request.POST.get("quantity"))
        except (TypeError, ValueError):
            messages.error(request, "La cantidad debe ser un número entero")
            return render(request, "app/buy_ticket.html", {"ticket": ticket})

        type = request.POST.get("type")

        success, result = Ticket.update(self=ticket, buy_date=timezone.now(), quantity=quantity, type=type, event=ticket.event, user=ticket.user)

        if success:
            messages.success(request, "¡Ticket modificado!")
            return redirect("tickets")
        else:
            messages.error(request, "Error al modificar el ticket")
            return render(
                request,
                "app/buy_ticket.html",
                {
                    "ticket": ticket,
                    "errors": result,
                    "data": request.POST,
                }
            )
    else:
        print ("NO entraste al POST")

    return render(request, "app/ticket_edit.html", {"ticket": ticket})



@login_required
def create_rating(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    # Verificar que el usuario no sea el organizador
    if request.user == event.organizer:
        messages.error(request, "Los organizadores no pueden calificar sus propios eventos.")
        return redirect("event_detail", event_id=event.id)
    
    # Verificar si el usuario ya ha calificado este evento
    if Rating.objects.filter(event=event, user=request.user).exists():
        messages.error(request, "Ya has calificado este evento.")
        return redirect("event_detail", event_id=event.id)
    
    
    if request.method == "POST":
        title = request.POST.get("title")
        text = request.POST.get("text", "")  # Texto es opcional
        rating = int(request.POST.get("rating"))
        
        if rating < 1 or rating > 5:
            messages.error(request, "La calificación debe estar entre 1 y 5 estrellas.")
            return render(request, "app/rating_form.html", {
                "event": event,
                "title": title,
                "text": text,
                "rating_value": rating
            })
        
        Rating.objects.create(
            title=title,
            text=text,
            rating=rating,
            event=event,
            user=request.user
        )
        messages.success(request, "Tu reseña ha sido publicada.")
        return redirect("event_detail", event_id=event.id)
            
    return render(request, "app/rating_form.html", {
        "event": event
    })


@login_required
def edit_rating(request, rating_id):
    rating = get_object_or_404(Rating, pk=rating_id)
    
    # Verificar que el usuario es el dueño de la calificación
    if rating.user != request.user:
        messages.error(request, "No tienes permiso para editar esta reseña.")
        return redirect("event_detail", event_id=rating.event.id)
    
    if request.method == "POST":
        title = request.POST.get("title")
        text = request.POST.get("text", "")  # Texto es opcional
        rating_value = int(request.POST.get("rating"))
        
        if rating_value < 1 or rating_value > 5:
            messages.error(request, "La calificación debe estar entre 1 y 5 estrellas.")
            return render(request, "app/rating_form.html", {
                "event": rating.event,
                "rating": rating,
                "title": title,
                "text": text,
                "rating_value": rating_value
            })
        
        rating.title = title
        rating.text = text
        rating.rating = rating_value
        rating.save()
        
        messages.success(request, "Tu reseña ha sido actualizada.")
        return redirect("event_detail", event_id=rating.event.id)
            
    return render(request, "app/rating_form.html", {
        "event": rating.event,
        "rating": rating,
        "title": rating.title,
        "text": rating.text,
        "rating_value": rating.rating
    })


@login_required
def delete_rating(request, rating_id):
    rating = get_object_or_404(Rating, pk=rating_id)
    event_id = rating.event.id
    
    # Verificar que el usuario es el dueño de la calificación o es el organizador del evento
    if rating.user != request.user and rating.event.organizer != request.user:
        return redirect("event_detail", event_id=event_id)
    
    rating.delete()
    return redirect("event_detail", event_id=event_id)


@login_required
def add_comment(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    
    # Verificar si el usuario ya ha comentado en este evento
    if Comment.objects.filter(event=event, user=request.user).exists():
        messages.error(request, "Ya has comentado en este evento. Puedes editar tu comentario existente.")
        return redirect("event_detail", event_id=event_id)
    
    if request.method == "POST":
        user = request.user
        title = request.POST.get("title")
        text = request.POST.get("text")

        if not title or not text:
            messages.error(request, "El título y el comentario son obligatorios.")
            return redirect("event_detail", event_id=event_id)
        
        Comment.objects.create(
            title=title,
            text=text,
            event=event,
            user=user
        )
        messages.success(request, "Tu comentario ha sido publicado.")
    return redirect("event_detail", event_id=event_id)


@login_required
def delete_comment(request, event_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, event_id=event_id)
    # Verificar que el usuario es el dueño del comentario o es el organizador del evento
    if comment.user != request.user and not request.user.is_organizer:
        messages.error(request, "No tienes permiso para eliminar este comentario.")
        return redirect("event_detail", event_id=event_id)
    
    if request.method == "POST":
        comment.delete()
        messages.success(request, "El comentario ha sido eliminado.")
        
    return redirect("event_detail", event_id=event_id)


@login_required
def update_comment(request, event_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, event_id=event_id)
    # Verificar que el usuario es el dueño del comentario
    if comment.user != request.user:
        messages.error(request, "No tienes permiso para editar este comentario.")
        return redirect("event_detail", event_id=event_id)
    
    if request.method == "POST":
        title = request.POST.get("title")
        text = request.POST.get("text")
        
        if not title or not text:
            messages.error(request, "El título y el comentario son obligatorios.")
            return redirect("event_detail", event_id=event_id)
        
        comment.title = title
        comment.text = text
        comment.save()
        messages.success(request, "Tu comentario ha sido actualizado.")
        
    return redirect("event_detail", event_id=event_id)


@login_required
def categories(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'app/categories.html', {'categories': categories})


@login_required
def category_form(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        is_active = request.POST.get("is_active") == "on"
        
        success, result = Category.new(name, description, is_active)
        
        if success:
            return redirect('categories')
        
        return render(request, 'app/category_form.html', {
            'errors': result,
            'data': {
                'name': name,
                'description': description,
                'is_active': is_active
            }
        })
        
    return render(request, 'app/category_form.html', {
        'data': {
            'is_active': True
        }
    })


@login_required
def category_edit(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        is_active = request.POST.get("is_active") == "on"
        
        success, errors = category.update(
            name=name,
            description=description,
            is_active=is_active
        )
        
        if success:
            return redirect('categories')
            
        return render(request, 'app/category_form.html', {
            'category': category,
            'errors': errors,
            'data': {
                'name': name,
                'description': description,
                'is_active': is_active
            }
        })
    
    return render(request, 'app/category_form.html', {
        'category': category,
        'data': {
            'name': category.name,
            'description': category.description,
            'is_active': category.is_active
        }
    })


@login_required
def category_delete(request, category_id):
    if request.method == "POST":
        category = get_object_or_404(Category, id=category_id)
        category.delete()
    return redirect('categories')


@login_required
def notification_list(request):
    if request.user.is_organizer:
        notifications = Notification.objects.all().order_by('-created_at')
        return render(request, "notifications/list.html", {"notifications": notifications, "user_is_organizer": request.user.is_organizer})
    else:
        notifications = Notification.objects.filter(users=request.user).order_by('-created_at')
        notifications_not_read = Notification.objects.filter(users=request.user, is_read=False).order_by('-created_at')
        return render(request, "notifications/list.html", {"notifications": notifications, "notifications_not_read": notifications_not_read, "user_is_organizer": request.user.is_organizer})


@login_required
def notification_create(request):
    if not request.user.is_organizer:
        return redirect("notification_list")

    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")
        priority = request.POST.get("priority")
        destinatario = request.POST.get("destinatario")
        event_id = request.POST.get("event_id")
        usuario_id = request.POST.get("usuario_id")

        # Validaciones
        if destinatario == "todos" and not event_id:
            messages.error(request, "Debe seleccionar un evento.")
            return redirect("notification_create")

        if destinatario == "usuario" and not usuario_id:
            messages.error(request, "Debe seleccionar un usuario.")
            return redirect("notification_create")

        notification = Notification.objects.create(
            title=title,
            message=message,
            priority=priority,
            created_at=timezone.now(),
        )

        # Asignar destinatarios
        if destinatario == "todos":
            event = get_object_or_404(Event, id=event_id)
            asistentes = event.get_attendees()
            notification.users.set(asistentes)
        elif destinatario == "usuario":
            usuario = get_object_or_404(User, pk=usuario_id)
            notification.users.set([usuario])

        notification.save()
        return redirect("notification_list")

    eventos = Event.objects.all()
    usuarios = User.objects.filter(is_organizer=False)
    return render(request, "notifications/form.html", {
        "eventos": eventos,
        "usuarios": usuarios,
    })


@login_required
def notification_edit(request, notification_id):
    if not request.user.is_organizer:
        return redirect("notification_list")

    notification = get_object_or_404(Notification, pk=notification_id)

    if request.method == "POST":
        notification.title = request.POST.get("title")
        notification.message = request.POST.get("message")
        notification.priority = request.POST.get("priority")
        recipient_ids = request.POST.getlist("recipients")
        notification.users.set(recipient_ids)
        notification.save()
        return redirect("notification_list")

    users = User.objects.filter(is_organizer=False)
    return render(request, "notifications/form.html", {"notification": notification, "users": users})


@login_required
def notification_delete(request, notification_id):
    if not request.user.is_organizer:
        return redirect("notification_list")

    notification = get_object_or_404(Notification, pk=notification_id)
    notification.delete()
    return redirect("notification_list")


@login_required
def notification_detail(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id)

    if not request.user.is_organizer and request.user not in notification.users.all():
        return redirect("notification_list")

    return render(request, "notifications/detail.html", {"notification": notification})


@login_required
def notification_mark_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, users=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notification_list')


@login_required
def mark_all_notifications_read(request):
    request.user.notifications.update(is_read=True)
    return redirect('notification_list')


@login_required
def venue_form(request):
    if request.method == 'POST':
        name=request.POST.get("name")
        adress=request.POST.get("adress")
        city=request.POST.get("city")
        capacity=int(request.POST.get("capacity"))
        contact=request.POST.get("contact")


        success, venue=Venue.new(
            name=name,
            adress=adress,
            city=city,
            capacity=capacity,
            contact=contact
        )

        if success:
            return redirect('venues')

    return render(request, "app/venue_form.html")

@login_required
def venues(request):
    venues = Venue.objects.all()

    return render(
        request,
        "app/venues.html",
        {"venues": venues, "user_is_organizer": request.user.is_organizer},
    )

@login_required
def venue_delete(request, id):
    if request.user.is_organizer:     
        venue = get_object_or_404(Venue, pk=id)
        venue.delete()

    return redirect("venues")

@login_required
def venue_edit(request, id):
    venue = get_object_or_404(Venue, pk=id)


    if request.method == "POST":
        name=request.POST.get("name")
        adress=request.POST.get("adress")
        city=request.POST.get("city")
        capacity=int(request.POST.get("capacity"))
        contact=request.POST.get("contact")


        success, updatedVenue=venue.update(
            name=name,
            adress=adress,
            city=city,
            capacity=capacity,
            contact=contact
        )

        # Validaciones básicas
        if not success:
            return render(request, "app/venue_edit_form.html", {
                "error": "Todos los campos son obligatorios.",
                "data": request.POST
            })
        else:
            return redirect('venues')

    return render(request, "app/venue_edit_form.html", {"venue": venue})

@login_required
def toggle_favorite(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    user = request.user
    
    if event.favorited_by.filter(id=user.id).exists():
        event.favorited_by.remove(user)
        messages.success(request, "Evento removido de favoritos")
    else:
        event.favorited_by.add(user)
        messages.success(request, "Evento agregado a favoritos")
    
    return redirect('events')

@login_required
def satisfaction_survey(request, ticket_id):
    """Vista para mostrar y procesar la encuesta de satisfacción"""
    ticket = get_object_or_404(Ticket, pk=ticket_id, user=request.user)
    
    # Verificar si ya existe una encuesta para este ticket
    if SatisfactionSurvey.objects.filter(ticket=ticket).exists():
        messages.info(request, "Ya has completado la encuesta para este ticket.")
        return redirect("tickets")
    
    if request.method == "POST":
        overall_satisfaction = request.POST.get("overall_satisfaction")
        purchase_experience = request.POST.get("purchase_experience")
        would_recommend = request.POST.get("would_recommend")
        comments = request.POST.get("comments", "")
        
        # Convertir would_recommend a booleano
        would_recommend_bool = would_recommend == "yes"
        
        # Validar y crear la encuesta
        success, result = SatisfactionSurvey.new(
            ticket=ticket,
            user=request.user,
            event=ticket.event,
            overall_satisfaction=int(overall_satisfaction) if overall_satisfaction else None,
            purchase_experience=purchase_experience,
            would_recommend=would_recommend_bool,
            comments=comments
        )
        
        if success:
            messages.success(request, "¡Gracias por completar la encuesta de satisfacción!")
            return redirect("tickets")
        else:
            messages.error(request, "Error al enviar la encuesta. Por favor, revisa los datos.")
            return render(request, "app/satisfaction_survey.html", {
                "ticket": ticket,
                "errors": result,
                "data": request.POST
            })
    
    return render(request, "app/satisfaction_survey.html", {
        "ticket": ticket,
        "event": ticket.event
    })


@login_required
def survey_results(request, event_id):
    """Vista para ver los resultados de las encuestas de un evento (solo organizadores)"""
    event = get_object_or_404(Event, pk=event_id)
    
    # Verificar que el usuario sea el organizador del evento
    if request.user != event.organizer:
        messages.error(request, "No tienes permiso para ver estos resultados.")
        return redirect("events")
    
    surveys = SatisfactionSurvey.objects.filter(event=event).select_related('user', 'ticket')
    
    # Calcular estadísticas
    total_surveys = surveys.count()
    if total_surveys > 0:
        avg_satisfaction = sum(s.overall_satisfaction for s in surveys) / total_surveys
        recommend_percentage = (surveys.filter(would_recommend=True).count() / total_surveys) * 100
    else:
        avg_satisfaction = 0
        recommend_percentage = 0
    
    return render(request, "app/survey_results.html", {
        "event": event,
        "surveys": surveys,
        "total_surveys": total_surveys,
        "avg_satisfaction": round(avg_satisfaction, 1),
        "recommend_percentage": round(recommend_percentage, 1)
    })
