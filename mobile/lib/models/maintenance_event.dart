class MaintenanceEventItem {
  final int id;
  final String eventType;
  final String title;
  final String description;
  final String startTime;
  final String endTime;
  final List<String> affectedTowers;
  final String severity;
  final String status;

  const MaintenanceEventItem({
    required this.id,
    required this.eventType,
    required this.title,
    required this.description,
    required this.startTime,
    required this.endTime,
    required this.affectedTowers,
    required this.severity,
    required this.status,
  });

  factory MaintenanceEventItem.fromJson(Map<String, dynamic> json) {
    return MaintenanceEventItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      eventType: json['event_type']?.toString() ?? 'OTHER',
      title: json['title']?.toString() ?? 'Water maintenance',
      description: json['description']?.toString() ?? '',
      startTime: json['start_time']?.toString() ?? '',
      endTime: json['end_time']?.toString() ?? '',
      affectedTowers: (json['affected_towers'] as List?)
              ?.map((t) => t.toString())
              .toList() ??
          const [],
      severity: json['severity']?.toString() ?? 'INFO',
      status: json['status']?.toString() ?? 'SCHEDULED',
    );
  }
}
