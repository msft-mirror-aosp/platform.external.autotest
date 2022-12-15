# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import conn_service_pb2 as conn__service__pb2
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
from google.protobuf import struct_pb2 as google_dot_protobuf_dot_struct__pb2


class ConnServiceStub(object):
    """ConnService provides functions for interacting with conn directly.
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.NewConn = channel.unary_unary(
                '/tast.cros.ui.ConnService/NewConn',
                request_serializer=conn__service__pb2.NewConnRequest.SerializeToString,
                response_deserializer=conn__service__pb2.NewConnResponse.FromString,
                )
        self.NewConnForTarget = channel.unary_unary(
                '/tast.cros.ui.ConnService/NewConnForTarget',
                request_serializer=conn__service__pb2.NewConnForTargetRequest.SerializeToString,
                response_deserializer=conn__service__pb2.NewConnResponse.FromString,
                )
        self.Close = channel.unary_unary(
                '/tast.cros.ui.ConnService/Close',
                request_serializer=conn__service__pb2.CloseRequest.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                )
        self.CloseAll = channel.unary_unary(
                '/tast.cros.ui.ConnService/CloseAll',
                request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                )
        self.ActivateTarget = channel.unary_unary(
                '/tast.cros.ui.ConnService/ActivateTarget',
                request_serializer=conn__service__pb2.ActivateTargetRequest.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                )
        self.Navigate = channel.unary_unary(
                '/tast.cros.ui.ConnService/Navigate',
                request_serializer=conn__service__pb2.NavigateRequest.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                )
        self.Eval = channel.unary_unary(
                '/tast.cros.ui.ConnService/Eval',
                request_serializer=conn__service__pb2.ConnEvalRequest.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_struct__pb2.Value.FromString,
                )
        self.Call = channel.unary_unary(
                '/tast.cros.ui.ConnService/Call',
                request_serializer=conn__service__pb2.ConnCallRequest.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_struct__pb2.Value.FromString,
                )
        self.WaitForExpr = channel.unary_unary(
                '/tast.cros.ui.ConnService/WaitForExpr',
                request_serializer=conn__service__pb2.ConnWaitForExprRequest.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                )


class ConnServiceServicer(object):
    """ConnService provides functions for interacting with conn directly.
    """

    def NewConn(self, request, context):
        """NewConn opens a new tab with the provided url and creates a new Conn for it.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def NewConnForTarget(self, request, context):
        """NewConnForTarget creates a new Conn for an existing tab matching the url provided.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Close(self, request, context):
        """Close calls conn.Close.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def CloseAll(self, request, context):
        """CloseAll closes all conns.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ActivateTarget(self, request, context):
        """ActivateTarget calls conn.ActivateTarget to bring focus to the tab/window.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Navigate(self, request, context):
        """Navigate calls conn.Navigate to navigate the tab to the url.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Eval(self, request, context):
        """Eval evaluates expr on the given page. See Conn.Eval for details.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Call(self, request, context):
        """Call calls the javascript fn with given args. See Conn.Call for details
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def WaitForExpr(self, request, context):
        """WaitForExpr repeatedly evaluates the JavaScript expression expr until it evaluates to true.
        Errors returned by Eval are treated the same as expr == false unless fail_on_err is true.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_ConnServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'NewConn': grpc.unary_unary_rpc_method_handler(
                    servicer.NewConn,
                    request_deserializer=conn__service__pb2.NewConnRequest.FromString,
                    response_serializer=conn__service__pb2.NewConnResponse.SerializeToString,
            ),
            'NewConnForTarget': grpc.unary_unary_rpc_method_handler(
                    servicer.NewConnForTarget,
                    request_deserializer=conn__service__pb2.NewConnForTargetRequest.FromString,
                    response_serializer=conn__service__pb2.NewConnResponse.SerializeToString,
            ),
            'Close': grpc.unary_unary_rpc_method_handler(
                    servicer.Close,
                    request_deserializer=conn__service__pb2.CloseRequest.FromString,
                    response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            ),
            'CloseAll': grpc.unary_unary_rpc_method_handler(
                    servicer.CloseAll,
                    request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                    response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            ),
            'ActivateTarget': grpc.unary_unary_rpc_method_handler(
                    servicer.ActivateTarget,
                    request_deserializer=conn__service__pb2.ActivateTargetRequest.FromString,
                    response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            ),
            'Navigate': grpc.unary_unary_rpc_method_handler(
                    servicer.Navigate,
                    request_deserializer=conn__service__pb2.NavigateRequest.FromString,
                    response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            ),
            'Eval': grpc.unary_unary_rpc_method_handler(
                    servicer.Eval,
                    request_deserializer=conn__service__pb2.ConnEvalRequest.FromString,
                    response_serializer=google_dot_protobuf_dot_struct__pb2.Value.SerializeToString,
            ),
            'Call': grpc.unary_unary_rpc_method_handler(
                    servicer.Call,
                    request_deserializer=conn__service__pb2.ConnCallRequest.FromString,
                    response_serializer=google_dot_protobuf_dot_struct__pb2.Value.SerializeToString,
            ),
            'WaitForExpr': grpc.unary_unary_rpc_method_handler(
                    servicer.WaitForExpr,
                    request_deserializer=conn__service__pb2.ConnWaitForExprRequest.FromString,
                    response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'tast.cros.ui.ConnService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class ConnService(object):
    """ConnService provides functions for interacting with conn directly.
    """

    @staticmethod
    def NewConn(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/NewConn',
            conn__service__pb2.NewConnRequest.SerializeToString,
            conn__service__pb2.NewConnResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def NewConnForTarget(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/NewConnForTarget',
            conn__service__pb2.NewConnForTargetRequest.SerializeToString,
            conn__service__pb2.NewConnResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Close(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/Close',
            conn__service__pb2.CloseRequest.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def CloseAll(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/CloseAll',
            google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def ActivateTarget(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/ActivateTarget',
            conn__service__pb2.ActivateTargetRequest.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Navigate(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/Navigate',
            conn__service__pb2.NavigateRequest.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Eval(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/Eval',
            conn__service__pb2.ConnEvalRequest.SerializeToString,
            google_dot_protobuf_dot_struct__pb2.Value.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Call(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/Call',
            conn__service__pb2.ConnCallRequest.SerializeToString,
            google_dot_protobuf_dot_struct__pb2.Value.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def WaitForExpr(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/tast.cros.ui.ConnService/WaitForExpr',
            conn__service__pb2.ConnWaitForExprRequest.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)