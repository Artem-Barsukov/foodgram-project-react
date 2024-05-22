from rest_framework.pagination import PageNumberPagination


class LimitPagesPagination(PageNumberPagination):
    """Переопределяем название поля."""

    page_size_query_param = 'limit'
