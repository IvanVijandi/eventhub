from django.test import TestCase, Client
from django.urls import reverse
from app.models import User, Event, Venue, Ticket, SatisfactionSurvey
from django.utils import timezone
from datetime import timedelta


class SatisfactionSurveyIntegrationTest(TestCase):
    """Tests de integración para la funcionalidad de satisfaction survey"""
    
    def setUp(self):
        """Configuración inicial para los tests de integración"""
        self.client = Client()
        
        # Usuario regular
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
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
        
        # Ticket para encuesta
        self.ticket = Ticket.objects.create(
            quantity=2,
            type='GENERAL',
            event=self.event,
            user=self.user
        )

    def test_user_completes_satisfaction_survey(self):
        """Test que verifica que un usuario puede completar una encuesta de satisfacción"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        # Acceder al formulario de encuesta
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.ticket.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Encuesta de Satisfacción')
        
        # Enviar formulario con datos válidos
        form_data = {
            'overall_satisfaction': 5,
            'purchase_experience': 'facil',
            'would_recommend': 'yes',
            'comments': 'Excelente experiencia de compra'
        }
        
        response = self.client.post(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.ticket.id}),
            data=form_data
        )
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        
        # Verificar que la encuesta se creó
        survey = SatisfactionSurvey.objects.get(ticket=self.ticket)
        self.assertEqual(survey.overall_satisfaction, 5)
        self.assertEqual(survey.purchase_experience, 'facil')
        self.assertTrue(survey.would_recommend)
        self.assertEqual(survey.comments, 'Excelente experiencia de compra')

    def test_organizer_views_survey_results(self):
        """Test que verifica que un organizador puede ver los resultados de las encuestas"""
        # Crear una encuesta de satisfacción
        SatisfactionSurvey.objects.create(
            ticket=self.ticket,
            user=self.user,
            event=self.event,
            overall_satisfaction=5,
            purchase_experience='facil',
            would_recommend=True,
            comments='Excelente experiencia de compra!'
        )
        
        # Login como organizador
        self.client.login(username='organizer', password='testpass123')
        
        # Acceder al dashboard de resultados
        response = self.client.get(
            reverse('survey_results', kwargs={'event_id': self.event.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resultados de Encuestas de Satisfaccion')
        self.assertContains(response, 'Excelente experiencia de compra!') 