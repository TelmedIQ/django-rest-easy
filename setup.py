from distutils.core import setup

setup(
    name='rest_easy',
    packages=['rest_easy'],
    version='0.1.0',
    download_url='https://github.com/telmediq/django-rest-easy/tarball/0.1.0',
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, <4',
    install_requires=[
        'django>=1.8.0',
        'djangorestframework>=3.0.0',
        'six',
    ],
    description='django-rest-easy is an extension to DRF providing QOL improvements to serializers and views.',
    long_description='django-rest-easy enables:'
                     ' * versioning serializers by model and schema,'
                     ' * creating views and viewsets using model and schema,'
                     ' * serializer override for a particular DRF verb, like create or update,'
                     ' * scoping views\' querysets and viewsets by url kwargs or request object parameters.',
    author='SMARTPAGER SYSTEMS INC. / Krzysztof Bujniewicz',
    author_email='racech@gmail.com',
    url='https://github.com/TelmedIQ/django-rest-easy',
    keywords=['django', 'DRF', 'rest framework', 'serializers', 'viewsets'],
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)