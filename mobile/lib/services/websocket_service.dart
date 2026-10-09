import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../core/constants.dart';
import '../models/water_status.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _reconnectTimer;
  String? _token;
  bool _disposed = false;

  final _controller = StreamController<WaterStatus>.broadcast();
  Stream<WaterStatus> get stream => _controller.stream;

  void connect(String? token) {
    _token = token;
    _reconnectTimer?.cancel();
    if (_token == null || _disposed) return;

    try {
      _subscription?.cancel();
      _channel?.sink.close();

      _channel = WebSocketChannel.connect(Uri.parse(socketBase));
      _channel!.sink.add(jsonEncode({'token': _token}));

      _subscription = _channel!.stream.listen(
        (frame) {
          try {
            final packet = jsonDecode(frame as String);
            if (packet is Map<String, dynamic> && packet['data'] != null) {
              final status = WaterStatus.fromJson(
                  Map<String, dynamic>.from(packet['data']));
              _controller.add(status);
            }
          } catch (_) {}
        },
        onDone: _scheduleReconnect,
        onError: (_) => _scheduleReconnect(),
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_disposed || _token == null) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 4), () {
      if (!_disposed && _token != null) connect(_token);
    });
  }

  void disconnect() {
    _token = null;
    _reconnectTimer?.cancel();
    _subscription?.cancel();
    _channel?.sink.close();
  }

  void dispose() {
    _disposed = true;
    disconnect();
    _controller.close();
  }
}
