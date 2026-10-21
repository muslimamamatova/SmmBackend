"""
Хуки для генератора OpenAPI-схемы (drf-spectacular).

Подключаются в settings.SPECTACULAR_SETTINGS['PREPROCESSING_HOOKS'].
"""


def strip_api_v1_prefix(endpoints, **kwargs):
    """Убирает префикс «/api/v1» из путей, которые показываются в документации.

    Зачем это нужно: реальная маршрутизация (config/urls.py) держит
    административное API под /api/v1/, чтобы его адреса не конфликтовали с
    админкой Django на /admin/. Но в Swagger удобнее видеть короткие пути,
    поэтому перед отрисовкой схемы префикс срезается.

    Аргументы:
        endpoints: список кортежей (path, path_regex, method, callback),
            который drf-spectacular собрал из маршрутов проекта.

    Возвращает:
        Такой же список, но с укороченными путями. На работу самого API
        это не влияет — меняется только отображение.
    """
    cleaned = []
    for path, path_regex, method, callback in endpoints:
        if path.startswith('/api/v1/'):
            # Отрезаем ровно '/api/v1', оставляя ведущий слеш следующего сегмента.
            path = path[len('/api/v1'):]
        cleaned.append((path, path_regex, method, callback))
    return cleaned
