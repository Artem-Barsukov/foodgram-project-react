from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.pagination import LimitPagesPagination
from api.serializers import UserSerializer, SubscribeListSerializer

from .models import Follow, User


class CustomUserViewSet(UserViewSet):
    """Вьюсет пользователя."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = LimitPagesPagination
    permission_classes = (AllowAny,)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id):
        """Функция добавления и удаления подписки."""
        user = request.user
        author = get_object_or_404(User, pk=id)

        if request.method == 'POST':
            serializer = SubscribeListSerializer(
                author, data=request.data, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            Follow.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            try:
                follow = Follow.objects.get(user=user, author=author)
            except ObjectDoesNotExist:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """Функция вывода всех подписок."""
        user = request.user
        queryset = User.objects.filter(author__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeListSerializer(
            pages, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)
