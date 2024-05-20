from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from foodgram.constants import MIN_INGREDIENT
from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (ModelSerializer,
                                        PrimaryKeyRelatedField,
                                        SerializerMethodField)
from users.models import User


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор создания пользователя."""

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )


class CustomUserSerializer(UserSerializer):
    """Сериализатор пользователя."""

    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        """Проверка подписки на автора."""
        user = self.context.get('request').user
        return (user.is_authenticated
                and user.follower.filter(author=obj).exists())


class SubscribeListSerializer(CustomUserSerializer):
    """Сериализатор подписок."""

    recipes_count = SerializerMethodField()
    recipes = SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count',
        )
        read_only_fields = ('email', 'username', 'first_name', 'last_name')

    def validate(self, data):
        """Валидация подписки."""
        author_id = self.context.get(
            'request').parser_context.get('kwargs').get('id')
        author = get_object_or_404(User, id=author_id)
        user = self.context.get('request').user
        if user.follower.filter(author=author_id).exists():
            raise ValidationError('Подписка уже существует')
        if user == author:
            raise ValidationError('Нельзя подписаться на самого себя')
        return data

    def get_recipes(self, obj):
        """Метод для получения списка рецептов автора."""
        request = self.context.get('request')
        recipes = obj.recipes.all()
        limit = request.GET.get('recipes_limit')
        if limit:
            recipes = recipes[: int(limit)]
        return ShortViewRecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        """Метод для получения количества рецептов автора."""
        return obj.recipes.count()


class ShortViewRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого представления рецепта."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(ModelSerializer):
    """Сериализатор ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиента в рецепте."""

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(ModelSerializer):
    """Сериализатор чтения рецепта."""

    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        read_only=True, many=True, source='ingredients_recipe'
    )
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        """Возвращает избранные."""
        user = self.context.get('request').user
        return (user.is_authenticated
                and obj.favorites.filter(recipe=obj).exists())

    def get_is_in_shopping_cart(self, obj):
        """Возвращает карту покупок."""
        user = self.context.get('request').user
        return (user.is_authenticated
                and obj.shopping_cart.filter(recipe=obj).exists())


class IngredientForRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов для рецепта."""

    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=MIN_INGREDIENT)

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeCreateSerializer(ModelSerializer):
    """Сериализатор создания и редактирования рецепта."""

    ingredients = IngredientForRecipeSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('author',)

    def validate_image(self, image):
        if not image:
            raise ValidationError(
                'Поле image не может быть пустым'
            )
        return image

    def validate_tags(self, tags):
        """Валидация тэгов."""
        if not tags:
            raise serializers.ValidationError(
                'Нужно указать как минимум 1 тэг'
            )
        uniqe_tags = set(tag.id for tag in tags)
        if len(tags) != len(uniqe_tags):
            raise serializers.ValidationError(
                'Тэги в рецепте не должны повторяться')
        return tags

    def validate(self, attrs):
        tags = self.initial_data.get('tags')
        ingredients = self.initial_data.get('ingredients')
        if not tags or not ingredients:
            raise ValidationError('Отсутствуют обязательные поля!')
        ingredients = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients) != len(set(ingredients)):
            raise ValidationError(
                'Нельзя указывать одинаковые ингредиенты!'
            )
        if len(tags) != len(set(tags)):
            raise ValidationError(
                'Нельзя указывать одинаковые теги!'
            )
        if not self.initial_data.get('text'):
            raise ValidationError(
                'Нельзя создать рецепт без текста!'
            )
        return super().validate(attrs)

    def add_ingredients(self, ingredients, recipe):
        """Добавление ингредиентов в рецепт."""
        ingredient_list = []
        for ingredient in ingredients:
            current_ingredient = ingredient.get('id')
            amount = ingredient.get('amount')
            ingredient_list.append(
                IngredientRecipe(
                    recipe=recipe,
                    ingredient=current_ingredient,
                    amount=amount
                )
            )
        IngredientRecipe.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        """Создание рецепта."""
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context.get('request').user,
            **validated_data
        )
        self.add_ingredients(ingredients, recipe)
        recipe.tags.set(tags)
        recipe.save()
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance.name = validated_data.get('name')
        instance.text = validated_data.get('text')
        instance.cooking_time = validated_data.get('cooking_time')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.ingredients.clear()
        if validated_data.get('image') is not None:
            instance.image = validated_data.pop('image')
        instance.save()
        self.add_ingredients(ingredients, instance)
        instance.tags.set(tags)
        return instance

    def to_representation(self, instance):
        """Обновленный рецепт."""
        return RecipeReadSerializer(instance, context=self.context).data
