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

    def test_countdown_visible_for_non_organizer_user_journey(self):
        """Test del flujo completo de usuario NO organizador viendo countdown usando Playwright"""
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

        # Verificar que el countdown muestra algún texto (no vacío)
        expect(countdown_timer).not_to_have_text("")

        #Esperar a que el texto cambie, pero con espera explícita y corta
        initial_text = countdown_timer.inner_text()
        self.page.wait_for_timeout(500)  # modifico Tiempo de espera de 2000 a 500
        expect(countdown_timer).not_to_have_text(initial_text)

    def test_countdown_not_visible_for_organizer_user(self):
        """Test que el countdown NO es visible para usuarios organizadores"""
        # Login como organizador
        self.login_user('organizador', 'password123')
        
        # Navegar al detalle del evento
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar que la página del evento cargó correctamente
        expect(self.page.locator("h1").filter(has_text="Future Event")).to_be_visible()
        
        # Verificar que el countdown NO está presente
        countdown_container = self.page.locator("#countdown-container")
        expect(countdown_container).to_have_count(0)
        
        # Verificar que tampoco están los elementos específicos del countdown
        expect(self.page.locator("#countdown-timer")).to_have_count(0)


    def test_countdown_responsive_design(self):
        """Test diseño responsive del countdown"""
        # Login como usuario NO organizador
        self.login_user('usuario', 'password123')
        
        # Navegar al detalle del evento
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Probar en viewport móvil
        self.page.set_viewport_size({"width": 375, "height": 667})
        
        # Verificar que el countdown sigue siendo visible en móvil
        expect(self.page.locator("#countdown-container")).to_be_visible()
        expect(self.page.locator("#countdown-timer")).to_be_visible()
        
        # Probar en tablet
        self.page.set_viewport_size({"width": 768, "height": 1024})
        expect(self.page.locator("#countdown-container")).to_be_visible()
        
        # Volver a desktop
        self.page.set_viewport_size({"width": 1200, "height": 800})
        expect(self.page.locator("#countdown-container")).to_be_visible()

    def test_countdown_with_past_event_behavior(self):
        """Test comportamiento del countdown con evento pasado"""
        self.login_user('usuario', 'password123')
        self.page.goto(f"{self.live_server_url}/events/{self.past_event.pk}/")
        self.page.wait_for_load_state("networkidle")

        expect(self.page.locator("h1", has_text="Past Event")).to_be_visible()
        countdown_container = self.page.locator("#countdown-container")
        expect(countdown_container).to_be_visible()
        expect(countdown_container).to_contain_text("¡El evento ya comenzó!")

    def test_countdown_visual_elements_present(self):
        """Test que todos los elementos visuales del countdown están presentes"""
        # Login como usuario NO organizador
        self.login_user('usuario', 'password123')
        
        # Navegar al detalle del evento
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar estructura HTML del countdown
        countdown_container = self.page.locator("#countdown-container")
        expect(countdown_container).to_be_visible()
        
        # Verificar que los labels de tiempo están presentes
        expect(countdown_container).to_contain_text("días")
        expect(countdown_container).to_contain_text("horas")
        expect(countdown_container).to_contain_text("minutos")
        expect(countdown_container).to_contain_text("segundos")
        
        # Verificar que el texto "Tiempo restante" está presente
        expect(countdown_container).to_contain_text("Tiempo restante")

    def test_countdown_event_information_display(self):
        """Test que la información del evento se muestra correctamente junto al countdown"""
        # Login como usuario NO organizador
        self.login_user('usuario', 'password123')
        
        # Navegar al detalle del evento
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar información del evento
        expect(self.page.locator("h1").filter(has_text="Future Event")).to_be_visible()
        expect(self.page.locator("p").filter(has_text="Event for countdown testing")).to_be_visible()
        
        # Verificar información del venue
        expect(self.page.locator("span").filter(has_text="Test Venue")).to_be_visible()
        
        # Verificar que el countdown y la información del evento están en la misma página
        expect(self.page.locator("#countdown-container")).to_be_visible()

    def test_countdown_authentication_requirement(self):
        """Test que se requiere autenticación para ver el countdown"""
        # Sin hacer login, intentar acceder al evento
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar que estamos en la página de login
        expect(self.page).to_have_url(re.compile(r"/login"))

    def test_countdown_multiple_events_navigation(self):
        """Test navegación entre múltiples eventos con countdown"""
        # Login como usuario NO organizador
        self.login_user('usuario', 'password123')
        
        # Navegar al primer evento
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar countdown en primer evento
        expect(self.page.locator("#countdown-container")).to_be_visible()
        expect(self.page.locator("h1").filter(has_text="Future Event")).to_be_visible()
        
        # Navegar al segundo evento
        self.page.goto(f"{self.live_server_url}/events/{self.additional_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar countdown en segundo evento
        expect(self.page.locator("#countdown-container")).to_be_visible()
        expect(self.page.locator("h1").filter(has_text="Additional Event")).to_be_visible()

    def test_countdown_event_details_interaction(self):
        """Test interacción con detalles del evento que tiene countdown"""
        self.login_user('usuario', 'password123')
        self.page.goto(f"{self.live_server_url}/events/{self.future_event.pk}/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar que el countdown no interfiere con otros elementos de la página
        expect(self.page.locator("#countdown-container")).to_be_visible()
        
        # Verificar que el botón de compra es visible y está habilitado
        buy_button = self.page.locator(".btn:has-text('Comprar')")
        expect(buy_button.first).to_be_visible()
        expect(buy_button.first).to_be_enabled()
        
        # Verificar que la navbar es visible
        navbar = self.page.locator(".navbar")
        expect(navbar).to_be_visible()
        
        # Verificar que se puede hacer scroll sin problemas con el countdown
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(500)
        expect(self.page.locator("#countdown-container")).to_be_visible() 