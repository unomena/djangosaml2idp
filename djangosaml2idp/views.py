# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import copy
import logging

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.urlresolvers import reverse
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect, HttpResponseServerError)
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.module_loading import import_string
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from saml2 import BINDING_HTTP_POST
from saml2.authn_context import PASSWORD, AuthnBroker, authn_context_class_ref
from saml2.config import IdPConfig
from saml2.ident import NameID
from saml2.metadata import entity_descriptor
from saml2.s_utils import UnknownPrincipal, UnsupportedBinding
from saml2.server import Server
from six import text_type

from .processors import BaseProcessor

logger = logging.getLogger(__name__)

try:
    idp_sp_config = settings.SAML_IDP_SPCONFIG
except AttributeError:
    raise ImproperlyConfigured("SAML_IDP_SPCONFIG not defined in settings.")


@csrf_exempt
def sso_entry(request):
    """ Entrypoint view for SSO. Gathers the parameters from the HTTP request, stores them in the session
        and redirects the request to the login_process view.
    """
    passed_data = request.POST or request.GET
    try:
        request.session['SAMLRequest'] = passed_data['SAMLRequest']
    except (KeyError, MultiValueDictKeyError) as e:
        return HttpResponseBadRequest(e)
    request.session['RelayState'] = passed_data.get('RelayState', '')
    # TODO check how the redirect saml way works. Taken from example idp in pysaml2.
    if "SigAlg" in passed_data and "Signature" in passed_data:
        request.session['SigAlg'] = passed_data['SigAlg']
        request.session['Signature'] = passed_data['Signature']
    return HttpResponseRedirect(reverse('saml_login_process'))


class LoginProcessView(LoginRequiredMixin, View):
    IDP = Server(config=IdPConfig().load(copy.deepcopy(settings.SAML_IDP_CONFIG)))

    def construct_server(self, request, *args, **kwargs):
        """ If necessary, construct / edit / update self.IDP here. """
        pass

    def construct_identity(self, request, processor, sp_config):
        """ Create user identity dict (list of attributes to include is SP-specific and defined in settings). """
        sp_attribute_mapping = sp_config.get('attribute_mapping', {'username': 'username'})
        return processor.create_identity(request.user, sp_attribute_mapping)

    def try_multifactor(self, request, processor, http_args):
        """ Hook called just before a normal SAML response return, to allow multifactor authentication. Example implementation here:
            If required by the processor, store the SAML response in request.session and redirect to a user-defined view.
            This user-defined view can then do whatever validation it needs and return HttpResponse(request.session['saml_data']).
        """
        multifactor_url = processor.multifactor_url(request.user)
        if multifactor_url:
            request.session['saml_data'] = http_args['data']
            logger.debug("Redirecting to process_multi_factor")
            return HttpResponseRedirect(multifactor_url)

    def get(self, request, *args, **kwargs):
        self.construct_server(request, *args, **kwargs)
        # Parse incoming request
        try:
            req_info = self.IDP.parse_authn_request(request.session['SAMLRequest'], BINDING_HTTP_POST)
        except Exception as excp:
            return HttpResponseBadRequest(excp)

        # TODO this is taken from example, but no idea how this works or whats it does. Check SAML2 specification?
        # Signed request for HTTP-REDIRECT
        if "SigAlg" in request.session and "Signature" in request.session:
            _certs = self.IDP.metadata.certs(req_info.message.issuer.text, "any", "signing")
            verified_ok = False
            for cert in _certs:
                # TODO implement
                # if verify_redirect_signature(_info, self.IDP.sec.sec_backend, cert):
                #    verified_ok = True
                #    break
                pass
            if not verified_ok:
                return HttpResponseBadRequest("Message signature verification failure")

        # Gather response arguments
        try:
            resp_args = self.IDP.response_args(req_info.message)
        except (UnknownPrincipal, UnsupportedBinding) as excp:
            return HttpResponseServerError(excp)

        logger.debug("Incoming request: {}".format({
            'SP': resp_args['sp_entity_id'], 'SAMLRequest': request.session['SAMLRequest'], 'RelayState': request.session['RelayState']}))

        try:
            sp_config = settings.SAML_IDP_SPCONFIG[resp_args['sp_entity_id']]
        except Exception:
            raise ImproperlyConfigured("No config for SP %s defined in SAML_IDP_SPCONFIG" % resp_args['sp_entity_id'])

        # Create user-specified processor or fallback to all-access base processor
        processor_as_string = sp_config.get('processor', None)
        processor = import_string(processor_as_string)() if processor_as_string else BaseProcessor()

        if not processor.has_access(request.user):  # Check if user has access to this SP
            raise PermissionDenied("User {} does not have access to this resource".format(request.user))

        # TODO investigate how this works, because I don't get it. Specification?
        req_authn_context = req_info.message.requested_authn_context or PASSWORD
        AUTHN_BROKER = AuthnBroker()
        AUTHN_BROKER.add(authn_context_class_ref(req_authn_context), "")

        binding_out, destination = self.IDP.pick_binding(service="assertion_consumer_service", entity_id=req_info.message.issuer.text)

        user_identity_dict = self.construct_identity(request, processor, sp_config)

        try:  # Construct SamlResponse message
            authn_resp = self.IDP.create_authn_response(
                identity=user_identity_dict, userid=request.user.username,
                name_id=NameID(format=resp_args['name_id_policy'].format, sp_name_qualifier=destination, text=request.user.username),
                authn=AUTHN_BROKER.get_authn_by_accr(req_authn_context),
                sign_response=self.IDP.config.getattr("sign_response", "idp") or False,
                sign_assertion=self.IDP.config.getattr("sign_assertion", "idp") or False,
                **resp_args)
        except Exception as excp:
            return HttpResponseServerError(excp)

        # Return as html with self-submitting form.
        http_args = self.IDP.apply_binding(
            binding=binding_out,
            msg_str="%s" % authn_resp,
            destination=destination,
            relay_state=request.session['RelayState'],
            response=True)

        logger.debug('Response args are: {}'.format(http_args))
        self.try_multifactor(request, processor, http_args)
        logger.debug("Performing SAML redirect to: {}".format(http_args['url']))
        return HttpResponse(http_args['data'])


def metadata(request):
    """ Returns an XML with the SAML 2.0 metadata for this Idp.
        The metadata is constructed on-the-fly based on the config dict in the django settings.
    """
    metadata = entity_descriptor(IdPConfig().load(copy.deepcopy(settings.SAML_IDP_CONFIG)))
    return HttpResponse(content=text_type(metadata).encode('utf-8'), content_type="text/xml; charset=utf8")
