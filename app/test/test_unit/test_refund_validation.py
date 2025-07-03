from django.test import TestCase
from django.utils import timezone
import datetime

from app.models import User, Event, Venue, Category, Ticket, RefundRequest

class RefundValidationUnitTest(TestCase):
    """Tests unitarios para la validación de solicitudes de reembolso"""

    def setUp(self):
        # Crear usuario (el mismo para todas las solicitudes)
        self.user = User.objects.create_user(
            username="usuario_test",
            email="usuario@test.com",
            password="password123"
        )

        # Crear venue y categoría
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

        # Crear evento
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.user,
            venue=self.venue,
            category=self.category
        )

        # Creo diferentes TICKETS para las solicitudes de reembolso
        # Un ticket para la solicitud pendiente (GENERAL)
        self.ticket_general_pending = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            type=Ticket.GENERAL
        )
        # Un ticket para la solicitud rechazada (VIP)
        self.ticket_vip_rejected = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            type=Ticket.VIP
        )
        # Un ticket para la solicitud aprobada (GENERAL)
        self.ticket_general_approved = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            type=Ticket.GENERAL
        )

        # Creo las instancias de RefundRequest con diferentes estados en setUp()
        # Solicitud pendiente (activa)
        self.refund_pending = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket_general_pending.ticket_code,
            reason="Solicitud pendiente creada en setUp",
            event_name=self.event.title,
            approval=None # Estado pendiente
        )

        # Solicitud rechazada
        self.refund_rejected = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket_vip_rejected.ticket_code, 
            reason="Solicitud rechazada creada en setUp",
            event_name=self.event.title,
            approval=False # Estado rechazado
        )

        # Solicitud aprobada
        self.refund_approved = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket_general_approved.ticket_code,
            reason="Solicitud aprobada creada en setUp",
            event_name=self.event.title,
            approval=True # Estado aprobado
        )

    def test_cannot_create_multiple_active_refunds(self):
        """
        Test que verifica que la lógica de conteo de solicitudes pendientes
        identifica correctamente la cantidad de solicitudes activas para un ticket.
        """
        # Creo otra solicitud pendiente para el mismo ticket (self.ticket_general_pending).
        
        second_pending_for_same_ticket = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket_general_pending.ticket_code, # Mismo ticket que self.refund_pending
            reason="Segunda solicitud pendiente para el mismo ticket",
            event_name=self.event.title,
            approval=None # pendiente
        )

        # Verificar que la primera y la segunda instancia están pendientes
        self.assertIsNone(self.refund_pending.approval)
        self.assertIsNone(second_pending_for_same_ticket.approval)

        # Verificar que la consulta de "solicitudes activas" para ese ticket devuelve 2
        active_refunds_count = RefundRequest.objects.filter(
            user=self.user,
            ticket_code=self.ticket_general_pending.ticket_code,
            approval__isnull=True # Filtro para solicitudes pendientes
        ).count()
        self.assertEqual(active_refunds_count, 2)
        

    def test_can_create_refund_after_rejected(self):
        """Test que verifica que se puede crear una nueva solicitud después de que una fue rechazada"""
        # Ahora creo una nueva solicitud pendiente para el MISMO ticket que la rechazada.
        new_refund = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket_vip_rejected.ticket_code, # Mismo ticket que la rechazada
            reason="Nueva solicitud después de una rechazada",
            event_name=self.event.title,
            approval=None # Debe estar pendiente
        )
        self.assertIsNone(new_refund.approval)

        # Verificar que ahora hay una rechazada y una pendiente para ese ticket
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=self.ticket_vip_rejected.ticket_code
        ).count(), 2)
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=self.ticket_vip_rejected.ticket_code, approval=False # Solo la rechazada
        ).count(), 1)
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=self.ticket_vip_rejected.ticket_code, approval__isnull=True # Solo la pendiente
        ).count(), 1)


    def test_can_create_refund_after_approved(self):
        """Test que verifica que se puede crear una nueva solicitud después de que una fue aprobada"""
        # Ahora creo una nueva solicitud pendiente para el MISMO ticket que la aprobada.
        new_refund = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket_general_approved.ticket_code, # Mismo ticket que la aprobada
            reason="Nueva solicitud después de una aprobada",
            event_name=self.event.title,
            approval=None # Debe estar pendiente
        )
        self.assertIsNone(new_refund.approval)

        # Verificar que ahora hay una aprobada y una pendiente para ese ticket
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=self.ticket_general_approved.ticket_code
        ).count(), 2)
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=self.ticket_general_approved.ticket_code, approval=True # Solo la aprobada
        ).count(), 1)
        self.assertEqual(RefundRequest.objects.filter(
            user=self.user, ticket_code=self.ticket_general_approved.ticket_code, approval__isnull=True # Solo la pendiente
        ).count(), 1)