djangosaml2idp
==============

.. image:: https://img.shields.io/pypi/v/djangosaml2idp.svg
    :target: https://pypi.python.org/pypi/djangosaml2idp
    :alt: PyPi

.. image:: https://readthedocs.org/projects/djangosaml2idp/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://djangosaml2idp.readthedocs.io/en/latest/?badge=latest


djangosaml2idp implements the Identity Provider side of the SAML2 protocol with Django.
It builds on top of PySAML2_, is compatible with Python 2/3 and Django >= 1.11.

.. _PySAML2: https://github.com/rohe/pysaml2/

Any contributions, feature requests, proposals, ideas ... are welcome!

Installation
------------

The first thing you need to do is add ``djangosaml2idp`` to the list of installed apps::

    ```python
    INSTALLED_APPS = (
        'django.contrib.admin',
        'djangosaml2idp',
        ...
    )
    ```


Now include ``djangosaml2idp`` in your project by adding it in the url config::

    ```python
    from django.conf.urls import url, include
    from django.contrib import admin

    urlpatterns = [
        url(r'^idp/', include('djangosaml2idp.urls')),
        url(r'^admin/', admin.site.urls),
        ...
    ]
    ```


In your Django settings, configure your IdP. Configuration follows the pysaml2_configuration_. The IdP from the example project looks like this::

    ```python
    ... # other django settings
    import saml2
    from saml2.saml import NAMEID_FORMAT_EMAILADDRESS, NAMEID_FORMAT_UNSPECIFIED
    from saml2.sigver import get_xmlsec_binary

    LOGIN_URL = '/login/'
    BASE_URL = 'http://localhost:9000/idp'

    SAML_IDP_CONFIG = {
        'debug' : DEBUG,
        'xmlsec_binary': get_xmlsec_binary(['/opt/local/bin', '/usr/bin/xmlsec1']),
        'entityid': '%s/metadata' % BASE_URL,
        'description': 'Example IdP setup',

        'service': {
            'idp': {
                'name': 'Django localhost IdP',
                'endpoints': {
                    'single_sign_on_service': [
                        ('%s/sso/post' % BASE_URL, saml2.BINDING_HTTP_POST),
                        ('%s/sso/redirect' % BASE_URL, saml2.BINDING_HTTP_REDIRECT),
                    ],
                },
                'name_id_format': [NAMEID_FORMAT_EMAILADDRESS, NAMEID_FORMAT_UNSPECIFIED],
                'sign_response': True,
                'sign_assertion': True,
            },
        },

        'metadata': {
            'local': [os.path.join(os.path.join(os.path.join(BASE_DIR, 'idp'), 'saml2_config'), 'sp_metadata.xml')],
        },
        # Signing
        'key_file': BASE_DIR + '/certificates/private_key.pem',
        'cert_file': BASE_DIR + '/certificates/public_key.pem',
        # Encryption
        'encryption_keypairs': [{
            'key_file': BASE_DIR + '/certificates/private_key.pem',
            'cert_file': BASE_DIR + '/certificates/public_key.pem',
        }],
        'valid_for': 365 * 24,
    }
    ```


You also have to define a mapping with config for each SP you talk to::

    ```python
    SAML_IDP_SPCONFIG = {
        'http://localhost:8000/saml2/metadata/': {
            'processor': 'djangosaml2idp.processors.BaseProcessor',
            'attribute_mapping': {
                # DJANGO: SAML
                'email': 'email',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'is_staff': 'is_staff',
                'is_superuser':  'is_superuser',
            }
        }
    }
    ```


The keys of this dict are the Service Provider ID's. The IdP will only respond to SP ID's which are present in this mapping.
For the values, see the `configuration` section in the docs.

That's all for the required IdP configuration. Assuming you run the Django development server on localhost:8000, you can get its metadata by visiting <http://localhost:8000/idp/metadata/>.
Use this metadata xml to configure your SP. Place the metadata xml from that SP in the location specified in the IdP config dict above (sp_metadata.xml in the example above).

.. _pysaml2_configuration: https://github.com/rohe/pysaml2/blob/master/doc/howto/config.rst


Example project
---------------
``example_project`` contains a barebone setup to demonstrate the package.
It consists of a Service Provider implemented with ``djangosaml2`` and an Identity Provider using ``djangosaml2idp``.
