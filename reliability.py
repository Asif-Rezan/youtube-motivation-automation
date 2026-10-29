"""Bounded retries for idempotent work; never retry an ambiguous video insertion."""
import errno
import json
import socket
import ssl
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

NETWORK_ERRNOS = {errno.ECONNRESET, errno.ECONNREFUSED, errno.ECONNABORTED,
                  errno.ETIMEDOUT, errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EPIPE}


def transient(error, depth=0):
    if isinstance(error, (TimeoutError, ConnectionError, ssl.SSLEOFError, ssl.SSLZeroReturnError)):
        return True
    if isinstance(error, socket.gaierror) and error.errno == socket.EAI_AGAIN:
        return True
    if isinstance(error, OSError) and error.errno in NETWORK_ERRNOS:
        return True
    status = getattr(getattr(error, 'resp', None), 'status', None)
    if status is None:
        status = getattr(getattr(error, 'response', None), 'status_code', None)
    if status in (408, 429, 500, 502, 503, 504):
        return True
    if status == 403:
        try:
            reasons = {item.get('reason') for item in json.loads(error.content).get('error', {}).get('errors', [])}
            return bool(reasons & {'rateLimitExceeded', 'userRateLimitExceeded', 'backendError'})
        except (ValueError, TypeError, AttributeError):
            return False
    # Optional clients use their own network exception classes.
    network_class = (type(error).__module__.split('.')[0] in {'requests', 'httpx', 'httpcore', 'httplib2'}
            and type(error).__name__ in {'ConnectError', 'ConnectTimeout', 'ReadTimeout',
                'ReadError', 'RemoteProtocolError', 'ConnectionError', 'Timeout', 'ServerNotFoundError'})
    if network_class:
        return True
    cause = getattr(error, '__cause__', None)
    return bool(status is None and depth < 2 and isinstance(cause, Exception) and transient(cause, depth+1))


def retry(operation, label, attempts=4):
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as error:
            if not transient(error) or attempt == attempts - 1:
                raise
            delay = min(2 ** (attempt + 1), 16)
            response = getattr(error, 'resp', None)
            header = response.get('retry-after') if isinstance(response, dict) else None
            if header:
                try:
                    wait = float(header)
                except (ValueError, TypeError):
                    try:
                        wait = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
                    except (ValueError, TypeError, OverflowError):
                        wait = delay
                delay = min(60, max(delay, wait))
            print(json.dumps({'check': label, 'retry': attempt + 1, 'max_attempts': attempts,
                'wait_seconds': delay, 'error_type': type(error).__name__}), flush=True)
            time.sleep(delay)


def api_execute(request):
    """Only use for reads or updates/deletes against known resource IDs."""
    from urllib.parse import urlsplit
    method, uri = getattr(request, 'method', None), getattr(request, 'uri', None)
    if method == 'POST' and isinstance(uri, str) and urlsplit(uri).path.rstrip('/').endswith(('/videos', '/files')):
        raise ValueError('Non-idempotent insertion must not use generic retry')
    return retry(lambda: request.execute(), 'Google API transient recovery')


def atomic_text(path, value, encoding='utf-8'):
    """Never expose a half-written local checkpoint as a completed cache entry."""
    from pathlib import Path
    path = Path(path)
    temporary = path.with_name(path.name + '.partial')
    try:
        temporary.write_text(value, encoding=encoding)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class ProcessingPending(TimeoutError):
    """The known video exists, so only its finalization may be retried."""
