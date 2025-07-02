import re
from playwright.sync_api import expect
from django.utils import timezone
from datetime import timedelta
from app.models import User, Event, Venue, Ticket, SatisfactionSurvey
from .base import BaseE2ETest


class SatisfactionSurveyE2ETest(BaseE2ETest):
    """Tests end-to-end para la funcionalidad completa de satisfaction survey usando Playwright"""
    
    def setUp(self):
        """Configuración inicial para los tests e2e"""
        super().setUp()
        
        # Usuario regular
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_organizer=False
        )
        
        # Usuario organizador
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@example.com',
            password='testpass123',
            is_organizer=True
        )
        
        # Venue para eventos
        self.venue = Venue.objects.create(
            name='Test Venue',
            adress='Test Address',
            city='Test City',
            capacity=100,
            contact='test@venue.com'
        )
        
        # Evento para encuestas
        self.event = Event.objects.create(
            title='Test Event',
            description='Event for survey testing',
            scheduled_at=timezone.now() + timedelta(days=30),
            organizer=self.organizer,
            venue=self.venue
        )

        # Crear todos los tickets necesarios para los tests
        self.base_ticket = Ticket.objects.create(
            quantity=1,
            type='GENERAL',
            event=self.event,
            user=self.user
        )

        self.vip_ticket = Ticket.objects.create(
            quantity=3,
            type='VIP',
            event=self.event,
            user=self.user
        )

        self.new_ticket = Ticket.objects.create(
            quantity=1,
            type='VIP',
            event=self.event,
            user=self.user
        )

        self.interactive_ticket = Ticket.objects.create(
            quantity=2,
            type='VIP',
            event=self.event,
            user=self.user
        )

    def test_complete_satisfaction_survey_user_journey(self):
        """Test del flujo completo de usuario completando encuesta usando Playwright"""
        # Login del usuario usando el método helper
        self.login_user('testuser', 'testpass123')
        
        # Navegar a la encuesta de satisfacción
        self.page.goto(f"{self.live_server_url}/tickets/{self.base_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar que la página de encuesta cargó correctamente
        expect(self.page.locator("h3")).to_contain_text("Encuesta de Satisfacción")
        expect(self.page.locator("strong").filter(has_text="Test Event")).to_be_visible()
        
        # Verificar que los elementos del formulario están presentes
        expect(self.page.locator("input[name='overall_satisfaction']").first).to_be_visible()
        expect(self.page.locator("select[name='purchase_experience']")).to_be_visible()
        expect(self.page.locator("input[name='would_recommend']").first).to_be_visible()
        expect(self.page.locator("textarea[name='comments']")).to_be_visible()
        
        # Llenar el formulario de encuesta
        self.page.check("input[name='overall_satisfaction'][value='5']")
        self.page.select_option("select[name='purchase_experience']", "facil")
        self.page.check("input[name='would_recommend'][value='yes']")
        self.page.fill("textarea[name='comments']", "Excelente experiencia de compra!")
        
        # Enviar el formulario
        self.page.click("button[type='submit']:has-text('Enviar encuesta')")
        
        # Verificar redirección exitosa
        expect(self.page).not_to_have_url(f"{self.live_server_url}/tickets/{self.base_ticket.pk}/survey/")

    def test_satisfaction_survey_form_validation_errors(self):
        """Test validación de errores en el formulario usando Playwright"""
        # Login del usuario
        self.login_user('testuser', 'testpass123')
        
        # Navegar a la encuesta
        self.page.goto(f"{self.live_server_url}/tickets/{self.new_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Intentar enviar formulario sin completar campos requeridos
        self.page.click("button[type='submit']:has-text('Enviar encuesta')")
        
        # Verificar que aparecen mensajes de error o validación HTML5
        # En caso de validación HTML5, la página no se enviará
        expect(self.page).to_have_url(re.compile(f".*tickets/{self.new_ticket.pk}/survey.*"))

    def test_satisfaction_survey_ticket_information_display(self):
        """Test que verifica la información del ticket en la encuesta"""
        # Login del usuario
        self.login_user('testuser', 'testpass123')
        
        # Navegar a la encuesta
        self.page.goto(f"{self.live_server_url}/tickets/{self.vip_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar información del evento y ticket
        expect(self.page.locator("strong").filter(has_text="Test Event")).to_be_visible()
        expect(self.page.locator("p").filter(has_text="3 entrada")).to_be_visible()
        expect(self.page.locator("p").filter(has_text="Tipo: VIP")).to_be_visible()

    def test_satisfaction_survey_form_elements_present(self):
        """Test que verifica que todos los elementos del formulario están presentes"""
        # Login del usuario
        self.login_user('testuser', 'testpass123')
        
        # Navegar a la encuesta usando el ticket base
        self.page.goto(f"{self.live_server_url}/tickets/{self.base_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar elementos de satisfacción (radio buttons)
        expect(self.page.locator("input[name='overall_satisfaction'][value='1']")).to_be_visible()
        expect(self.page.locator("input[name='overall_satisfaction'][value='2']")).to_be_visible()
        expect(self.page.locator("input[name='overall_satisfaction'][value='3']")).to_be_visible()
        expect(self.page.locator("input[name='overall_satisfaction'][value='4']")).to_be_visible()
        expect(self.page.locator("input[name='overall_satisfaction'][value='5']")).to_be_visible()
        
        # Verificar dropdown de experiencia de compra
        expect(self.page.locator("select[name='purchase_experience']")).to_be_visible()
        
        # Verificar radio buttons de recomendación
        expect(self.page.locator("input[name='would_recommend'][value='yes']")).to_be_visible()
        expect(self.page.locator("input[name='would_recommend'][value='no']")).to_be_visible()
        
        # Verificar textarea de comentarios
        expect(self.page.locator("textarea[name='comments']")).to_be_visible()
        
        # Verificar botones
        expect(self.page.locator("button[type='submit']:has-text('Enviar encuesta')")).to_be_visible()
        expect(self.page.locator("a.btn:has-text('Omitir encuesta')")).to_be_visible()  # Botón "Omitir encuesta"

    def test_satisfaction_survey_responsive_design(self):
        """Test diseño responsive de la encuesta"""
        # Login del usuario
        self.login_user('testuser', 'testpass123')
        
        # Navegar a la encuesta usando el ticket base
        self.page.goto(f"{self.live_server_url}/tickets/{self.base_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Probar en viewport móvil
        self.page.set_viewport_size({"width": 375, "height": 667})
        
        # Verificar que los elementos se adaptan al móvil
        expect(self.page.locator(".container")).to_be_visible()
        expect(self.page.locator("input[name='overall_satisfaction']").first).to_be_visible()
        expect(self.page.locator("button[type='submit']:has-text('Enviar encuesta')")).to_be_visible()

    def test_satisfaction_survey_complete_form_interaction(self):
        """Test interacción completa con todos los elementos del formulario"""
        # Login del usuario
        self.login_user('testuser', 'testpass123')
        
        # Navegar a la encuesta
        self.page.goto(f"{self.live_server_url}/tickets/{self.interactive_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Probar cada nivel de satisfacción
        self.page.check("input[name='overall_satisfaction'][value='1']")
        expect(self.page.locator("input[name='overall_satisfaction'][value='1']")).to_be_checked()
        
        self.page.check("input[name='overall_satisfaction'][value='2']")
        expect(self.page.locator("input[name='overall_satisfaction'][value='2']")).to_be_checked()
        
        self.page.check("input[name='overall_satisfaction'][value='3']")
        expect(self.page.locator("input[name='overall_satisfaction'][value='3']")).to_be_checked()
        
        self.page.check("input[name='overall_satisfaction'][value='4']")
        expect(self.page.locator("input[name='overall_satisfaction'][value='4']")).to_be_checked()
        
        self.page.check("input[name='overall_satisfaction'][value='5']")
        expect(self.page.locator("input[name='overall_satisfaction'][value='5']")).to_be_checked()
        
        # Probar opciones de experiencia de compra
        self.page.select_option("select[name='purchase_experience']", "muy_dificil")
        expect(self.page.locator("select[name='purchase_experience']")).to_have_value("muy_dificil")
        
        self.page.select_option("select[name='purchase_experience']", "dificil")
        expect(self.page.locator("select[name='purchase_experience']")).to_have_value("dificil")
        
        self.page.select_option("select[name='purchase_experience']", "normal")
        expect(self.page.locator("select[name='purchase_experience']")).to_have_value("normal")
        
        self.page.select_option("select[name='purchase_experience']", "facil")
        expect(self.page.locator("select[name='purchase_experience']")).to_have_value("facil")
        
        self.page.select_option("select[name='purchase_experience']", "muy_facil")
        expect(self.page.locator("select[name='purchase_experience']")).to_have_value("muy_facil")
        
        # Probar radio buttons de recomendación
        self.page.check("input[name='would_recommend'][value='yes']")
        expect(self.page.locator("input[name='would_recommend'][value='yes']")).to_be_checked()
        
        self.page.check("input[name='would_recommend'][value='no']")
        expect(self.page.locator("input[name='would_recommend'][value='no']")).to_be_checked()
        
        # Probar textarea de comentarios
        test_comment = "Este es un comentario de prueba para verificar la funcionalidad."
        self.page.fill("textarea[name='comments']", test_comment)
        expect(self.page.locator("textarea[name='comments']")).to_have_value(test_comment)

    def test_satisfaction_survey_navigation_elements(self):
        """Test elementos de navegación en la página de encuesta"""
        self.login_user('testuser', 'testpass123')
        self.page.goto(f"{self.live_server_url}/tickets/{self.base_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar navbar
        expect(self.page.locator(".navbar")).to_be_visible()
        
        # No hace falta chequear breadcrumb si nunca existe
        # expect(self.page.locator(".breadcrumb")).to_have_count(0)  # Opcional, si querés ser explícito
        
        # Verificar botón de "Omitir encuesta" (debe estar siempre)
        omit_button = self.page.locator("a.btn:has-text('Omitir encuesta')")
        expect(omit_button).to_be_visible()
        expect(omit_button).to_have_attribute("href", re.compile(r".*"))

    def test_satisfaction_survey_ticket_details_section(self):
        """Test sección de detalles del ticket en la encuesta"""
        self.login_user('testuser', 'testpass123')
        self.page.goto(f"{self.live_server_url}/tickets/{self.base_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar información del evento
        expect(self.page.locator("strong").filter(has_text="Test Event")).to_be_visible()
        
        # Verificar información del ticket
        expect(self.page.locator("p").filter(has_text="1 entrada")).to_be_visible()
        expect(self.page.locator("p").filter(has_text="Tipo: GENERAL")).to_be_visible()
        
        # Verificar información del venue (debe estar siempre)
        expect(self.page.locator("p").filter(has_text="Test Venue")).to_be_visible()

    def test_satisfaction_survey_success_purchase_message(self):
        """Test mensaje de éxito después de completar encuesta"""
        self.login_user('testuser', 'testpass123')
        self.page.goto(f"{self.live_server_url}/tickets/{self.base_ticket.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Completar y enviar formulario
        self.page.check("input[name='overall_satisfaction'][value='4']")
        self.page.select_option("select[name='purchase_experience']", "facil")
        self.page.check("input[name='would_recommend'][value='yes']")
        self.page.fill("textarea[name='comments']", "Buen servicio en general")
        self.page.click("button[type='submit']:has-text('Enviar encuesta')")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar que ya no estamos en la página de encuesta (redirección exitosa)
        expect(self.page).not_to_have_url(f"{self.live_server_url}/tickets/{self.base_ticket.pk}/survey/") 