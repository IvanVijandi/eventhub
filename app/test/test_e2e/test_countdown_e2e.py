import re
from playwright.sync_api import expect
from django.utils import timezone
from datetime import timedelta
from app.models import User, Event, Venue
from .base import BaseE2ETest


class CountdownE2ETest(BaseE2ETest):
    """Tests end-to-end para la funcionalidad completa de countdown usando Playwright"""
    
    def setUp(self):
        """Configuración inicial para los tests e2e"""
        super().setUp()
        
        # Venue para eventos
        self.venue = Venue.objects.create(
            name='Test Venue',
            adress='Test Address',
            city='Test City',
            capacity=100,
            contact='test@venue.com'
        )
        
        # Eventos base para reutilizar en tests
        self.future_event = Event.objects.create(
            title='Future Event',
            description='Event for countdown testing',
            scheduled_at=timezone.now() + timedelta(days=30),
            organizer=self.organizer,
            venue=self.venue
        )

        self.past_event = Event.objects.create(
            title='Past Event', 
            description='Event that already happened',
            scheduled_at=timezone.now() - timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue
        )

        # Evento adicional para pruebas de navegación
        self.additional_event = Event.objects.create(
            title='Additional Event',
            description='Another event for navigation testing',
            scheduled_at=timezone.now() + timedelta(days=45),
            organizer=self.organizer,
            venue=self.venue
        )

    def test_countdown_visible_for_regular_users(self):
        """Test que verifica que usuarios regulares pueden ver el countdown del evento"""
        # Login como usuario NO organizador
        self.login_user('usuario', 'password123')
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")

        # Verificar que la página del evento cargó correctamente
        expect(self.page.locator("h1", has_text="Future Event")).to_be_visible()

        # Verificar que el countdown está presente y visible
        countdown_container = self.page.locator("#countdown-container")
        countdown_timer = self.page.locator("#countdown-timer")
        expect(countdown_container).to_be_visible()
        expect(countdown_timer).to_be_visible()

        # Verificar que el texto del countdown cambia con el tiempo
        initial_text = countdown_timer.inner_text()
        self.page.wait_for_timeout(500)
        expect(countdown_timer).not_to_have_text(initial_text)

    def test_countdown_not_visible_for_organizers(self):
        """Test que verifica que el countdown NO es visible para organizadores"""
        # Login como organizador
        self.login_user('organizador', 'password123')
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar que la página del evento cargó correctamente
        expect(self.page.locator("h1").filter(has_text="Future Event")).to_be_visible()
        
        # Verificar que el countdown NO está presente
        expect(self.page.locator("#countdown-container")).to_have_count(0)

 