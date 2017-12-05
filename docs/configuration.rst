##############
Configuration
##############

**********
Processor
**********

The *SAML_IDP_SPCONFIG* setting contains per SP you need to talk to a configuration dict. The **processor** value has to be a dotted path to a Processor class (either subclass or create your own implementing the methods below). If not present in the config dict, it will fallback
to the *BaseProcessor* of this package. The BaseProcessor is shown here and can be subclassed to allow different behaviour per SP. The methods of this processor are called by the LoginView
to perform some checks on a user.


.. automodule:: djangosaml2idp.processors
   :members:

**********
Login View
**********

The main view that processes a SAML request is the LoginView. It is a class-based view allowing to override methods and hooks as necessary. The code below shows the flow of the view.


    class LoginProcessView(LoginRequiredMixin, View):
        IDP = Server(config=IdPConfig().load(copy.deepcopy(settings.SAML_IDP_CONFIG)))

        def construct_server(self, request, *args, **kwargs):
            """ If necessary, construct / edit / update self.IDP here. """
            pass

        def construct_identity(self, request, processor, sp_config):
            """ Create user identity dict (SP-specific). """
            sp_attribute_mapping = sp_config.get('attribute_mapping', {'username': 'username'})
            return processor.create_identity(request.user, sp_attribute_mapping)

        def try_multifactor(self, request, processor, http_args):
            """ Hook to allow multifactor authentication. Example implementation here:
                If required by processor, store SAML response in session and redirect to user-defined view.
                User-defined view can then do whatever validation it needs and return HttpResponse(request.session['saml_data']).
            """
            multifactor_url = processor.multifactor_url(request.user)
            if multifactor_url:
                request.session['saml_data'] = http_args['data']
                logger.debug("Redirecting to process_multi_factor")
                return HttpResponseRedirect(multifactor_url)

        def get(self, request, *args, **kwargs):
            self.construct_server(request, *args, **kwargs)

            # SAML code

            # Create user-specified processor or fallback to all-access base processor
            processor_as_string = sp_config.get('processor', None)
            processor = import_string(processor_as_string)() if processor_as_string else BaseProcessor()

            if not processor.has_access(request.user):  # Check if user has access to this SP
                raise PermissionDenied("User {} does not have access to this resource".format(request.user))

            user_identity_dict = self.construct_identity(request, processor, sp_config)

            # SAML code

            self.try_multifactor(request, processor, http_args)

            return HttpResponse(http_args['data'])



***********************************
Multi factor authentication support
***********************************

It's possible to require an extra multi-factor authorization step in the authentication view. 2 places require work for that.

The first place is the *try_multifactor* method of the *LoginProcessView*. It should be overriden to (for example) redirect a user to a view which does some multifactor check logic.

The *Processor* class used for the SP can implement a *multifactor_url* method and redirect a user to the url it returns. That view can return the request.session[‘saml_data’] data after
its check to complete the SAML login. **Note that depending on your custom try_multifactor() method of your subclassed LoginProcessView, you might not use this multifactor_url at all.**
