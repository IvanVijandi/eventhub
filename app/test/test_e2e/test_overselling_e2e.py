import datetime
from django.utils import timezone
from playwright.sync_api import expect

from app.models import Event, User, Venue, Ticket
from app.test.test_e2e.base import BaseE2ETest


class OversellingPreventionTest(BaseE2ETest):
    """Tests relacionados con la prevención de overselling de tickets"""

    def setUp(self):
        super().setUp()

        # Crear un usuario regular
        self.regular_user = User.objects.create_user(
            username="testuser_regular",
            email="testuser_regular@example.com",
            password="password123",
            is_organizer=False,
        )
        
        # Crear un establecimiento/localización
        self.venue = Venue.objects.create(
            name="Estadio de Prueba",
            adress="Calle de Prueba 123",
            city="Ciudad de Prueba",
            capacity=3
        )

        # Crear un evento que use la localización anterior
        event_date = timezone.make_aware(datetime.datetime(2030, 2, 10, 10, 10))
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento",
            scheduled_at=event_date,
            organizer=self.regular_user,
            venue=self.venue
        )

    def test_cannot_exceed_remaining_capacity(self):
        """Test que verifica que no se pueden comprar más tickets que los disponibles después de compras previas"""
        self.login_user("usuario", "password123")
        
        self.page.goto(f"{self.live_server_url}/events/{self.event.id}/buy-ticket/")
        self.page.wait_for_selector("#quantity")
        self.page.fill("#quantity", "4") 
        self.page.get_by_label("Tipo de entrada").select_option("GENERAL")
        self.complete_card_data_in_buy_ticket_form()
        self.page.get_by_role("button", name="Confirmar compra").click()
        error_message = self.page.locator(".alert")
        expect(error_message).to_have_text("No hay suficientes entradas disponibles. Solo quedan 3 entradas.")