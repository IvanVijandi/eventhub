from django.test import TestCase
from django.utils import timezone
import datetime
from typing import cast 

from app.models import User, Event, Venue, Category, Ticket, RefundRequest


class RefundValidationUnitTest(TestCase):
    """Tests unitarios para la validación de solicitudes de reembolso"""

    def setUp(self):
        # Creo usuario (el mismo para todas las solicitudes)
        self.user = User.objects.create_user(
            username="usuario_test",
            email="usuario@test.com",
            password="password123"
        )
        # Creo organizador (el mismo para todas las solicitudes)
        self.organizer = User.objects.create_user(
            username='organizer_test', email='organizer@test.com', password='password_org', is_organizer=True
        )

        # Creo venue y categoría
        self.venue = Venue.objects.create(
            name="Venue de prueba",
            adress="Dirección de prueba",
            city="Ciudad de prueba",
            capacity=100,
            contact="contacto@prueba.com"
        )

        self.category = Category.objects.create(
            name="Categoría de prueba",
            description="Descripción de la categoría de prueba",
            is_active=True
        )

        # Creo evento
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
            category=self.category
        )

        # Creo diferentes TICKETS para las solicitudes de reembolso
        self.ticket_general_pending = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            type=Ticket.GENERAL
        )
        self.ticket_vip_rejected = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            type=Ticket.VIP
        )
        self.ticket_general_approved = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            type=Ticket.GENERAL
        )
    
        self.initial_count = RefundRequest.objects.count()

    def test_validate_successful_data(self):
        """Verifica que RefundRequest.validate() retorna un diccionario vacío para datos válidos."""
        errors = RefundRequest.validate(
            user=self.user,
            ticket_code=str(self.ticket_general_pending.ticket_code),
            reason="Motivo válido para reembolso",
            accepted_policy=True
        )
        self.assertEqual(errors, {})

    def test_validate_missing_user(self):
        """Verifica que RefundRequest.validate() detecta la falta de usuario."""
        errors = RefundRequest.validate(
            user=None,
            ticket_code=str(self.ticket_general_pending.ticket_code),
            reason="Motivo válido",
            accepted_policy=True
        )
        self.assertIn("user", errors)
        self.assertEqual(errors["user"], "El usuario es requerido")

    def test_validate_missing_ticket_code(self):
        """Verifica que RefundRequest.validate() detecta la falta de código de ticket."""
        errors = RefundRequest.validate(
            user=self.user,
            ticket_code="", # Código de ticket vacío
            reason="Motivo válido",
            accepted_policy=True
        )
        self.assertIn("ticket_code", errors)
        self.assertEqual(errors["ticket_code"], "El código del ticket es requerido")

    def test_validate_missing_reason(self):
        """Verifica que RefundRequest.validate() detecta la falta de motivo."""
        errors = RefundRequest.validate(
            user=self.user,
            ticket_code=str(self.ticket_general_pending.ticket_code),
            reason="", # Motivo vacío
            accepted_policy=True
        )
        self.assertIn("reason", errors)
        self.assertEqual(errors["reason"], "El motivo es requerido")

    def test_validate_policy_not_accepted(self):
        """Verifica que RefundRequest.validate() detecta si la política no fue aceptada."""
        errors = RefundRequest.validate(
            user=self.user,
            ticket_code=str(self.ticket_general_pending.ticket_code),
            reason="Motivo válido",
            accepted_policy=False # Política no aceptada
        )
        self.assertIn("accepted_policy", errors)
        self.assertEqual(errors["accepted_policy"], "Debes aceptar la política de reembolsos")

    def test_new_successful_creation(self):
        """Verifica que RefundRequest.new() crea una solicitud exitosamente y en estado pendiente."""
        success, result = RefundRequest.new(
            user=self.user,
            ticket_code=str(self.ticket_general_pending.ticket_code),
            reason="Creación exitosa de solicitud",
            accepted_policy=True,
            additional_details="Detalles opcionales",
            event_name=self.event.title
        )
        
        refund_request = cast(RefundRequest, result)

        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(RefundRequest.objects.count(), self.initial_count + 1)
        self.assertIsNone(refund_request.approval)

    def test_new_with_validation_errors(self):
        """Verifica que RefundRequest.new() retorna False y errores si los datos no son válidos."""
        success, raw_errors = RefundRequest.new(
            user=None, # Dato inválido
            ticket_code=str(self.ticket_general_pending.ticket_code),
            reason="Motivo",
            accepted_policy=True
        )
        self.assertFalse(success)
        
        errors = cast(dict, raw_errors) 
        
        self.assertIn("user", errors)
        self.assertEqual(RefundRequest.objects.count(), self.initial_count)

    def test_cannot_create_multiple_active_refunds(self):
        """
        Test que verifica que RefundRequest.new() previene la creación de múltiples solicitudes
        de reembolso activas para el mismo ticket y usuario.
        """

        # Creo la primera solicitud pendiente
        success1, result1 = RefundRequest.new(
            user=self.user,
            ticket_code=str(self.ticket_general_pending.ticket_code),
            reason="Primera solicitud pendiente",
            accepted_policy=True,
            event_name=self.event.title
        )
        self.assertTrue(success1, "La primera solicitud debería crearse exitosamente.")
        self.assertEqual(RefundRequest.objects.count(), self.initial_count + 1)

        # Intento creao una segunda solicitud pendiente para el mismo ticket
        success2, raw_errors = RefundRequest.new(
            user=self.user,
            ticket_code=str(self.ticket_general_pending.ticket_code),
            reason="Segunda solicitud que debería ser bloqueada",
            accepted_policy=True,
            event_name=self.event.title
        )
        self.assertFalse(success2, "La segunda solicitud duplicada NO debería crearse.")
        
        errors = cast(dict, raw_errors)

        self.assertIn("ticket_code", errors)
        self.assertEqual(errors["ticket_code"], "Ya existe una solicitud pendiente para este ticket")
        self.assertEqual(RefundRequest.objects.count(), self.initial_count + 1)

    def test_can_create_refund_after_rejected(self):
        """Test que verifica que se puede crear una nueva solicitud después de que una fue rechazada."""

        # Creo y rechazo la primera solicitud
        refund1 = RefundRequest.objects.create(
            user=self.user,
            ticket_code=str(self.ticket_vip_rejected.ticket_code),
            reason="Primera solicitud rechazada",
            accepted_policy=True,
            event_name=self.event.title,
            approval=False, # Estado rechazado
            approval_date=timezone.now().date()
        )
        self.assertFalse(refund1.approval)
        self.assertEqual(RefundRequest.objects.count(), self.initial_count + 1)

        # Ahora creo una nueva solicitud pendiente para el MISMO ticket
        success2, result2 = RefundRequest.new(
            user=self.user,
            ticket_code=str(self.ticket_vip_rejected.ticket_code),
            reason="Nueva solicitud después de una rechazada",
            accepted_policy=True,
            event_name=self.event.title
        )
        self.assertTrue(success2, f"La nueva solicitud debería crearse después del rechazo, pero falló con: {result2}")
        
        new_refund = cast(RefundRequest, result2)

        self.assertIsInstance(new_refund, RefundRequest)
        self.assertIsNone(new_refund.approval)
        self.assertEqual(RefundRequest.objects.count(), self.initial_count + 2)

        # Verificar conteos finales para este ticket
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=str(self.ticket_vip_rejected.ticket_code)
        ).count(), 2)
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=str(self.ticket_vip_rejected.ticket_code), approval=False
        ).count(), 1)
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=str(self.ticket_vip_rejected.ticket_code), approval__isnull=True
        ).count(), 1)


    def test_can_create_refund_after_approved(self):
        """Test que verifica que se puede crear una nueva solicitud después de que una fue aprobada."""

        # Creo y apruebo la primera solicitud
        refund1 = RefundRequest.objects.create(
            user=self.user,
            ticket_code=str(self.ticket_general_approved.ticket_code),
            reason="Primera solicitud aprobada",
            accepted_policy=True,
            event_name=self.event.title,
            approval=True,
            approval_date=timezone.now().date()
        )
        self.assertTrue(refund1.approval)
        self.assertEqual(RefundRequest.objects.count(), self.initial_count + 1)

        # Ahora creo una nueva solicitud pendiente para el MISMO ticket
        success2, result2 = RefundRequest.new(
            user=self.user,
            ticket_code=str(self.ticket_general_approved.ticket_code),
            reason="Nueva solicitud después de una aprobada",
            accepted_policy=True,
            event_name=self.event.title
        )
        self.assertTrue(success2, f"La nueva solicitud debería crearse después de la aprobación, pero falló con: {result2}")
        
        new_refund = cast(RefundRequest, result2)

        self.assertIsInstance(new_refund, RefundRequest)
        self.assertIsNone(new_refund.approval)
        self.assertEqual(RefundRequest.objects.count(), self.initial_count + 2)

        # Verifico conteos finales para este ticket
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=str(self.ticket_general_approved.ticket_code)
        ).count(), 2)
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=str(self.ticket_general_approved.ticket_code), approval=True
        ).count(), 1)
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=str(self.ticket_general_approved.ticket_code), approval__isnull=True
        ).count(), 1)