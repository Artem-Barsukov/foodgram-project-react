from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import OuterRef

from colorfield.fields import ColorField

from foodgram.constants import (MAX_LENGHT_COLOR, MAX_LENGHT_RECIPES,
                                MIN_COOKING_TIME, MIN_INGREDIENT)
from users.models import User


class Tag(models.Model):

    name = models.CharField(
        max_length=MAX_LENGHT_RECIPES,
        verbose_name='Название тэга',
        unique=True
    )
    color = ColorField(
        format='hex',
        max_length=MAX_LENGHT_COLOR,
        verbose_name='Цвет тэга',
        unique=True,
    )
    slug = models.SlugField(
        max_length=MAX_LENGHT_RECIPES,
        verbose_name='Слаг тэга',
        unique=True,
    )

    def __str__(self):
        return self.name


class Ingredient(models.Model):

    name = models.CharField(
        max_length=MAX_LENGHT_RECIPES,
        verbose_name='Название ингредиента',
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGHT_RECIPES,
        verbose_name='Единица измерения'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Aвтор рецепта',
        related_name='recipes',
    )
    name = models.CharField(
        max_length=MAX_LENGHT_RECIPES,
        verbose_name='Название рецепта'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах',
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message='Минимальное время приготовления в минутах'
                f'{MIN_COOKING_TIME}')
        ]
    )
    text = models.TextField(verbose_name='Описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        verbose_name='Список ингредиентов'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэги'
    )
    image = models.ImageField(
        verbose_name='Вкусная картинка',
        upload_to='recipes/images/',
        default=None,
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredients_recipe'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients_recipe'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='количество',
        validators=[
            MinValueValidator(
                MIN_INGREDIENT,
                message='Значение не может быть меньше'
                f'{MIN_INGREDIENT}')
        ]
    )

    def __str__(self):
        return f'{self.ingredient} {self.recipe}'


class FavoriteQuerySet(models.QuerySet):

    def get_favorited(self, user):
        return self.filter(recipe=OuterRef('pk'), user=user)


class Favorite(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )

    objects = FavoriteQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self):
        return f'{self.user} {self.recipe}'


class ShoppingCartQuerySet(models.QuerySet):

    def get_cart(self, user):
        return self.filter(recipe=OuterRef('pk'), user=user)


class ShoppingCart(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart'
    )

    objects = ShoppingCartQuerySet.as_manager()

    def __str__(self):
        return f'{self.user} {self.recipe}'
