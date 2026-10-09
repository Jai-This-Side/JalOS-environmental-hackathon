import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/constants.dart';
import '../../models/water_status.dart';
import '../../providers/app_providers.dart';
import '../../widgets/animated_tank.dart';
import '../../widgets/metric_card.dart';

class HomeTab extends ConsumerWidget {
  const HomeTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final waterAsync = ref.watch(waterStatusProvider);
    final maintenanceAsync = ref.watch(maintenanceProvider);

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(waterStatusProvider.notifier).refresh();
        ref.invalidate(maintenanceProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          const Text(
            'Good morning',
            style: TextStyle(color: jalosMuted, fontSize: 13),
          ),
          const SizedBox(height: 2),
          const Text(
            'Your water, at a glance',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: jalosInk,
              letterSpacing: -0.5,
            ),
          ),
          waterAsync.when(
            loading: () => const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 40),
                child: CircularProgressIndicator(),
              ),
            ),
            error: (err, _) => Padding(
              padding: const EdgeInsets.only(top: 14),
              child: metricCard(
                child: Row(
                  children: [
                    const Icon(Icons.cloud_off_rounded,
                        color: jalosCriticalText),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Unable to reach JalOS API. Verify the server is running.',
                        style: const TextStyle(
                            color: jalosCriticalText, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            data: (water) => _buildContent(context, water, maintenanceAsync),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WaterStatus water,
    AsyncValue<dynamic> maintenanceAsync,
  ) {
    final risk = water.runway.risk;
    final recommendation = water.recommendations.isNotEmpty
        ? water.recommendations.first
        : 'Water inventory is stable. Normal monitoring in effect.';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (water.syntheticPrototypeData)
          Container(
            margin: const EdgeInsets.only(top: 10, bottom: 4),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: jalosGreenLight,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.science_outlined, size: 13, color: jalosGreen),
                SizedBox(width: 5),
                Text(
                  'DEMO · Synthetic prototype readings',
                  style: TextStyle(
                    fontSize: 10,
                    color: jalosGreen,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 14),
        metricCard(
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'SOCIETY WATER LEVEL',
                    style: TextStyle(
                      fontSize: 11,
                      letterSpacing: 1,
                      color: jalosMuted,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  riskChip(risk),
                ],
              ),
              const SizedBox(height: 12),
              AnimatedTank(level: water.levelPercent, risk: risk),
              const SizedBox(height: 8),
              Text(
                '${water.levelPercent.toStringAsFixed(0)}%',
                style: const TextStyle(
                  fontSize: 32,
                  color: jalosInk,
                  fontWeight: FontWeight.w900,
                ),
              ),
              Text(
                '${water.inventoryLitres.round()} L available',
                style: const TextStyle(
                  color: jalosMuted,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Usable inventory of ${water.capacityLitres.round()} L capacity',
                style: const TextStyle(fontSize: 11, color: Color(0xFF9AA7A1)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: statTile(
                label: 'Expected Runway',
                value: water.formattedRunway,
                icon: Icons.hourglass_bottom_rounded,
                subtext: 'To critical reserve',
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: statTile(
                label: 'Next Supply',
                value: water.formattedTankerEta,
                icon: Icons.local_shipping_outlined,
                subtext: '${water.nextTankerQuantityLitres.round()} L tanker',
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        metricCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.tips_and_updates_outlined,
                      color: jalosGreen, size: 18),
                  SizedBox(width: 8),
                  Text(
                    'Operational Guidance',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      color: jalosInk,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                recommendation,
                style: const TextStyle(
                  height: 1.45,
                  color: Color(0xFF52685E),
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Your household consumption is private and not shared publicly.',
                style: TextStyle(fontSize: 10, color: jalosMuted),
              ),
            ],
          ),
        ),
        maintenanceAsync.when(
          data: (events) {
            final scheduled = events
                .where((e) => e.status == 'SCHEDULED')
                .take(2)
                .toList();
            if (scheduled.isEmpty) return const SizedBox.shrink();
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 16),
                const Text(
                  'Upcoming Maintenance',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: jalosInk,
                  ),
                ),
                const SizedBox(height: 8),
                ...scheduled.map((e) {
                  final start = DateTime.tryParse(e.startTime)?.toLocal();
                  final when = start == null
                      ? 'Scheduled notice'
                      : '${start.day}/${start.month} · ${start.hour.toString().padLeft(2, '0')}:${start.minute.toString().padLeft(2, '0')}';
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: metricCard(
                      padding: const EdgeInsets.all(12),
                      child: ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: jalosMint,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(Icons.build_outlined,
                              color: jalosGreen, size: 20),
                        ),
                        title: Text(
                          e.title,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                            color: jalosInk,
                          ),
                        ),
                        subtitle: Text(
                          '$when · ${e.affectedTowers.isEmpty ? 'All towers' : e.affectedTowers.join(', ')}',
                          style: const TextStyle(
                              fontSize: 11, color: jalosMuted),
                        ),
                      ),
                    ),
                  );
                }),
              ],
            );
          },
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
        ),
      ],
    );
  }
}
