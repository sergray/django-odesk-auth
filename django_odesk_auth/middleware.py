from . import utils
from . import O_REQUEST_TOKEN, O_ACCESS_TOKEN


class RequestClientMiddleware(object):

    def process_request(self, request):
        """
        Injects an initialized oDesk client to every request, making 
        it easy to use it in views
        """
        access_token = request.session.get(O_ACCESS_TOKEN, None)
        odesk_client = utils.get_client()
        try:
            odesk_client.oauth_access_token = access_token[0]
            odesk_client.oauth_access_token_secret = access_token[1]
        except (IndexError, TypeError):
            pass
        request.odesk_client = odesk_client
        return None
