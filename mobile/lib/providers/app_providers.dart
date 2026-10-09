import 'dart:async';
import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/alert_item.dart';
import '../models/complaint_item.dart';
import '../models/maintenance_event.dart';
import '../models/usage.dart';
import '../models/user_profile.dart';
import '../models/water_status.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../services/websocket_service.dart';

// Services
final storageServiceProvider = Provider<StorageService>((ref) {
  return StorageService();
});

final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService();
});

final webSocketServiceProvider = Provider<WebSocketService>((ref) {
  final service = WebSocketService();
  ref.onDispose(service.dispose);
  return service;
});

// Auth State
enum AuthStatus { initial, authenticating, authenticated, unauthenticated }

class AuthState {
  final AuthStatus status;
  final String? token;
  final UserProfile? user;
  final String? errorMessage;

  const AuthState({
    required this.status,
    this.token,
    this.user,
    this.errorMessage,
  });

  factory AuthState.initial() =>
      const AuthState(status: AuthStatus.initial);

  factory AuthState.authenticating() =>
      const AuthState(status: AuthStatus.authenticating);

  factory AuthState.authenticated(String token, UserProfile user) =>
      AuthState(status: AuthStatus.authenticated, token: token, user: user);

  factory AuthState.unauthenticated([String? message]) => AuthState(
      status: AuthStatus.unauthenticated, errorMessage: message);
}

class AuthNotifier extends StateNotifier<AuthState> {
  final StorageService _storage;
  final ApiService _api;
  final WebSocketService _ws;

  AuthNotifier(this._storage, this._api, this._ws)
      : super(AuthState.unauthenticated()) {
    initSession();
  }

  Future<void> initSession() async {
    final token = await _storage.getToken();
    if (token == null) {
      state = AuthState.unauthenticated();
      return;
    }
    try {
      _api.setToken(token);
      final user = await _api.getMe();
      if (user.role != 'RESIDENT') {
        await _storage.clearToken();
        _api.setToken(null);
        state = AuthState.unauthenticated(
            'Administrator accounts use the JalOS Operations Portal.');
        return;
      }
      state = AuthState.authenticated(token, user);
      _ws.connect(token);
    } catch (_) {
      await _storage.clearToken();
      _api.setToken(null);
      state = AuthState.unauthenticated();
    }
  }

  Future<void> login(String email, String password) async {
    state = AuthState.authenticating();
    try {
      final res = await _api.login(email, password);
      final role = res['user']?['role']?.toString();
      if (role != 'RESIDENT') {
        state = AuthState.unauthenticated(
            'Administrator accounts use the JalOS Operations Portal.');
        return;
      }
      final token = res['access_token'] as String;
      final user = UserProfile.fromJson(Map<String, dynamic>.from(res['user']));
      await _storage.saveToken(token);
      _api.setToken(token);
      state = AuthState.authenticated(token, user);
      _ws.connect(token);
    } catch (e) {
      state = AuthState.unauthenticated(
          e.toString().replaceFirst('Exception: ', ''));
      rethrow;
    }
  }

  Future<void> logout() async {
    await _storage.clearToken();
    _api.setToken(null);
    _ws.disconnect();
    state = AuthState.unauthenticated();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final storage = ref.watch(storageServiceProvider);
  final api = ref.watch(apiServiceProvider);
  final ws = ref.watch(webSocketServiceProvider);
  return AuthNotifier(storage, api, ws);
});

// Water Status Provider
class WaterStatusNotifier extends StateNotifier<AsyncValue<WaterStatus>> {
  final ApiService _api;
  final WebSocketService _ws;
  StreamSubscription? _socketSub;
  Timer? _pollTimer;

  WaterStatusNotifier(this._api, this._ws, String? token)
      : super(const AsyncValue.loading()) {
    if (token != null) {
      refresh();
      _socketSub = _ws.stream.listen((status) {
        state = AsyncValue.data(status);
      });
      _pollTimer = Timer.periodic(const Duration(seconds: 25), (_) => refresh());
    }
  }

  Future<void> refresh() async {
    try {
      final data = await _api.getWaterStatus();
      state = AsyncValue.data(data);
    } catch (e, st) {
      if (!state.hasValue) {
        state = AsyncValue.error(e, st);
      }
    }
  }

  @override
  void dispose() {
    _socketSub?.cancel();
    _pollTimer?.cancel();
    super.dispose();
  }
}

final waterStatusProvider =
    StateNotifierProvider<WaterStatusNotifier, AsyncValue<WaterStatus>>((ref) {
  final api = ref.watch(apiServiceProvider);
  final ws = ref.watch(webSocketServiceProvider);
  final auth = ref.watch(authProvider);
  return WaterStatusNotifier(api, ws, auth.token);
});

// Usage Provider
class UsageNotifier extends StateNotifier<AsyncValue<HouseholdUsage>> {
  final ApiService _api;

  UsageNotifier(this._api, String? token) : super(const AsyncValue.loading()) {
    if (token != null) refresh();
  }

  Future<void> refresh() async {
    try {
      final usage = await _api.getUsage();
      state = AsyncValue.data(usage);
    } catch (e, st) {
      if (!state.hasValue) {
        state = AsyncValue.error(e, st);
      }
    }
  }
}

final usageProvider =
    StateNotifierProvider<UsageNotifier, AsyncValue<HouseholdUsage>>((ref) {
  final api = ref.watch(apiServiceProvider);
  final auth = ref.watch(authProvider);
  return UsageNotifier(api, auth.token);
});

// Alerts Provider
class AlertsNotifier extends StateNotifier<List<AlertItem>> {
  final ApiService _api;

  AlertsNotifier(this._api, String? token) : super(const []) {
    if (token != null) refresh();
  }

  Future<void> refresh() async {
    try {
      final items = await _api.getAlerts();
      state = items;
    } catch (_) {}
  }

  Future<void> markAsRead(int alertId) async {
    try {
      await _api.markAlertRead(alertId);
      state = state.map((item) {
        if (item.id == alertId) return item.copyWith(read: true);
        return item;
      }).toList();
    } catch (_) {}
  }

  int get unreadCount => state.where((item) => !item.read).length;
}

final alertsProvider =
    StateNotifierProvider<AlertsNotifier, List<AlertItem>>((ref) {
  final api = ref.watch(apiServiceProvider);
  final auth = ref.watch(authProvider);
  return AlertsNotifier(api, auth.token);
});

// Complaints Provider
class ComplaintsNotifier extends StateNotifier<List<ComplaintItem>> {
  final ApiService _api;

  ComplaintsNotifier(this._api, String? token) : super(const []) {
    if (token != null) refresh();
  }

  Future<void> refresh() async {
    try {
      final items = await _api.getComplaints();
      state = items;
    } catch (_) {}
  }

  Future<void> createComplaint({
    required String category,
    required String title,
    required String description,
    File? photo,
  }) async {
    final complaint = await _api.createComplaint(
      category: category,
      title: title,
      description: description,
    );
    if (photo != null) {
      try {
        await _api.uploadComplaintPhoto(complaint.id, photo);
      } catch (_) {}
    }
    await refresh();
  }
}

final complaintsProvider =
    StateNotifierProvider<ComplaintsNotifier, List<ComplaintItem>>((ref) {
  final api = ref.watch(apiServiceProvider);
  final auth = ref.watch(authProvider);
  return ComplaintsNotifier(api, auth.token);
});

// Maintenance Provider
final maintenanceProvider =
    FutureProvider<List<MaintenanceEventItem>>((ref) async {
  final auth = ref.watch(authProvider);
  if (auth.token == null) return [];
  final api = ref.watch(apiServiceProvider);
  return api.getMaintenance();
});
