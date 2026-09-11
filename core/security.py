from django.utils.http import url_has_allowed_host_and_scheme


def safe_next_url(request, value):
    if not value:
        return ""
    if url_has_allowed_host_and_scheme(
        url=value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return value
    return ""
