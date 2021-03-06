# coding: utf-8
# pylint: skip-file
"""
Tests for django-rest-easy.
"""
from __future__ import unicode_literals

import six
from django.conf import settings
from django.http import Http404
from django.test import TestCase

from rest_easy.exceptions import RestEasyException
from rest_easy.models import deserialize_data
from rest_easy.patterns import SingletonCreator, Singleton, SingletonBase, RegisteredCreator, BaseRegister
from rest_easy.registers import serializer_register
from rest_easy.scopes import ScopeQuerySet, UrlKwargScopeQuerySet, RequestAttrScopeQuerySet
from rest_easy.serializers import ModelSerializer, SerializerCreator
from rest_easy.tests.models import *
from rest_easy.views import ModelViewSet


class Container(object):
    pass


class BaseTestCase(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        serializer_register._entries = {}


class SingletonDecoratorTest(BaseTestCase):
    """
    This test case checks the init-regulating decorator.
    """

    @classmethod
    def setUpClass(cls):
        """
        This method sets up properties required to run the tests.
        :return:
        """
        super(SingletonDecoratorTest, cls).setUpClass()

        class Test(object):
            """
            This class enables properties, pure object doesn't.
            """

            def __init__(self, sl_init=True):
                """
                This method sets the parameter checked by singleton_decorator.
                """
                self.sl_init = sl_init

        cls.Test = Test

        def func(param):
            """
            This function is used to test the decorator.
            :param param:
            :return:
            """
            if param:
                return 1

        cls.decorated = staticmethod(SingletonCreator.singleton_decorator(func))
        cls.func = staticmethod(func)

    def test_properties(self):
        """
        This test checks if the function gets decorated properly.
        :return:
        """
        self.assertEqual(self.func.__name__, self.decorated.__name__)

    def test_init(self):
        """
        This test checks whether initialization is done when it should be.
        :return:
        """
        obj = self.Test(True)
        self.assertEqual(self.decorated(obj), 1)
        obj = self.Test(False)
        self.assertEqual(self.decorated(obj), None)

    def test_multiple_calls(self):
        """
        This test checks a more life-like decorator usage with multiple calls.
        :return:
        """
        obj = self.Test(True)
        self.assertEqual(self.decorated(obj), 1)
        obj.sl_init = False
        self.assertEqual(self.decorated(obj), None)
        self.assertEqual(self.decorated(obj), None)
        self.assertEqual(self.decorated(obj), None)
        obj.sl_init = True
        self.assertEqual(self.decorated(obj), 1)
        self.assertEqual(self.decorated(obj), 1)


class SingletonTest(BaseTestCase):
    """
    This test suite checks whether our extended singleton works as intended.
    """

    @classmethod
    def setUpClass(cls):
        """
        This method sets up a class required to proceed with the tests.
        :return:
        """
        super(SingletonTest, cls).setUpClass()

        class Test(Singleton):
            """
            This class is the bare requirement to test NamedSingleton.
            """

            def __init__(self, param):
                """
                This function allows us to check how many times it was called.
                :param param:
                :return:
                """
                self.test = self.test + 1 if hasattr(self, 'test') else param
                self.var = None
        cls.Test = Test

    def test_same(self):
        object_a = self.Test(1)
        object_b = self.Test(5)
        self.assertTrue(object_a is object_b)
        object_a.var = 1
        self.assertEqual(object_b.var, 1)
        self.assertEqual(object_b.test, 1)
        self.assertEqual(object_a.test, 1)


class TestCreator(BaseTestCase):
    def test_get_name(self):
        self.assertEqual('a', RegisteredCreator.get_name('a', None, None))

    def test_get_fields_from_base(self):
        class A(object):
            a = 1
            b = 2

            def c(self):  # pragma: no coverage
                pass

        fields = list(RegisteredCreator.get_fields_from_base(A))
        self.assertEqual(len(fields), 2)
        self.assertIn(('a', 1), fields)
        self.assertIn(('b', 2), fields)

    def test_simple_required_fields(self):
        missing = RegisteredCreator.get_missing_fields({'a'}, {})
        self.assertIn('a', missing)
        required_fields = {
            'a': None,
            'b': lambda x: x is not None
        }
        fields = {'b': None}
        missing = RegisteredCreator.get_missing_fields(required_fields, fields)
        self.assertIn('a', missing)
        self.assertIn('b', missing)

    def test_hooks(self):
        self.assertEqual((1, 2, 3), RegisteredCreator.pre_register(1, 2, 3))
        self.assertEqual(None, RegisteredCreator.post_register(True, 1, 2, 3))

    def test_field_inheritance(self):
        class Mock(object):
            a = {}

        RegisteredCreator.inherit_fields = True
        RegisteredCreator.register = BaseRegister()

        class Test(six.with_metaclass(RegisteredCreator, Mock)):
            pass

        self.assertEqual(Mock.a, Test.a)
        RegisteredCreator.inherit_fields = False

    def test_serializer_field_inheritance(self):
        class Mock(object):
            a = {}

        SerializerCreator.inherit_fields = True

        class Test(six.with_metaclass(SerializerCreator, Mock)):
            __abstract__ = True

        self.assertEqual(Mock.a, Test.a)
        SerializerCreator.inherit_fields = False


class TestSerializers(BaseTestCase):
    def testModelSerializerMissingFields(self):
        def inner():
            class MockSerializer(ModelSerializer):
                class Meta:
                    fields = '__all__'
                    model = MockModel

        def inner2():
            class MockSerializer(ModelSerializer):
                class Meta:
                    fields = '__all__'
                    schema = 'default'

        def inner3():
            class MockSerializer(ModelSerializer):
                class Meta:
                    fields = '__all__'

        self.assertRaises(RestEasyException, inner)
        self.assertRaises(RestEasyException, inner2)
        self.assertRaises(RestEasyException, inner3)

    def testModelSerializerAutoFields(self):
        class MockSerializer(ModelSerializer):
            class Meta:
                fields = ('value', )
                model = MockModel
                schema = 'default'

        self.assertTrue(MockSerializer._declared_fields['model'].value == 'rest_easy.MockModel')
        self.assertTrue(MockSerializer._declared_fields['schema'].value == 'default')
        self.assertIn('model', MockSerializer.Meta.fields)
        self.assertIn('schema', MockSerializer.Meta.fields)

    def testRegisterDuplication(self):
        def create():
            class MockSerializer(ModelSerializer):
                class Meta:
                    fields = '__all__'
                    model = MockModel
                    schema = 'default'
            return MockSerializer
        settings.REST_EASY_SERIALIZER_CONFLICT_POLICY = 'raise'
        create()
        self.assertRaises(RestEasyException, create)
        settings.REST_EASY_SERIALIZER_CONFLICT_POLICY = 'allow'
        ms = create()
        self.assertIn((serializer_register.get_name(MockModel, 'default'), ms), serializer_register.entries())
        self.assertEqual(serializer_register.get(MockModel, 'default'), ms)

    def testRegisterAttributes(self):
        self.assertRaises(RestEasyException, lambda: serializer_register.get(object, 'schema'))

    def testModelSerializerAutoFieldsNoneModel(self):
        class MockSerializer(ModelSerializer):
            class Meta:
                fields = '__all__'
                model = None
                schema = 'default'

        self.assertTrue(MockSerializer._declared_fields['model'].value is None)
        self.assertTrue(MockSerializer._declared_fields['schema'].value == 'default')


class TestModels(BaseTestCase):
    def setUp(self):
        super(TestModels, self).setUp()

        class MockSerializer(ModelSerializer):
            class Meta:
                fields = '__all__'
                model = MockModel
                schema = 'default'

        self.serializer = MockSerializer
        pass

    def test_get_serializer_success(self):
        taggable = MockModel(value='asd')
        self.assertEqual(taggable.get_serializer('default'), self.serializer)

    def test_get_serializer_failure(self):
        taggable = MockModel(value='asd')
        self.assertEqual(taggable.get_serializer('nope'), None)

    def test_serialize_success(self):
        taggable = MockModel(value='asd')
        serialized = taggable.serialize()
        self.assertEqual(serialized['model'], 'rest_easy.MockModel')
        self.assertEqual(serialized['schema'], 'default')
        self.assertEqual(serialized['value'], 'asd')

    def test_serialize_failure(self):
        taggable = MockModel(value='asd')
        self.assertRaises(RestEasyException, lambda: taggable.serialize('nope'))

    def test_deserialize_success(self):
        data = {'model': 'rest_easy.mockmodel', 'schema': 'default', 'value': 'zxc'}
        validated = deserialize_data(data)
        self.assertEqual(validated, {'value': data['value']})

    def test_deserialize_failure(self):
        data = {'model': 'rest_easy.MockModel', 'value': 'zxc'}
        self.assertRaises(RestEasyException, lambda: deserialize_data(data))
        data['schema'] = 'nonexistant'
        self.assertRaises(RestEasyException, lambda: deserialize_data(data))


class TestViews(BaseTestCase):
    def test_missing_fields(self):
        class FailingViewSet(ModelViewSet):
            pass

        self.assertIsNone(FailingViewSet.queryset, None)

    def test_queryset(self):
        class TaggableViewSet(ModelViewSet):
            queryset = MockModel.objects.all()
            model = MockModel2

        class AccountViewSet(ModelViewSet):
            model = MockModel2

        self.assertEqual(TaggableViewSet.queryset.model, MockModel)
        self.assertEqual(AccountViewSet.queryset.model, MockModel2)

    def test_scope_fails(self):
        class TaggableViewSet(ModelViewSet):
            model = MockModel
            scope = ScopeQuerySet(MockModel2)

        self.assertRaises(NotImplementedError, TaggableViewSet().get_queryset)

    def test_scope(self):
        class UserViewSet(ModelViewSet):
            model = User
            scope = UrlKwargScopeQuerySet(Account)
        vs = UserViewSet()
        vs.kwargs = {'account_pk': 1}
        self.assertEqual(0, vs.get_queryset().count())

    def test_get_scope_object(self):
        mock = Container()

        class UserViewSet(ModelViewSet):
            model = User
            scope = RequestAttrScopeQuerySet(Account, request_attr='account')

        vs = UserViewSet()
        vs.request = Container()
        vs.request.account = mock
        self.assertEqual(mock, vs.get_account)
        self.assertRaises(AttributeError, lambda: vs.get_whatever())

    def test_performs(self):
        class UserViewSet(ModelViewSet):
            model = User
            scope = UrlKwargScopeQuerySet(Account)

        class Serializer(object):
            def __init__(self, case, param):
                self.case = case
                self.param = param

            def save(self, param):
                self.case.assertEqual(param, self.param)

        s = Serializer(self, 'create')
        vs = UserViewSet()
        vs.perform_create(s, param='create')
        s.param = 'update'
        vs.perform_update(s, param='update')

    def test_serializer_class(self):
        class UserSerializer(ModelSerializer):
            class Meta:
                model = User
                schema = 'default'
                fields = '__all__'

        class UserRetrieveSerializer(ModelSerializer):
            class Meta:
                model = User
                schema = 'default-retrieve'
                fields = '__all__'

        class UserListSerializer(ModelSerializer):
            class Meta:
                model = User
                schema = 'default-list'
                fields = '__all__'

        class UserViewSet(ModelViewSet):
            model = User
            schema = 'default'
            serializer_schema_for_verb = {'retrieve': 'default-retrieve', 'list': 'default-list'}
            lookup_url_kwarg = 'pk'

        class UserViewSet2(ModelViewSet):
            serializer_class = UserSerializer

        vs = UserViewSet()
        vs.request = Container()
        vs.rest_easy_object_cache = {}

        # retrieve
        vs.kwargs = {'pk': 1}
        vs.request.method = 'get'
        self.assertEqual(vs.get_serializer_class(), UserRetrieveSerializer)
        # list
        vs.kwargs = {}
        self.assertEqual(vs.get_serializer_class(), UserListSerializer)
        #default
        vs.request.method = 'put'
        self.assertEqual(vs.get_serializer_class(), UserSerializer)
        #queryset
        vs = UserViewSet2()
        self.assertEqual(vs.get_serializer_class(), UserSerializer)

    def test_serializer_class_failing(self):
        class UserViewSet(ModelViewSet):
            model = User

        class UserViewSet2(ModelViewSet):
            pass

        vs = UserViewSet()
        vs.request = Container()
        vs.rest_easy_object_cache = {}
        vs.kwargs = {'pk': 1}
        vs.request.method = 'get'
        self.assertRaises(RestEasyException, vs.get_serializer_class)

        vs = UserViewSet2()
        vs.request = Container()
        vs.rest_easy_object_cache = {}
        vs.kwargs = {'pk': 1}
        vs.request.method = 'get'
        self.assertRaises(RestEasyException, vs.get_serializer_class)


class TestScopeQuerySet(BaseTestCase):
    def setUp(self):
        self.account = Account.objects.create()
        self.other_account = Account.objects.create()
        self.user = User.objects.create(account=self.account)
        self.other_user = User.objects.create(account=self.other_account)

    def test_chaining(self):
        self.assertRaises(NotImplementedError,
                          lambda: UrlKwargScopeQuerySet(Account,
                                                        parent=ScopeQuerySet(Account.objects.all(),
                                                                             get_object_handle=None),
                                                        get_object_handle=None
                                                        ).child_queryset(None, None))

    def test_creation_fails(self):
        self.assertRaises(RestEasyException, lambda: ScopeQuerySet(object))
        self.assertRaises(RestEasyException, lambda: ScopeQuerySet(None))
        self.assertRaises(RestEasyException, lambda: UrlKwargScopeQuerySet(None, related_field='a',
                                                                           get_object_handle=None))
        self.assertRaises(RestEasyException, lambda: RequestAttrScopeQuerySet(None))
        self.assertRaises(RestEasyException, lambda: RequestAttrScopeQuerySet(None, request_attr='a'))
        self.assertRaises(RestEasyException, lambda: RequestAttrScopeQuerySet(None,
                                                                              request_attr='a',
                                                                              related_field='a'))

    def test_contribute_to_class(self):
        view = Container()
        view.rest_easy_object_cache = {}
        view.rest_easy_available_object_handles = {}
        parent = UrlKwargScopeQuerySet(User, get_object_handle='test')
        scope = UrlKwargScopeQuerySet(Account, parent=parent)
        scope.contribute_to_class(view)
        self.assertEqual(view.rest_easy_available_object_handles['account'], scope)
        self.assertEqual(view.rest_easy_available_object_handles['test'], parent)
        self.assertRaises(RestEasyException, lambda: scope.contribute_to_class(view))

    def test_url_kwarg(self):
        view = Container()
        view.rest_easy_object_cache = {}
        view.kwargs = {'account_pk': self.other_account.pk}

        qs = UrlKwargScopeQuerySet(Account).child_queryset(User.objects.all(), view)
        self.assertIn(self.other_user, list(qs))
        self.assertEqual(1, len(list(qs)))

    def test_request_attrs(self):
        view = Container()
        view.rest_easy_object_cache = {}
        view.request = Container()
        view.request.account = self.other_account.pk

        qs = RequestAttrScopeQuerySet(Account, request_attr='account',
                                      is_object=False).child_queryset(User.objects.all(), view)
        self.assertIn(self.other_user, list(qs))
        self.assertEqual(1, len(list(qs)))

        view.request.account = self.other_account
        qs = RequestAttrScopeQuerySet(Account, request_attr='account',
                                      is_object=True, get_object_handle=None).child_queryset(User.objects.all(), view)
        self.assertIn(self.other_user, list(qs))
        self.assertEqual(1, len(list(qs)))

    def test_none(self):
        view = Container()
        view.rest_easy_object_cache = {}
        view.kwargs = {'account_pk': self.other_account.pk + 100}

        qs = UrlKwargScopeQuerySet(Account).child_queryset(User.objects.all(), view)
        self.assertEqual(0, len(list(qs)))

    def test_raises(self):
        view = Container()
        view.rest_easy_object_cache = {}
        view.kwargs = {'account_pk': self.other_account.pk + 100}

        self.assertRaises(Http404,
                          lambda: UrlKwargScopeQuerySet(Account,
                                                        raise_404=True).child_queryset(User.objects.all(), view))
