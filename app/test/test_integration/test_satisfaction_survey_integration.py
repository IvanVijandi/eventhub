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

        # Otro usuario para tests de permisos
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
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
        
        # Tickets para diferentes tests
        self.ticket = Ticket.objects.create(
            quantity=2,
            type='GENERAL',
            event=self.event,
            user=self.user
        )

        self.vip_ticket = Ticket.objects.create(
            quantity=1,
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

        # Crear encuesta base para tests que la requieran
        self.existing_survey = SatisfactionSurvey.objects.create(
            ticket=self.ticket,
            user=self.user,
            event=self.event,
            overall_satisfaction=4,
            purchase_experience='facil',
            would_recommend=True
        )

    def test_satisfaction_survey_form_display(self):
        """Test que el formulario de encuesta se muestra correctamente"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        # Acceder al formulario de encuesta
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id})
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que el formulario está presente
        self.assertContains(response, 'Encuesta de Satisfacción')
        self.assertContains(response, 'overall_satisfaction')
        self.assertContains(response, 'purchase_experience')
        self.assertContains(response, 'would_recommend')
        self.assertContains(response, 'comments')
        
        # Verificar elementos del formulario
        self.assertContains(response, 'form-control')
        self.assertContains(response, 'btn btn-primary')

    def test_satisfaction_survey_form_submission_success(self):
        """Test envío exitoso del formulario de encuesta"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        # Datos válidos para la encuesta
        form_data = {
            'overall_satisfaction': 5,
            'purchase_experience': 'facil',
            'would_recommend': 'yes',
            'comments': 'Excelente experiencia de compra'
        }
        
        # Enviar formulario
        response = self.client.post(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id}),
            data=form_data
        )
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        
        # Verificar que la encuesta se creó
        survey = SatisfactionSurvey.objects.get(ticket=self.vip_ticket)
        self.assertEqual(survey.overall_satisfaction, 5)
        self.assertEqual(survey.purchase_experience, 'facil')
        self.assertTrue(survey.would_recommend)
        self.assertEqual(survey.comments, 'Excelente experiencia de compra')

    def test_satisfaction_survey_form_validation_errors(self):
        """Test validación de errores en el formulario"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        # Datos inválidos
        form_data = {
            'overall_satisfaction': '',  # Campo requerido vacío
            'purchase_experience': '',   # Campo requerido vacío
            'would_recommend': '',       # Campo requerido vacío
            'comments': 'x' * 501        # Muy largo
        }
        
        # Enviar formulario con errores
        response = self.client.post(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id}),
            data=form_data
        )
        
        # Debe mostrar el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debes seleccionar')

    def test_satisfaction_survey_duplicate_prevention(self):
        """Test prevención de encuestas duplicadas usando la encuesta base del setUp"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        # Intentar acceder nuevamente al formulario de ticket que ya tiene encuesta
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.ticket.id})
        )
        
        # Debe redirigir o mostrar mensaje de encuesta ya completada
        self.assertIn(response.status_code, [302, 200])
        self.assertTrue(
            response.status_code == 302 or 'ya has completado' in response.content.decode()
        )

    def test_satisfaction_survey_authentication_required(self):
        """Test que se requiere autenticación para acceder a la encuesta"""
        # Sin login
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.ticket.id})
        )
        
        # Debe redirigir al login
        self.assertEqual(response.status_code, 302)

    def test_satisfaction_survey_ticket_ownership(self):
        """Test que solo el dueño del ticket puede hacer la encuesta"""
        # Login con otro usuario
        self.client.login(username='otheruser', password='testpass123')
        
        # Intentar acceder a encuesta de ticket ajeno
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.ticket.id})
        )
        
        # Debe denegar acceso
        self.assertIn(response.status_code, [403, 404])

    def test_satisfaction_survey_context_variables(self):
        """Test variables de contexto en el template"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id})
        )
        
        # Verificar variables de contexto
        self.assertEqual(response.context['ticket'], self.vip_ticket)
        self.assertEqual(response.context['event'], self.event)

    def test_satisfaction_survey_redirect_after_purchase(self):
        """Test redirección a encuesta después de comprar ticket"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        # Simular redirección desde proceso de compra
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id}) + '?from=purchase'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Encuesta de Satisfacción')

    def test_satisfaction_survey_template_inheritance(self):
        """Test que el template hereda correctamente de base.html"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id})
        )
        
        # Verificar elementos comunes del template base
        self.assertContains(response, 'navbar')  # Navigation bar
        self.assertContains(response, 'container')     # Bootstrap container

    def test_satisfaction_survey_responsive_design(self):
        """Test diseño responsive de la encuesta"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id})
        )
        
        # Verificar clases Bootstrap para responsive design
        self.assertContains(response, 'col-md')     # Grid responsive
        self.assertContains(response, 'container')  # Container responsive

    def test_satisfaction_survey_form_fields_validation(self):
        """Test validación específica de campos del formulario"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        # Test con satisfacción fuera de rango
        form_data = {
            'overall_satisfaction': 6,   # Fuera de rango 1-5
            'purchase_experience': 'facil',
            'would_recommend': 'yes',
        }
        
        response = self.client.post(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id}),
            data=form_data
        )
        
        # Debe mostrar error de validación
        self.assertEqual(response.status_code, 200)

    def test_satisfaction_survey_success_message(self):
        """Test mensaje de éxito después de enviar encuesta"""
        # Login del usuario
        self.client.login(username='testuser', password='testpass123')
        
        # Datos válidos
        form_data = {
            'overall_satisfaction': 4,
            'purchase_experience': 'facil',
            'would_recommend': 'yes',
            'comments': 'Buen servicio'
        }
        
        # Enviar formulario
        response = self.client.post(
            reverse('satisfaction_survey', kwargs={'ticket_id': self.vip_ticket.id}),
            data=form_data,
            follow=True  # Seguir redirección
        )
        
        # Verificar mensaje de éxito
        self.assertContains(response, '¡Gracias por completar la encuesta de satisfacción!') 