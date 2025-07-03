import datetime
from django.utils import timezone
from playwright.sync_api import expect

from app.models import Event, User, Venue, Category
from app.test.test_e2e.base import BaseE2ETest

class EventStatesE2ETest(BaseE2ETest):
    """Tests end-to-end para la funcionalidad de estados de eventos"""

    def setUp(self):
        super().setUp()

        # Crear usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador_states",
            email="organizador_states@example.com",
            password="password123",
            is_organizer=True,
        )

        # Crear usuario regular
        self.regular_user = User.objects.create_user(
            username="usuario_states",
            email="usuario_states@example.com",
            password="password123",
            is_organizer=False,
        )

        # Crear venue y categoría
        self.venue = Venue.objects.create(
            name="Venue de prueba states",
            adress="Dirección de prueba",
            city="Ciudad de prueba",
            capacity=100,
            contact="contacto@prueba.com"
        )

        self.category = Category.objects.create(
            name="Categoría de prueba states",
            description="Descripción de la categoría de prueba",
            is_active=True
        )

        # Crear evento futuro
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
            category=self.category
        )

        # Crear evento pasado
        self.past_event = Event.objects.create(
            title="Evento pasado",
            description="Descripción del evento pasado",
            scheduled_at=timezone.now() - datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
            category=self.category
        )

    def test_cancel_event_as_organizer(self):
        """Test que verifica que un organizador puede cancelar un evento desde la interfaz"""
        # Iniciar sesión como organizador
        self.login_user("organizador_states", "password123")
        
        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")
        
        # Verificar que el evento está activo
        event_row = self.page.locator("table tbody tr").filter(has_text="Evento de prueba")
        expect(event_row.locator("td").nth(3)).to_have_text("ACTIVO")
        
        # Hacer clic en el botón de cancelar
        cancel_button = event_row.locator("form[action*='/cancel/'] button")
        expect(cancel_button).to_be_visible()
        cancel_button.click()
        
        # Verificar que el estado cambió a CANCELADO
        event_row = self.page.locator("table tbody tr").filter(has_text="Evento de prueba")
        expect(event_row.locator("td").nth(3)).to_have_text("CANCELADO")

    def test_edit_event_updates_state(self):
        """Test que verifica que editar un evento actualiza su estado en la interfaz"""
        # Iniciar sesión como organizador
        self.login_user("organizador_states", "password123")
        
        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")
        
        # Hacer clic en el botón de editar
        edit_button = self.page.locator("a[href*='/edit/']").first
        expect(edit_button).to_be_visible()
        edit_button.click()
        
        # Verificar que estamos en la página de edición
        expect(self.page).to_have_url(f"{self.live_server_url}/events/{self.event.id}/edit/")
        
        # Cambiar la fecha del evento
        future_date = (timezone.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        self.page.get_by_label("Fecha").fill(future_date)
        
        # Guardar los cambios
        self.page.get_by_role("button", name="Guardar Cambios").click()
        
        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")
        
        # Verificar que el estado cambió a REPROGRAMADO
        event_row = self.page.locator("table tbody tr").filter(has_text="Evento de prueba")
        expect(event_row.locator("td").nth(3)).to_have_text("REPROGRAMADO")

    def test_regular_user_cannot_cancel_event(self):
        """Test que verifica que un usuario regular no puede cancelar un evento"""
        # Iniciar sesión como usuario regular
        self.login_user("usuario_states", "password123")
        
        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")
        
        # Verificar que no hay botón de cancelar
        event_row = self.page.locator("table tbody tr").filter(has_text="Evento de prueba")
        expect(event_row.locator("form[action*='/cancel/']")).to_have_count(0)

    def test_event_states_display(self):
        """Test que verifica que los estados se muestran correctamente en la interfaz"""
        # Iniciar sesión como organizador
        self.login_user("organizador_states", "password123")
        
        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")
        
        # Verificar que el estado se muestra en la tabla
        event_row = self.page.locator("table tbody tr").filter(has_text="Evento de prueba")
        expect(event_row.locator("td").nth(3)).to_be_visible()
        expect(event_row.locator("td").nth(3)).to_have_text("ACTIVO")

    def test_past_event_shows_finished_state(self):
        """Test que verifica que un evento pasado no se muestra en la lista de eventos"""
        # Iniciar sesión como organizador
        self.login_user("organizador_states", "password123")
        
        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")
        
        # Verificar que el evento pasado no aparece en la lista
        event_row = self.page.locator("table tbody tr").filter(has_text="Evento pasado")
        expect(event_row).to_have_count(0) 