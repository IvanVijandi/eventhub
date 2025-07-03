from django.test import TestCase, Client
from django.urls import reverse
from app.models import User, Event, Venue
from django.utils import timezone
from datetime import timedelta


class CountdownIntegrationTest(TestCase):
    """Tests de integración para la funcionalidad de countdown"""
    
    def setUp(self):
        """Configuración inicial para los tests de integración"""
        self.client = Client()
        
        # Usuario regular (NO organizador)
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
        
        # Evento futuro para countdown
        self.future_event = Event.objects.create(
            title='Future Event',
            description='Event for countdown testing',
            scheduled_at=timezone.now() + timedelta(days=30),
            organizer=self.organizer,
            venue=self.venue
        )

    def test_countdown_visible_for_regular_user(self):
        """Test que el countdown es visible para usuarios regulares"""
        # Login como usuario regular
        self.client.login(username='testuser', password='testpass123')
        
        # Acceder al detalle del evento
        response = self.client.get(
            reverse('event_detail', kwargs={'event_id': self.future_event.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['user_is_organizer'])
        self.assertContains(response, 'countdown-container')

    def test_countdown_not_visible_for_organizer(self):
        """Test que el countdown NO es visible para organizadores"""
        # Login como organizador
        self.client.login(username='organizer', password='testpass123')
        
        # Acceder al detalle del evento
        response = self.client.get(
            reverse('event_detail', kwargs={'event_id': self.future_event.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user_is_organizer'])
        self.assertNotContains(response, 'countdown-container')

 