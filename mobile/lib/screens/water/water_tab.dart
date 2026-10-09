import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/constants.dart';
import '../../models/water_status.dart';
import '../../providers/app_providers.dart';
import '../../widgets/metric_card.dart';

class WaterTab extends ConsumerWidget {
  const WaterTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final waterAsync = ref.watch(waterStatusProvider);

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(waterStatusProvider.notifier).refresh();
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          const Text(
            'Society Water Telemetry',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: jalosInk,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 2),
          const Text(
            'Real-time tank infrastructure and reserve metrics',
            style: TextStyle(color: jalosMuted, fontSize: 12),
          ),
          const SizedBox(height: 14),
          waterAsync.when(
            loading: () => const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 40),
                child: CircularProgressIndicator(),
              ),
            ),
            error: (err, _) => metricCard(
              child: const Text(
                'Telemetry data currently unavailable.',
                style: TextStyle(color: jalosCriticalText),
              ),
            ),
            data: (water) => _buildWaterContent(context, water),
          ),
        ],
      ),
    );
  }

  Widget _buildWaterContent(BuildContext context, WaterStatus water) {
    final risk = water.runway.risk;
    final levelPct = water.levelPercent.clamp(0.0, 100.0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        metricCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'TOTAL WATER INVENTORY',
                    style: TextStyle(
                      fontSize: 10,
                      letterSpacing: 0.8,
                      color: jalosMuted,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  riskChip(risk),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                '${water.inventoryLitres.round()} Litres',
                style: const TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w900,
                  color: jalosInk,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${water.levelPercent.toStringAsFixed(1)}% of total society capacity (${water.capacityLitres.round()} L)',
                style: const TextStyle(fontSize: 12, color: jalosMuted),
              ),
              const SizedBox(height: 14),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: levelPct / 100,
                  minHeight: 12,
                  backgroundColor: const Color(0xFFE5EFEA),
                  valueColor: AlwaysStoppedAnimation(
                    risk == 'CRITICAL' || risk == 'HIGH'
                        ? const Color(0xFFE0533C)
                        : jalosGreen,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              const Divider(height: 1, color: Color(0xFFF0F4F2)),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _telemetryRow(
                      Icons.settings_input_component_outlined,
                      'Pump Status',
                      water.pumpState,
                    ),
                  ),
                  Expanded(
                    child: _telemetryRow(
                      Icons.arrow_downward_rounded,
                      'Net Inflow',
                      '${water.inflowLitresPerMinute.toStringAsFixed(1)} L/min',
                    ),
                  ),
                  Expanded(
                    child: _telemetryRow(
                      Icons.arrow_upward_rounded,
                      'Net Outflow',
                      '${water.outflowLitresPerMinute.toStringAsFixed(1)} L/min',
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        metricCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Society Tank Infrastructure (4 Tanks)',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 14,
                  color: jalosInk,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Seeded storage configuration across Jal Residency towers',
                style: TextStyle(fontSize: 11, color: jalosMuted),
              ),
              const SizedBox(height: 12),
              _tankItem(
                'Underground Sump 1',
                'Primary municipal intake & raw buffer',
                levelPct,
                '120,000 L',
              ),
              const SizedBox(height: 10),
              _tankItem(
                'Underground Sump 2',
                'Treated reserve & tanker intake',
                levelPct * 0.95,
                '80,000 L',
              ),
              const SizedBox(height: 10),
              _tankItem(
                'Overhead Tank East (Towers A–D)',
                'Gravity feed to residential units',
                levelPct * 1.02,
                '50,000 L',
              ),
              const SizedBox(height: 10),
              _tankItem(
                'Overhead Tank West (Towers E–H)',
                'Gravity feed to residential units',
                levelPct * 0.98,
                '50,000 L',
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        metricCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.local_shipping_outlined,
                      color: jalosGreen, size: 20),
                  const SizedBox(width: 8),
                  const Text(
                    'Supply Logistics',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                      color: jalosInk,
                    ),
                  ),
                  const Spacer(),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: jalosGreenLight,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      '${water.nextTankerQuantityLitres.round()} Litres',
                      style: const TextStyle(
                        fontSize: 10,
                        color: jalosGreen,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Next municipal tanker delivery estimated in ${water.formattedTankerEta}.',
                style: const TextStyle(fontSize: 13, color: Color(0xFF455A51)),
              ),
              const SizedBox(height: 4),
              Text(
                water.tankerEtaHours < water.runway.hoursToCritical
                    ? 'Delivery is projected before the society reaches critical reserve.'
                    : 'Notice: Delivery arrival is close to projected critical threshold.',
                style: TextStyle(
                  fontSize: 11,
                  color: water.tankerEtaHours < water.runway.hoursToCritical
                      ? jalosNormalText
                      : jalosCriticalText,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _telemetryRow(IconData icon, String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: jalosMuted),
            const SizedBox(width: 4),
            Text(
              label,
              style: const TextStyle(fontSize: 10, color: jalosMuted),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: jalosInk,
          ),
        ),
      ],
    );
  }

  Widget _tankItem(
      String name, String role, double percent, String capacity) {
    final clamped = percent.clamp(0.0, 100.0);
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFFFBFDFB),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE9F0EC)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                name,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: jalosInk,
                ),
              ),
              Text(
                '${clamped.toStringAsFixed(0)}% · $capacity',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: jalosGreen,
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(role, style: const TextStyle(fontSize: 10, color: jalosMuted)),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: clamped / 100,
              minHeight: 5,
              backgroundColor: const Color(0xFFE5ECE8),
              valueColor: const AlwaysStoppedAnimation(jalosGreen),
            ),
          ),
        ],
      ),
    );
  }
}
