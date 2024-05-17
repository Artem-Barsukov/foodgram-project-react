"""Пагинация страниц."""
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Переопределяем название поля."""

    page_size_query_param = 'limit'
