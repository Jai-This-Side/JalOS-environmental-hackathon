class UserProfile {
  final int id;
  final String email;
  final String role;
  final int? flatId;
  final String? flatNumber;
  final String? tower;

  const UserProfile({
    required this.id,
    required this.email,
    required this.role,
    this.flatId,
    this.flatNumber,
    this.tower,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: (json['id'] as num?)?.toInt() ?? 0,
      email: json['email']?.toString() ?? '',
      role: json['role']?.toString() ?? 'RESIDENT',
      flatId: (json['flat_id'] as num?)?.toInt(),
      flatNumber: json['flat_number']?.toString(),
      tower: json['tower']?.toString(),
    );
  }
}
