import re

from django.conf import settings


def sentry_dsn(request):
    """
    Make the Sentry / Raven DSN available in the templates *without* the secret key.
    """
    try:
        raven_config = settings.RAVEN_CONFIG['dsn']
    except AttributeError, KeyError:
        return {}

    match = re.search( r"https:\/\/([a-z|0-9]+):([a-z|0-9]+)\@app.getsentry.com\/(\d+)", raven_config, re.M|re.I)

    if not match:
        return {}
    else:
        public_key = match.group(1)
        project_id = match.group(3)

        return {'RAVEN_DSN': "https://{0}@app.getsentry.com/{1}".format(public_key, project_id)}

