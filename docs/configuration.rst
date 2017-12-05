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

The main view that processes a SAML request is the LoginView. It is a class-based view allowing inheritance to override methods and hooks as necessary.


.. autoclass:: djangosaml2idp.views.LoginProcessView
   :members:

***********************************
Multi factor authentication support
***********************************

It's possible to require an extra multi-factor authorization step in the authentication view. 2 places might require work for that.

The first place is the *try_multifactor* method of the *LoginProcessView*, which is called just before normally returning the SAML response. By default, if the *processor.multifactor_url* returns something,
it is going to redirect the user to that url, which then does some multifactor check logic.
If the *multifactor_url* method returns nothing (which is the *BaseProcessor* default implementation), no multi-factor will be done at all.

The *Processor* class used for the SP can implement a *multifactor_url* method and redirect a user to the url it returns. That view can then return the request.session[‘saml_data’] data after
its check to complete the SAML login. **Note that depending on your custom try_multifactor() method of your subclassed LoginProcessView, you might not use this multifactor_url at all.**
