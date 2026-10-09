import 'dart:io';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../core/constants.dart';
import '../models/alert_item.dart';
import '../models/complaint_item.dart';
import '../models/maintenance_event.dart';
import '../models/usage.dart';
import '../models/user_profile.dart';
import '../models/water_status.dart';

class ApiService {
  final Dio _dio;
  String? _token;

  ApiService([Dio? dio])
      : _dio = dio ??
            Dio(BaseOptions(
              baseUrl: apiBase,
              connectTimeout: const Duration(seconds: 6),
              receiveTimeout: const Duration(seconds: 6),
            ));

  void setToken(String? token) {
    _token = token;
  }

  Options _authOptions([Options? base]) {
    final headers = Map<String, dynamic>.from(base?.headers ?? {});
    if (_token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }
    return (base ?? Options()).copyWith(headers: headers);
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post('/auth/login', data: {
      'email': email.trim().toLowerCase(),
      'password': password,
    });
    return Map<String, dynamic>.from(response.data);
  }

  Future<UserProfile> getMe() async {
    final response = await _dio.get('/auth/me', options: _authOptions());
    return UserProfile.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<void> changePassword(String currentPassword, String newPassword) async {
    await _dio.patch('/auth/password',
        options: _authOptions(),
        data: {
          'current_password': currentPassword,
          'new_password': newPassword,
        });
  }

  Future<WaterStatus> getWaterStatus() async {
    final response = await _dio.get('/water/status', options: _authOptions());
    return WaterStatus.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<HouseholdUsage> getUsage() async {
    final response =
        await _dio.get('/consumption/me', options: _authOptions());
    return HouseholdUsage.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<List<AlertItem>> getAlerts() async {
    final response = await _dio.get('/alerts', options: _authOptions());
    return (response.data as List)
        .whereType<Map<String, dynamic>>()
        .map(AlertItem.fromJson)
        .toList();
  }

  Future<void> markAlertRead(int alertId) async {
    await _dio.patch('/alerts/$alertId/read', options: _authOptions());
  }

  Future<List<ComplaintItem>> getComplaints() async {
    final response = await _dio.get('/complaints', options: _authOptions());
    return (response.data as List)
        .whereType<Map<String, dynamic>>()
        .map(ComplaintItem.fromJson)
        .toList();
  }

  Future<ComplaintItem> createComplaint({
    required String category,
    required String title,
    required String description,
  }) async {
    final response = await _dio.post('/complaints',
        options: _authOptions(),
        data: {
          'category': category,
          'title': title,
          'description': description,
        });
    return ComplaintItem.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<void> uploadComplaintPhoto(int complaintId, File file) async {
    final formData = FormData.fromMap({
      'photo': await MultipartFile.fromFile(
        file.path,
        filename: file.path.split(Platform.pathSeparator).last,
      ),
    });
    await _dio.post('/complaints/$complaintId/photo',
        options: _authOptions(), data: formData);
  }

  Future<Uint8List> getComplaintPhoto(int complaintId) async {
    final response = await _dio.get<List<int>>('/complaints/$complaintId/photo',
        options: _authOptions(Options(responseType: ResponseType.bytes)));
    return Uint8List.fromList(response.data ?? const []);
  }

  Future<List<MaintenanceEventItem>> getMaintenance() async {
    final response = await _dio.get('/maintenance', options: _authOptions());
    return (response.data as List)
        .whereType<Map<String, dynamic>>()
        .map(MaintenanceEventItem.fromJson)
        .toList();
  }
}
