class ConsumptionPoint {
  final String date;
  final double litres;
  final bool anomaly;

  const ConsumptionPoint({
    required this.date,
    required this.litres,
    this.anomaly = false,
  });

  factory ConsumptionPoint.fromJson(Map<String, dynamic> json) {
    return ConsumptionPoint(
      date: json['date']?.toString() ?? '',
      litres: (json['litres'] as num?)?.toDouble() ?? 0.0,
      anomaly: json['anomaly'] == true,
    );
  }
}

class HourlyPoint {
  final int hour;
  final String label;
  final double litres;
  final bool anomaly;

  const HourlyPoint({
    required this.hour,
    required this.label,
    required this.litres,
    this.anomaly = false,
  });

  factory HourlyPoint.fromJson(Map<String, dynamic> json) {
    return HourlyPoint(
      hour: (json['hour'] as num?)?.toInt() ?? 0,
      label: json['label']?.toString() ?? '',
      litres: (json['litres'] as num?)?.toDouble() ?? 0.0,
      anomaly: json['anomaly'] == true,
    );
  }
}

class HouseholdUsage {
  final String flatId;
  final bool syntheticPrototypeData;
  final double todayLitres;
  final double yesterdayLitres;
  final double? sevenDayAverageLitres;
  final double? thirtyDayAverageLitres;
  final double householdBaselineLitresPerDay;
  final List<double> recommendedRange;
  final bool budgetIsGuidance;
  final bool possibleAnomaly;
  final List<ConsumptionPoint> dailySeries;
  final List<HourlyPoint> hourlyToday;
  final List<HourlyPoint> hourlyYesterday;

  const HouseholdUsage({
    required this.flatId,
    required this.syntheticPrototypeData,
    required this.todayLitres,
    required this.yesterdayLitres,
    this.sevenDayAverageLitres,
    this.thirtyDayAverageLitres,
    required this.householdBaselineLitresPerDay,
    required this.recommendedRange,
    required this.budgetIsGuidance,
    required this.possibleAnomaly,
    required this.dailySeries,
    required this.hourlyToday,
    required this.hourlyYesterday,
  });

  factory HouseholdUsage.fromJson(Map<String, dynamic> json) {
    return HouseholdUsage(
      flatId: json['flat_id']?.toString() ?? '',
      syntheticPrototypeData: json['synthetic_prototype_data'] == true,
      todayLitres: (json['today_litres'] as num?)?.toDouble() ?? 0.0,
      yesterdayLitres: (json['yesterday_litres'] as num?)?.toDouble() ?? 0.0,
      sevenDayAverageLitres:
          (json['seven_day_average_litres'] as num?)?.toDouble(),
      thirtyDayAverageLitres:
          (json['thirty_day_average_litres'] as num?)?.toDouble(),
      householdBaselineLitresPerDay:
          (json['household_baseline_litres_per_day'] as num?)?.toDouble() ??
              400.0,
      recommendedRange: (json['recommended_range_litres_per_day'] as List?)
              ?.whereType<num>()
              .map((v) => v.toDouble())
              .toList() ??
          const [350.0, 500.0],
      budgetIsGuidance: json['budget_is_guidance'] == true,
      possibleAnomaly: json['possible_anomaly'] == true,
      dailySeries: (json['daily_series'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(ConsumptionPoint.fromJson)
              .toList() ??
          const [],
      hourlyToday: (json['hourly_today'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(HourlyPoint.fromJson)
              .toList() ??
          const [],
      hourlyYesterday: (json['hourly_yesterday'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(HourlyPoint.fromJson)
              .toList() ??
          const [],
    );
  }
}
