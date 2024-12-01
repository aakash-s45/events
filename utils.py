import logging
import requests
from datetime import datetime
from urllib.parse import urlparse

from settings import APP_NAME, LFM_RATE_LIMIT, MUSICBRAINZ_BASE_URL, THE_LAST_FM_BASE_URL, MB_RATE_LIMIT

logger = logging.getLogger(__name__)
last_call_timestamps = {}
rate_limits = {
    THE_LAST_FM_BASE_URL: LFM_RATE_LIMIT,
    MUSICBRAINZ_BASE_URL: MB_RATE_LIMIT,
}

def make_api_request(url, method, params=None, json=None, headers=None):
    global last_call_timestamps
    parsed_url = urlparse(url)
    host = parsed_url.hostname
    _headers = {"User-Agent": f'{APP_NAME}/1.0'}
    if headers:
        _headers.update(headers)


    last_call_timestamp = last_call_timestamps.get(host, 0)
    now = datetime.now().timestamp()
    if now - last_call_timestamp < rate_limits.get(host, 1):
        msg = f"rate limit exceeded for {host}"
        logger.error(msg)
        return False, msg, None
    
    last_call_timestamps[host] = now
    
    try:
        response = requests.request(method, url, params=params, json=json, headers=_headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"request failed due to {e}", exc_info=True)
        return False, "failed", None
    except Exception as e:
        logger.error(f"request failed due to {e}", exc_info=True)
        return False, "failed", None
    return True, "succes", response