# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pass_criteria.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor.FileDescriptor(
        name='pass_criteria.proto',
        package='',
        syntax='proto3',
        serialized_options=None,
        serialized_pb=
        b'\n\x13pass_criteria.proto\"\x16\n\x05\x42ound\x12\r\n\x05\x62ound\x18\x01 \x01(\x01\"k\n\x08\x43riteria\x12\x12\n\nname_regex\x18\x01 \x01(\t\x12\x11\n\ttest_name\x18\x02 \x01(\t\x12\x1b\n\x0blower_bound\x18\x03 \x01(\x0b\x32\x06.Bound\x12\x1b\n\x0bupper_bound\x18\x04 \x01(\x0b\x32\x06.Bound\"+\n\x0cPassCriteria\x12\x1b\n\x08\x63riteria\x18\x01 \x03(\x0b\x32\t.Criteriab\x06proto3'
)

_BOUND = _descriptor.Descriptor(
        name='Bound',
        full_name='Bound',
        filename=None,
        file=DESCRIPTOR,
        containing_type=None,
        fields=[
                _descriptor.FieldDescriptor(name='bound',
                                            full_name='Bound.bound',
                                            index=0,
                                            number=1,
                                            type=1,
                                            cpp_type=5,
                                            label=1,
                                            has_default_value=False,
                                            default_value=float(0),
                                            message_type=None,
                                            enum_type=None,
                                            containing_type=None,
                                            is_extension=False,
                                            extension_scope=None,
                                            serialized_options=None,
                                            file=DESCRIPTOR),
        ],
        extensions=[],
        nested_types=[],
        enum_types=[],
        serialized_options=None,
        is_extendable=False,
        syntax='proto3',
        extension_ranges=[],
        oneofs=[],
        serialized_start=23,
        serialized_end=45,
)

_CRITERIA = _descriptor.Descriptor(
        name='Criteria',
        full_name='Criteria',
        filename=None,
        file=DESCRIPTOR,
        containing_type=None,
        fields=[
                _descriptor.FieldDescriptor(name='name_regex',
                                            full_name='Criteria.name_regex',
                                            index=0,
                                            number=1,
                                            type=9,
                                            cpp_type=9,
                                            label=1,
                                            has_default_value=False,
                                            default_value=b"".decode('utf-8'),
                                            message_type=None,
                                            enum_type=None,
                                            containing_type=None,
                                            is_extension=False,
                                            extension_scope=None,
                                            serialized_options=None,
                                            file=DESCRIPTOR),
                _descriptor.FieldDescriptor(name='test_name',
                                            full_name='Criteria.test_name',
                                            index=1,
                                            number=2,
                                            type=9,
                                            cpp_type=9,
                                            label=1,
                                            has_default_value=False,
                                            default_value=b"".decode('utf-8'),
                                            message_type=None,
                                            enum_type=None,
                                            containing_type=None,
                                            is_extension=False,
                                            extension_scope=None,
                                            serialized_options=None,
                                            file=DESCRIPTOR),
                _descriptor.FieldDescriptor(name='lower_bound',
                                            full_name='Criteria.lower_bound',
                                            index=2,
                                            number=3,
                                            type=11,
                                            cpp_type=10,
                                            label=1,
                                            has_default_value=False,
                                            default_value=None,
                                            message_type=None,
                                            enum_type=None,
                                            containing_type=None,
                                            is_extension=False,
                                            extension_scope=None,
                                            serialized_options=None,
                                            file=DESCRIPTOR),
                _descriptor.FieldDescriptor(name='upper_bound',
                                            full_name='Criteria.upper_bound',
                                            index=3,
                                            number=4,
                                            type=11,
                                            cpp_type=10,
                                            label=1,
                                            has_default_value=False,
                                            default_value=None,
                                            message_type=None,
                                            enum_type=None,
                                            containing_type=None,
                                            is_extension=False,
                                            extension_scope=None,
                                            serialized_options=None,
                                            file=DESCRIPTOR),
        ],
        extensions=[],
        nested_types=[],
        enum_types=[],
        serialized_options=None,
        is_extendable=False,
        syntax='proto3',
        extension_ranges=[],
        oneofs=[],
        serialized_start=47,
        serialized_end=154,
)

_PASSCRITERIA = _descriptor.Descriptor(
        name='PassCriteria',
        full_name='PassCriteria',
        filename=None,
        file=DESCRIPTOR,
        containing_type=None,
        fields=[
                _descriptor.FieldDescriptor(name='criteria',
                                            full_name='PassCriteria.criteria',
                                            index=0,
                                            number=1,
                                            type=11,
                                            cpp_type=10,
                                            label=3,
                                            has_default_value=False,
                                            default_value=[],
                                            message_type=None,
                                            enum_type=None,
                                            containing_type=None,
                                            is_extension=False,
                                            extension_scope=None,
                                            serialized_options=None,
                                            file=DESCRIPTOR),
        ],
        extensions=[],
        nested_types=[],
        enum_types=[],
        serialized_options=None,
        is_extendable=False,
        syntax='proto3',
        extension_ranges=[],
        oneofs=[],
        serialized_start=156,
        serialized_end=199,
)

_CRITERIA.fields_by_name['lower_bound'].message_type = _BOUND
_CRITERIA.fields_by_name['upper_bound'].message_type = _BOUND
_PASSCRITERIA.fields_by_name['criteria'].message_type = _CRITERIA
DESCRIPTOR.message_types_by_name['Bound'] = _BOUND
DESCRIPTOR.message_types_by_name['Criteria'] = _CRITERIA
DESCRIPTOR.message_types_by_name['PassCriteria'] = _PASSCRITERIA
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Bound = _reflection.GeneratedProtocolMessageType(
        'Bound',
        (_message.Message, ),
        {
                'DESCRIPTOR': _BOUND,
                '__module__': 'pass_criteria_pb2'
                # @@protoc_insertion_point(class_scope:Bound)
        })
_sym_db.RegisterMessage(Bound)

Criteria = _reflection.GeneratedProtocolMessageType(
        'Criteria',
        (_message.Message, ),
        {
                'DESCRIPTOR': _CRITERIA,
                '__module__': 'pass_criteria_pb2'
                # @@protoc_insertion_point(class_scope:Criteria)
        })
_sym_db.RegisterMessage(Criteria)

PassCriteria = _reflection.GeneratedProtocolMessageType(
        'PassCriteria',
        (_message.Message, ),
        {
                'DESCRIPTOR': _PASSCRITERIA,
                '__module__': 'pass_criteria_pb2'
                # @@protoc_insertion_point(class_scope:PassCriteria)
        })
_sym_db.RegisterMessage(PassCriteria)

# @@protoc_insertion_point(module_scope)
