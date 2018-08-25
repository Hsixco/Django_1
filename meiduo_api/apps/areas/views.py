from rest_framework.viewsets import ModelViewSet,ReadOnlyModelViewSet
from .models import Area
from .serializers import AreaSerializer,SubAreaSerializer


class AreasViewSet(ReadOnlyModelViewSet):
    pagination_class = None

    def get_queryset(self):
        if self.action == 'list':
            return Area.objects.filter(parents=None)
        else:
            return Area.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return AreaSerializer
        else:
            return SubAreaSerializer