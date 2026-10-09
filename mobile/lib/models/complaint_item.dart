class ComplaintUpdateItem {
  final String status;
  final String comment;
  final String createdAt;

  const ComplaintUpdateItem({
    required this.status,
    required this.comment,
    required this.createdAt,
  });

  factory ComplaintUpdateItem.fromJson(Map<String, dynamic> json) {
    return ComplaintUpdateItem(
      status: json['status']?.toString() ?? '',
      comment: json['comment']?.toString() ?? '',
      createdAt: json['created_at']?.toString() ?? '',
    );
  }
}

class ComplaintItem {
  final int id;
  final String category;
  final String title;
  final String description;
  final String status;
  final String createdAt;
  final String? photoUrl;
  final List<ComplaintUpdateItem> updates;

  const ComplaintItem({
    required this.id,
    required this.category,
    required this.title,
    required this.description,
    required this.status,
    required this.createdAt,
    this.photoUrl,
    required this.updates,
  });

  factory ComplaintItem.fromJson(Map<String, dynamic> json) {
    return ComplaintItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      category: json['category']?.toString() ?? 'OTHER',
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      status: json['status']?.toString() ?? 'OPEN',
      createdAt: json['created_at']?.toString() ?? '',
      photoUrl: json['photo_url']?.toString(),
      updates: (json['updates'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(ComplaintUpdateItem.fromJson)
              .toList() ??
          const [],
    );
  }
}
