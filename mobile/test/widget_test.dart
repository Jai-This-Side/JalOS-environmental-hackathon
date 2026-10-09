import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jalos_mobile/main.dart';
import 'package:jalos_mobile/models/alert_item.dart';
import 'package:jalos_mobile/models/complaint_item.dart';
import 'package:jalos_mobile/models/usage.dart';
import 'package:jalos_mobile/models/water_status.dart';
import 'package:jalos_mobile/widgets/consumption_charts.dart';

void main() {
  testWidgets('resident app opens on its sign-in screen', (tester) async {
    await tester.pumpWidget(const JalOSApp());
    await tester.pumpAndSettle();

    expect(find.text('Welcome to JalOS'), findsOneWidget);
    expect(
        find.text(
            'Society administrators use the separate JalOS Operations Portal.'),
        findsOneWidget);
  });

  testWidgets('animated tank renders a bounded water level', (tester) async {
    await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: AnimatedTank(level: 63))));
    await tester.pumpAndSettle();

    expect(find.byType(AnimatedTank), findsOneWidget);
  });

  test('WaterStatus model parsing and formatted helpers', () {
    final status = WaterStatus.fromJson({
      'society': 'Jal Residency',
      'synthetic_prototype_data': true,
      'observed_at': '2026-10-08T12:00:00Z',
      'inventory_litres': 189400.0,
      'capacity_litres': 300000.0,
      'critical_reserve_litres': 45000.0,
      'next_tanker_quantity_litres': 12000.0,
      'level_percent': 63.1,
      'pump_state': 'RUNNING',
      'demand_litres_per_day': 98000.0,
      'scenario': 'NORMAL_DAY',
      'tanker_eta_hours': 14.5,
      'inflow_litres_per_minute': 120.0,
      'outflow_litres_per_minute': 68.0,
      'runway': {
        'hours_to_critical': 35.5,
        'hours_to_empty': 46.2,
        'risk': 'NORMAL'
      },
      'recommendations': ['Normal monitoring in effect.']
    });

    expect(status.society, 'Jal Residency');
    expect(status.levelPercent, 63.1);
    expect(status.formattedRunway, '35h 30m');
    expect(status.formattedTankerEta, '14h 30m');
    expect(status.runway.risk, 'NORMAL');
  });

  test('HouseholdUsage model parses daily and hourly breakdowns', () {
    final usage = HouseholdUsage.fromJson({
      'flat_id': 'C-101',
      'synthetic_prototype_data': true,
      'today_litres': 420.0,
      'yesterday_litres': 460.0,
      'seven_day_average_litres': 440.0,
      'thirty_day_average_litres': 430.0,
      'household_baseline_litres_per_day': 430.0,
      'recommended_range_litres_per_day': [380.0, 520.0],
      'budget_is_guidance': true,
      'possible_anomaly': true,
      'daily_series': [
        {'date': '2026-10-07', 'litres': 460.0, 'anomaly': false},
        {'date': '2026-10-08', 'litres': 420.0, 'anomaly': true},
      ],
      'hourly_today': [
        {'hour': 8, 'label': '08:00', 'litres': 42.0, 'anomaly': true},
        {'hour': 9, 'label': '09:00', 'litres': 18.0, 'anomaly': false},
      ],
      'hourly_yesterday': [
        {'hour': 8, 'label': '08:00', 'litres': 24.0, 'anomaly': false},
      ],
    });

    expect(usage.flatId, 'C-101');
    expect(usage.possibleAnomaly, true);
    expect(usage.dailySeries.length, 2);
    expect(usage.dailySeries.last.anomaly, true);
    expect(usage.hourlyToday.first.anomaly, true);
    expect(usage.recommendedRange, [380.0, 520.0]);
  });

  testWidgets('ConsumptionChart renders hourly and daily views',
      (tester) async {
    final usage = HouseholdUsage.fromJson({
      'flat_id': 'C-101',
      'synthetic_prototype_data': true,
      'today_litres': 420.0,
      'yesterday_litres': 460.0,
      'seven_day_average_litres': 440.0,
      'thirty_day_average_litres': 430.0,
      'household_baseline_litres_per_day': 430.0,
      'recommended_range_litres_per_day': [380.0, 520.0],
      'budget_is_guidance': true,
      'possible_anomaly': false,
      'daily_series': [
        {'date': '2026-10-07', 'litres': 460.0, 'anomaly': false},
        {'date': '2026-10-08', 'litres': 420.0, 'anomaly': false},
      ],
      'hourly_today': [
        {'hour': 0, 'label': '00:00', 'litres': 2.0, 'anomaly': false},
        {'hour': 8, 'label': '08:00', 'litres': 35.0, 'anomaly': false},
      ],
      'hourly_yesterday': [],
    });

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: ConsumptionChart(usage: usage, window: 'Today'),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.byType(ConsumptionChart), findsOneWidget);
  });

  test('AlertItem and ComplaintItem serialization', () {
    final alert = AlertItem.fromJson({
      'id': 1,
      'kind': 'WATER_STATUS',
      'level': 'HIGH',
      'message': 'Tanker delayed by 8 hours',
      'created_at': '2026-10-08T10:00:00Z',
      'read': false,
    });
    expect(alert.read, false);
    final readAlert = alert.copyWith(read: true);
    expect(readAlert.read, true);

    final complaint = ComplaintItem.fromJson({
      'id': 42,
      'category': 'LOW_PRESSURE',
      'title': 'Low water pressure in 4th floor',
      'description': 'Taps on 4th floor running very slow since 7am',
      'status': 'IN_PROGRESS',
      'created_at': '2026-10-08T08:00:00Z',
      'updates': [
        {
          'status': 'ACKNOWLEDGED',
          'comment': 'Maintenance plumber dispatched',
          'created_at': '2026-10-08T08:30:00Z'
        }
      ]
    });
    expect(complaint.id, 42);
    expect(complaint.updates.length, 1);
    expect(complaint.updates.first.status, 'ACKNOWLEDGED');
  });
}
