from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def api_status(request):
    """API status endpoint"""
    return Response({
        'message': '🚀 NexusPM Enterprise API is running!',
        'status': 'operational',
        'version': '1.0.0',
        'docs': '/api/docs/'
    })

urlpatterns = [
    path('', api_status, name='api_status'),
]