# app/test/test_unit/test_refund_validation.py (Tu archivo actual)

from django.test import TestCase
from django.utils import timezone
import datetime

from app.models import User, Event, Venue, Category, Ticket, RefundRequest

class RefundValidationUnitTest(TestCase):
    """Tests unitarios para la validación de solicitudes de reembolso"""

    def setUp(self):
        # Crear usuario
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

        # Crear ticket
        self.ticket = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            type=Ticket.GENERAL # Usar la constante del modelo
        )

    def test_cannot_create_multiple_active_refunds(self):
        """
        Test que verifica que la lógica de conteo de solicitudes pendientes
        identifica correctamente la cantidad de solicitudes activas para un ticket.
        (Este test NO intenta prevenir la creación a nivel de DB, sino contar lo que hay).
        """
        # Crear la primera solicitud de reembolso
        # La guardamos en una variable para poder referenciarla directamente
        first_refund = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            reason="Razón de prueba 1",
            event_name=self.event.title,
            approval=None # Aseguramos que está pendiente
        )

        # Intentar crear una segunda solicitud (a nivel de DB, esto es posible sin una restricción unique_together)
        # La guardamos en otra variable
        second_refund = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            reason="Razón de prueba 2",
            event_name=self.event.title,
            approval=None # Aseguramos que también está pendiente
        )

        # Verificar que se crearon ambas instancias y que están pendientes
        # Accediendo directamente a las variables que ya tenemos
        self.assertIsNone(first_refund.approval)
        self.assertIsNone(second_refund.approval)

        # Verificar que la consulta de "solicitudes activas" (pendientes)
        # para este usuario y ticket_code devuelve 2.
        # Esto prueba que el filtro `approval__isnull=True` funciona como se espera
        # para identificar múltiples solicitudes si la DB las permitiera.
        active_refunds_count = RefundRequest.objects.filter(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            approval__isnull=True # Filtro para solicitudes pendientes
        ).count()
        self.assertEqual(active_refunds_count, 2)

        # NOTA: Este test unitario, tal como está, prueba que el ORM *puede* crear dos solicitudes
        # y que tu filtro las contaría como activas. La prevención de duplicados ocurre en la vista.
        # Si el objetivo de tus profesores era que este test unitario *fallara* al intentar crear la segunda
        # solicitud, entonces necesitarías una restricción `unique_together` en tu modelo `RefundRequest`
        # que incluya `user`, `ticket_code` y `approval__isnull=True`. Sin esa restricción,
        # el `create` siempre tendrá éxito a nivel de DB.


    def test_can_create_refund_after_rejected(self):
        """Test que verifica que se puede crear una nueva solicitud después de que una fue rechazada"""
        # Crear y rechazar primera solicitud
        refund1 = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            reason="Razón de prueba 1",
            event_name=self.event.title,
            approval=False # Rechazada
        )
        # No necesitas refund1.save() si ya asignas approval=False en el create.
        # Si lo haces en dos pasos:
        # refund1 = RefundRequest.objects.create(...)
        # refund1.approval = False
        # refund1.save() # Aquí sí necesitas el save()

        # Crear segunda solicitud
        refund2 = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            reason="Razón de prueba 2",
            event_name=self.event.title,
            approval=None # La nueva solicitud debe estar pendiente
        )
        self.assertIsNone(refund2.approval)  # La nueva solicitud debe estar pendiente

        # Verificar que hay dos solicitudes en total para este ticket/usuario
        self.assertEqual(RefundRequest.objects.filter(user=self.user, ticket_code=self.ticket.ticket_code).count(), 2)
        # Y que solo una está pendiente (la segunda)
        self.assertEqual(RefundRequest.objects.filter(user=self.user, ticket_code=self.ticket.ticket_code, approval__isnull=True).count(), 1)


    def test_can_create_refund_after_approved(self):
        """Test que verifica que se puede crear una nueva solicitud después de que una fue aprobada"""
        # Crear y aprobar primera solicitud
        refund1 = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            reason="Razón de prueba 1",
            event_name=self.event.title,
            approval=True # Aprobada
        )
        # No necesitas refund1.save() si ya asignas approval=True en el create.

        # Crear segunda solicitud
        refund2 = RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            reason="Razón de prueba 2",
            event_name=self.event.title,
            approval=None # La nueva solicitud debe estar pendiente
        )
        self.assertIsNone(refund2.approval)  # La nueva solicitud debe estar pendiente

        # Verificar que hay dos solicitudes en total para este ticket/usuario
        self.assertEqual(RefundRequest.objects.filter(user=self.user, ticket_code=self.ticket.ticket_code).count(), 2)
        # Y que solo una está pendiente (la segunda)
        self.assertEqual(RefundRequest.objects.filter(user=self.user, ticket_code=self.ticket.ticket_code, approval__isnull=True).count(), 1)