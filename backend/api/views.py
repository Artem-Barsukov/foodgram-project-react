from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.status import (HTTP_201_CREATED, HTTP_204_NO_CONTENT,
                                   HTTP_400_BAD_REQUEST)
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.models import Follow, User

from .filters import IngredientNameFilter, RecipeFilter
from .pagination import LimitPagesPagination
from .permissions import AuthorOrReadOnly
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          RecipeReadSerializer, ShortViewRecipeSerializer,
                          SubscribeListSerializer, TagSerializer,
                          UserSerializer)
from .utils import download_cart


class TagViewSet(ReadOnlyModelViewSet):

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None


class IngredientsViewSet(ReadOnlyModelViewSet):

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (IngredientNameFilter, )
    pagination_class = None


class RecipeViewSet(ModelViewSet):

    permission_classes = (IsAuthenticatedOrReadOnly, AuthorOrReadOnly)
    pagination_class = LimitPagesPagination
    filterset_class = RecipeFilter
    filter_backends = (DjangoFilterBackend,)

    def get_queryset(self):
        queryset = (
            Recipe
            .objects
            .select_related('author')
            .prefetch_related('ingredients')
        )
        user = self.request.user
        if user.is_authenticated and self.action in ['list', 'retrieve']:
            queryset = queryset.annotate(
                is_favorited=Exists(Favorite.objects.filter(
                    recipe=OuterRef('pk'),
                    user=user)),
                is_in_shopping_cart=Exists(ShoppingCart.objects.filter(
                    recipe=OuterRef('pk'),
                    user=user)))
        return queryset

    def get_serializer_class(self):
        if self.request.method in ('POST', 'PATCH'):
            return RecipeCreateSerializer
        return RecipeReadSerializer

    def add_recipe(self, request, model, pk):

        recipe = get_object_or_404(Recipe, pk=pk)
        _, created = model.objects.get_or_create(
            recipe=recipe, user=request.user
        )
        if created:
            serializer = ShortViewRecipeSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(status=HTTP_400_BAD_REQUEST)

    def delete_recipe(self, user, model, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        obj = model.objects.filter(
            user=user, recipe=recipe
        )
        if not obj.exists():
            return Response(status=HTTP_400_BAD_REQUEST)
        obj.delete()
        return Response(status=HTTP_204_NO_CONTENT)

    @action(
        methods=['POST'],
        url_path='favorite',
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        return self.add_recipe(request, Favorite, pk)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self.delete_recipe(request.user, Favorite, pk)

    @action(
        methods=['POST'],
        url_path='shopping_cart',
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        return self.add_recipe(request, ShoppingCart, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.delete_recipe(request.user, ShoppingCart, pk)

    @action(
        methods=['GET'],
        url_path='download_shopping_cart',
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        user = request.user
        return download_cart(user)


class UserViewSet(DjoserUserViewSet):

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
        methods=['POST'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, pk=id)
        serializer = SubscribeListSerializer(
            author, data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        Follow.objects.create(user=user, author=author)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, pk=id)
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
        user = request.user
        queryset = User.objects.filter(author__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeListSerializer(
            pages, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)
