from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from talentwright.users.models import User

from .serializers import UserSerializer

from rest_framework.permissions import AllowAny


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_queryset(self, *args, **kwargs):
        assert isinstance(self.request.user.id, int)
        return self.queryset.filter(id=self.request.user.id)

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    # @action(detail=False, methods=["get"])
    # def health(self, request):
    #     return Response({"status": "ok"})

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[AllowAny],
    )
    def health(self, request):
        return Response({"status": "ok"})
            
    @action(detail=False, methods=["get"])
    def whoami(self, request):
        return Response({
            "id": request.user.id,
            "email": request.user.email,
            "name": request.user.name,
        })