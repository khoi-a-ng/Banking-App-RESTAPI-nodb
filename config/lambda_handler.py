"""Entry point for AWS Lambda.

Lambda hands your code an `event` dict, not an HTTP request. Django speaks
WSGI. apig_wsgi is the adapter between the two: it translates API Gateway's
event into the environ dict Django expects, then translates Django's response
back into the JSON shape API Gateway wants.

That is the whole job. Every view, serializer and test stays untouched -- the
app does not know it is running on Lambda.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from apig_wsgi import make_lambda_handler  # noqa: E402
from config.wsgi import application  # noqa: E402

# binary_support lets non-text responses through correctly. This API only
# returns JSON, but it costs nothing and avoids a surprise later.
handler = make_lambda_handler(application, binary_support=True)
