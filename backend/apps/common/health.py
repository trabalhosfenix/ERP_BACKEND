from django.http import JsonResponse
from django.db import connection
from .redis import get_redis

def health(request):
    db_ok = True
    redis_ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        db_ok = False

    try:
        get_redis().ping()
    except Exception:
        redis_ok = False

    ok = db_ok and redis_ok
    return JsonResponse(
        {'status': 'ok' if ok else 'fail', 'database': db_ok, 'redis': redis_ok},
        status=200 if ok else 500,
    )
