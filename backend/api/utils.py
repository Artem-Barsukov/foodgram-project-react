from io import BytesIO

from django.db.models import F, Sum
from django.http import FileResponse

from recipes.models import IngredientRecipe, Recipe


def download_cart(user):
    """Download the shopping list."""
    recipes = Recipe.objects.filter(shopping_cart__user=user)
    shopping_cart = IngredientRecipe.objects.filter(
        recipe__in=recipes).values(
        name=F('ingredient__name'),
        units=F('ingredient__measurement_unit')).order_by(
        'ingredient__name').annotate(total=Sum('amount'))
    ingr_list = []
    for recipe in shopping_cart:
        ingr_list.append(recipe)
    shopping_list = 'Купить в магазине:\n'
    for ingredient in shopping_cart:
        shopping_list += (
            f'{ingredient["name"]}: '
            f'{ingredient["total"]}'
            f'{ingredient["units"]}.\n')
    buffer = BytesIO(shopping_list.encode('utf8'))
    return FileResponse(buffer, filename='shopping_list.txt',
                        as_attachment=True)
