from rest_framework.pagination import PageNumberPagination


class LimitPagesPagination(PageNumberPagination):
    """Redefining the field name."""

    page_size_query_param = 'limit'
