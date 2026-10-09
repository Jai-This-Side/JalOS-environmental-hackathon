class Runway {
  final double hoursToCritical;
  final double hoursToEmpty;
  final String risk;

  const Runway({
    required this.hoursToCritical,
    required this.hoursToEmpty,
    required this.risk,
  });

  factory Runway.fromJson(Map<String, dynamic> json) {
    return Runway(
      hoursToCritical: (json['hours_to_critical'] as num?)?.toDouble() ?? 0.0,
      hoursToEmpty: (json['hours_to_empty'] as num?)?.toDouble() ?? 0.0,
      risk: json['risk']?.toString() ?? 'NORMAL',
    );
  }

  Map<String, dynamic> toJson() => {
        'hours_to_critical': hoursToCritical,
        'hours_to_empty': hoursToEmpty,
        'risk': risk,
      };
}

class WaterStatus {
  final String society;
  final bool syntheticPrototypeData;
  final String observedAt;
  final double inventoryLitres;
  final double capacityLitres;
  final double criticalReserveLitres;
  final double nextTankerQuantityLitres;
  final double levelPercent;
  final String pumpState;
  final double demandLitresPerDay;
  final String scenario;
  final double tankerEtaHours;
  final double inflowLitresPerMinute;
  final double outflowLitresPerMinute;
  final Runway runway;
  final List<String> recommendations;

  const WaterStatus({
    required this.society,
    required this.syntheticPrototypeData,
    required this.observedAt,
    required this.inventoryLitres,
    required this.capacityLitres,
    required this.criticalReserveLitres,
    required this.nextTankerQuantityLitres,
    required this.levelPercent,
    required this.pumpState,
    required this.demandLitresPerDay,
    required this.scenario,
    required this.tankerEtaHours,
    required this.inflowLitresPerMinute,
    required this.outflowLitresPerMinute,
    required this.runway,
    required this.recommendations,
  });

  factory WaterStatus.fromJson(Map<String, dynamic> json) {
    return WaterStatus(
      society: json['society']?.toString() ?? 'Jal Residency',
      syntheticPrototypeData: json['synthetic_prototype_data'] == true,
      observedAt: json['observed_at']?.toString() ?? '',
      inventoryLitres: (json['inventory_litres'] as num?)?.toDouble() ?? 0.0,
      capacityLitres: (json['capacity_litres'] as num?)?.toDouble() ?? 300000.0,
      criticalReserveLitres:
          (json['critical_reserve_litres'] as num?)?.toDouble() ?? 45000.0,
      nextTankerQuantityLitres:
          (json['next_tanker_quantity_litres'] as num?)?.toDouble() ?? 12000.0,
      levelPercent: (json['level_percent'] as num?)?.toDouble() ?? 0.0,
      pumpState: json['pump_state']?.toString() ?? 'RUNNING',
      demandLitresPerDay:
          (json['demand_litres_per_day'] as num?)?.toDouble() ?? 0.0,
      scenario: json['scenario']?.toString() ?? 'NORMAL_DAY',
      tankerEtaHours: (json['tanker_eta_hours'] as num?)?.toDouble() ?? 12.0,
      inflowLitresPerMinute:
          (json['inflow_litres_per_minute'] as num?)?.toDouble() ?? 0.0,
      outflowLitresPerMinute:
          (json['outflow_litres_per_minute'] as num?)?.toDouble() ?? 0.0,
      runway: json['runway'] is Map<String, dynamic>
          ? Runway.fromJson(json['runway'] as Map<String, dynamic>)
          : const Runway(
              hoursToCritical: 24.0, hoursToEmpty: 36.0, risk: 'NORMAL'),
      recommendations: (json['recommendations'] as List?)
              ?.map((item) => item.toString())
              .toList() ??
          const [],
    );
  }

  String get formattedRunway {
    final h = runway.hoursToCritical;
    final hours = h.floor();
    final minutes = (h.remainder(1) * 60).round();
    return '${hours}h ${minutes}m';
  }

  String get formattedTankerEta {
    final h = tankerEtaHours;
    final hours = h.floor();
    final minutes = (h.remainder(1) * 60).round();
    return '${hours}h ${minutes}m';
  }
}
