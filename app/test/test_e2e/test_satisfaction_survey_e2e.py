import re
from playwright.sync_api import expect
from django.utils import timezone
from datetime import timedelta
from app.models import User, Event, Venue, Ticket, SatisfactionSurvey
from .base import BaseE2ETest


class SatisfactionSurveyE2ETest(BaseE2ETest):
    """Tests end-to-end para la funcionalidad de encuesta de satisfacción usando Playwright"""
    
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
            organizer=self.organizer,  # Usar el organizador que ya existe en BaseE2ETest
            venue=self.venue
        )

        # Ticket para encuesta (usado para el test de resultados)
        self.ticket = Ticket.objects.create(
            quantity=1,
            type='GENERAL',
            event=self.event,
            user=self.user
        )

        # Ticket adicional para el test de completar encuesta
        self.ticket_for_survey = Ticket.objects.create(
            quantity=2,
            type='VIP',
            event=self.event,
            user=self.user
        )

        # Encuesta de satisfacción para tests (usando el primer ticket)
        self.survey = SatisfactionSurvey.objects.create(
            ticket=self.ticket,
            user=self.user,
            event=self.event,
            overall_satisfaction=5,
            purchase_experience='facil',
            would_recommend=True,
            comments='Excelente experiencia de compra!'
        )

    def test_user_completes_satisfaction_survey(self):
        """Test que verifica que un usuario puede completar una encuesta de satisfacción"""
        # Login del usuario
        self.login_user('testuser', 'testpass123')
        
        # Navegar a la encuesta de satisfacción
        self.page.goto(f"{self.live_server_url}/tickets/{self.ticket_for_survey.pk}/survey/")
        self.page.wait_for_load_state("networkidle")
        
        # Verificar que la página de encuesta cargó correctamente
        expect(self.page.locator("h3")).to_contain_text("Encuesta de Satisfacción")
        expect(self.page.locator("strong").filter(has_text="Test Event")).to_be_visible()
        
        # Completar el formulario de encuesta
        self.page.check("input[name='overall_satisfaction'][value='5']")
        self.page.select_option("select[name='purchase_experience']", "facil")
        self.page.check("input[name='would_recommend'][value='yes']")
        self.page.fill("textarea[name='comments']", "Excelente experiencia de compra!")
        
        # Enviar el formulario
        self.page.click("button[type='submit']:has-text('Enviar encuesta')")
        
        # Verificar redirección exitosa
        expect(self.page).not_to_have_url(f"{self.live_server_url}/tickets/{self.ticket_for_survey.pk}/survey/")

    def test_organizer_views_survey_results(self):
        """Test que verifica que un organizador puede ver los resultados de las encuestas"""
        # Login como organizador
        self.login_user('organizador', 'password123')

        # Navegar al dashboard de resultados
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/survey-results/")
        self.page.wait_for_load_state("networkidle")

        # Verificar que se muestran los resultados (más flexible)
        expect(self.page.locator("h3").filter(has_text="Resultados")).to_be_visible()
        expect(self.page.locator("text=Excelente experiencia de compra!")).to_be_visible() 