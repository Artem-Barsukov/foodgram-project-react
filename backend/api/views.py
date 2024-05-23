from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.status import (HTTP_201_CREATED, HTTP_204_NO_CONTENT,
                                   HTTP_400_BAD_REQUEST)
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag

from .filters import IngredientNameFilter, RecipeFilter
from .pagination import LimitPagesPagination
from .permissions import AuthorOrReadOnly
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          RecipeReadSerializer, ShortViewRecipeSerializer,
                          TagSerializer)
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
        queryset = Recipe.objects.select_related('author').prefetch_related(
            'ingredients').all()
        user = self.request.user
        if user.is_authenticated:
            if self.action in ['list', 'retrieve']:
                favorited = Favorite.objects.filter(recipe=OuterRef('pk'),
                                                    user=user)
                cart = ShoppingCart.objects.filter(recipe=OuterRef('pk'),
                                                   user=user)
                queryset = queryset.annotate(is_favorited=Exists(favorited),
                                             is_in_shopping_cart=Exists(cart))
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
        methods=('POST', 'DELETE'),
        url_path='favorite',
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.add_recipe(request, Favorite, pk)
        return self.delete_recipe(request.user, Favorite, pk)

    @action(
        methods=('POST', 'DELETE'),
        url_path='shopping_cart',
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self.add_recipe(request, ShoppingCart, pk)
        return self.delete_recipe(request.user, ShoppingCart, pk)

    @action(
        methods=('GET',),
        url_path='download_shopping_cart',
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        user = request.user
        return download_cart(user)
