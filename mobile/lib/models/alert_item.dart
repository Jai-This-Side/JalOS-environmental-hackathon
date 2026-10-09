class AlertItem {
  final int id;
  final String kind;
  final String level;
  final String message;
  final String createdAt;
  final bool read;

  const AlertItem({
    required this.id,
    required this.kind,
    required this.level,
    required this.message,
    required this.createdAt,
    required this.read,
  });

  factory AlertItem.fromJson(Map<String, dynamic> json) {
    return AlertItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      kind: json['kind']?.toString() ?? json['type']?.toString() ?? 'WATER_STATUS',
      level: json['level']?.toString() ?? 'INFO',
      message: json['message']?.toString() ?? '',
      createdAt: json['created_at']?.toString() ?? '',
      read: json['read'] == true,
    );
  }

  AlertItem copyWith({bool? read}) {
    return AlertItem(
      id: id,
      kind: kind,
      level: level,
      message: message,
      createdAt: createdAt,
      read: read ?? this.read,
    );
  }
}
