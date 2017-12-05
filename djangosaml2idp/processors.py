class BaseProcessor(object):
    """ Processor class is used to:
        - determine if a user has access to a client service of this IDP
        - create the identity dictionary sent to the SP
    """

    def has_access(self, user):
        """ Return True if this user can perform SSO login. """
        return True

    def multifactor_url(self, user):
        """ If a second level authentication system is required, return a url here to redirect
            the user to (this default behaviour can be changed by overriden the method in the LoginView).
            If None is returned (or something evaluating to False), no multifactor check is
            done. Return HttpResponse(request.session['saml_data']) from that view after verification.
        """
        return None

    def create_identity(self, user, sp_mapping):
        """ Create a dictionary with user attributes to be sent to the SP. """
        return {
            out_attr: getattr(user, user_attr)
            for user_attr, out_attr in sp_mapping.items()
            if hasattr(user, user_attr)
        }
