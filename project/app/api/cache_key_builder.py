from starlette.requests import Request
from starlette.responses import Response


def request_key_builder(
    func,
    *args,
    namespace: str = "",
    request: Request = None,
    response: Response = None,
    **kwargs,
):
    key = ":".join([
        namespace,
        request.method.lower(),
        request.url.path,
        repr(sorted(request.query_params.items()))
    ])
    return key


def request_without_token_builder(
    func,
    *args,
    namespace: str = "",
    request: Request = None,
    response: Response = None,
    **kwargs,
):
    """
    Строит ключ кэша БЕЗ токена.
    Для POST unified feed - кэшируем по URL (body одинаковый для всех).
    """
    # Убираем token из query params
    params_dict = {k: v for k, v in request.query_params.items() if k != "token"}
    
    key = ":".join([
        namespace,
        request.method.lower(),
        request.url.path,
        repr(sorted(params_dict.items()))
    ])
    return key
